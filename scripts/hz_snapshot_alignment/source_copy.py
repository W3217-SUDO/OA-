"""完整保留只读旧库快照，并校验每张表的全部字段。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import sql
import pyodbc


def source_connection():
    return pyodbc.connect(os.environ["HZ_SQLSERVER_DSN"], timeout=15)


def target_connection():
    return psycopg.connect(os.environ["HZ_POSTGRES_DSN"])


def source_schema(connection):
    tables = {}
    for name, column, kind, length, precision, scale, nullable in connection.execute("""
        SELECT t.name,c.name,ty.name,c.max_length,c.precision,c.scale,c.is_nullable
        FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        ORDER BY t.name,c.column_id
    """):
        tables.setdefault(name, []).append(
            {
                "name": column,
                "type": kind,
                "length": length,
                "precision": precision,
                "scale": scale,
                "nullable": bool(nullable),
            }
        )
    return tables


def pg_type(spec):
    kind = spec["type"]
    if kind in {"nvarchar", "varchar", "char", "nchar"}:
        size = spec["length"] // 2 if kind.startswith("n") else spec["length"]
        if spec["length"] == -1:
            return "text"
        return f"{'char' if kind in {'char', 'nchar'} else 'varchar'}({size})"
    if kind in {"decimal", "numeric"}:
        return f"numeric({spec['precision']},{spec['scale']})"
    types = {
        "int": "integer",
        "bigint": "bigint",
        "smallint": "smallint",
        "tinyint": "smallint",
        "bit": "boolean",
        "datetime": "timestamp",
        "datetime2": "timestamp",
        "smalldatetime": "timestamp",
        "date": "date",
        "uniqueidentifier": "varchar(36)",
        "varbinary": "bytea",
        "binary": "bytea",
        "image": "bytea",
        "ntext": "text",
        "text": "text",
        "float": "double precision",
        "real": "real",
        "money": "numeric(19,4)",
        "smallmoney": "numeric(10,4)",
    }
    if kind not in types:
        raise ValueError(f"不支持的源类型: {kind}")
    return types[kind]


def canonical(value, spec):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if isinstance(value, Decimal):
        return str(value.normalize()) if value else "0"
    if spec["type"] in {"char", "nchar"}:
        return str(value).rstrip(" ")
    if isinstance(value, str) and "\x00" in value:
        raise ValueError(f"源字段 {spec['name']} 含 NUL 字符，不能静默丢弃")
    return value


class Fingerprint:
    def __init__(self, columns):
        self.columns = columns
        self.count = 0
        self.total = 0
        self.xor = 0

    def add(self, row):
        encoded = json.dumps(
            [canonical(value, spec) for value, spec in zip(row, self.columns)],
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        digest = int.from_bytes(hashlib.sha256(encoded).digest(), "big")
        self.count += 1
        self.total = (self.total + digest) % (1 << 256)
        self.xor ^= digest

    def result(self):
        return {"rows": self.count, "sha256_sum": f"{self.total:064x}", "sha256_xor": f"{self.xor:064x}"}


def target_fingerprint(connection, name, columns):
    result = Fingerprint(columns)
    statement = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(",").join(sql.Identifier(c["name"]) for c in columns), sql.Identifier(name)
    )
    with connection.cursor(name="verify_raw") as cursor:
        cursor.itersize = 2000
        cursor.execute(statement)
        for row in cursor:
            result.add(row)
    return result.result()


def ensure_columns(connection, name, columns):
    existing = {
        row[0]: row[1:]
        for row in connection.execute(
            "SELECT column_name,character_maximum_length,numeric_precision,numeric_scale,data_type "
            "FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
            (name,),
        )
    }
    if not existing:
        definitions = [
            sql.SQL("{} {} {}").format(
                sql.Identifier(c["name"]), sql.SQL(pg_type(c)), sql.SQL("" if c["nullable"] else "NOT NULL")
            )
            for c in columns
        ]
        connection.execute(sql.SQL("CREATE TABLE {} ({})").format(sql.Identifier(name), sql.SQL(",").join(definitions)))
        return
    for spec in columns:
        if spec["name"] not in existing:
            connection.execute(
                sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                    sql.Identifier(name), sql.Identifier(spec["name"]), sql.SQL(pg_type(spec))
                )
            )
            continue
        length, precision, scale, kind = existing[spec["name"]]
        expected_length = spec["length"] // 2 if spec["type"].startswith("n") else spec["length"]
        wider_text = (
            spec["type"] in {"varchar", "nvarchar", "char", "nchar"}
            and length is not None
            and (spec["length"] == -1 or expected_length > length)
        )
        wider_number = (
            spec["type"] in {"decimal", "numeric"}
            and kind == "numeric"
            and (spec["precision"] > precision or spec["scale"] > scale)
        )
        if wider_text or wider_number:
            connection.execute(
                sql.SQL("ALTER TABLE {} ALTER COLUMN {} TYPE {}").format(
                    sql.Identifier(name), sql.Identifier(spec["name"]), sql.SQL(pg_type(spec))
                )
            )


def reset_sequences(connection, name):
    for column, sequence in connection.execute(
        """
        SELECT column_name, pg_get_serial_sequence(format('%%I', table_name), column_name)
        FROM information_schema.columns WHERE table_schema='public' AND table_name=%s
          AND (is_identity='YES' OR column_default LIKE 'nextval%%')
    """,
        (name,),
    ).fetchall():
        if sequence:
            value, populated = connection.execute(
                sql.SQL("SELECT COALESCE(max({}),1),count(*)>0 FROM {}").format(
                    sql.Identifier(column), sql.Identifier(name)
                )
            ).fetchone()
            connection.execute("SELECT setval(%s,%s,%s)", (sequence, value, populated))


def run(report_path, apply):
    prior = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {"tables": {}}
    with source_connection() as source, target_connection() as target:
        schema = source_schema(source)
        prior["source_table_count"] = len(schema)
        prior["source_column_count"] = sum(len(c) for c in schema.values())
        for name, columns in schema.items():
            with target.transaction():
                ensure_columns(target, name, columns)
                count = target.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(name))).fetchone()[0]
                previous = prior["tables"].get(name)
                if count and not previous:
                    raise RuntimeError(f"{name} 已有 {count} 条未知数据，停止以避免覆盖")
                fingerprint = Fingerprint(columns)
                fields = ",".join("[" + c["name"].replace("]", "]]") + "]" for c in columns)
                cursor = source.cursor()
                cursor.execute(f"SELECT {fields} FROM [{name}]")
                if previous:
                    for row in cursor:
                        fingerprint.add(row)
                else:
                    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
                        sql.Identifier(name), sql.SQL(",").join(sql.Identifier(c["name"]) for c in columns)
                    )
                    with target.cursor().copy(statement) as copy:
                        while batch := cursor.fetchmany(2000):
                            for row in batch:
                                fingerprint.add(row)
                                copy.write_row(tuple(row))
                expected = fingerprint.result()
                actual = target_fingerprint(target, name, columns)
                if expected != actual:
                    raise RuntimeError(f"{name} 全字段校验失败: {expected} != {actual}")
                reset_sequences(target, name)
            if apply:
                target.commit()
                prior["tables"][name] = {"columns": len(columns), **expected}
                report_path.write_text(json.dumps(prior, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                target.rollback()
            print(
                json.dumps(
                    {
                        "table": name,
                        "rows": expected["rows"],
                        "columns": len(columns),
                        "verified": True,
                        "applied": apply,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    print(
        json.dumps(
            {"verified_tables": len(prior["tables"]), "verified_rows": sum(r["rows"] for r in prior["tables"].values())}
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(args.report, args.apply)

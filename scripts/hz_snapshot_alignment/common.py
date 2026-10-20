"""本地迁移的连接、源表读取和事务内投影工具。"""

import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from ..hz_field_maps import text

SOURCE = "hz_crm_20260930"
ACTOR = "hz-alignment"
LOCAL_TZ = timezone(timedelta(hours=8))


def connect():
    report_directory()
    db = psycopg.connect(os.environ["HZ_POSTGRES_DSN"], row_factory=dict_row)
    db.execute("SET TIME ZONE 'Asia/Shanghai'")
    return db


def rows(db, table):
    return db.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))).fetchall()


def keyed(items, field):
    result = {}
    for row in items:
        key = text(row.get(field))
        if not key or key in result:
            raise ValueError(f"{field} source identity is empty or duplicated")
        result[key] = row
    return result


def audit_time(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=LOCAL_TZ) if value.tzinfo is None else value
    return value


def enum_labels(suffix):
    with Path(__file__).with_name("enum-values.csv").open(encoding="utf-8-sig", newline="") as handle:
        result = {
            text(row["value"]): row["description"] or row["name"]
            for row in csv.DictReader(handle)
            if row["enum"].endswith("." + suffix)
        }
    if not result:
        raise ValueError(f"Legacy enum is unavailable: {suffix}")
    return result


def report_directory():
    output = Path(os.environ["HZ_ALIGNMENT_OUTPUT_DIR"]).expanduser().resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("迁移报告必须保存到仓库外目录")
    output.mkdir(parents=True, exist_ok=True)
    return output


def save_report(name, report):
    output = report_directory()
    (output / name).write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, default=str), flush=True)

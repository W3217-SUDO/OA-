"""Register the complete read-only legacy SQL Server schema in SQLAlchemy.

The manifest is exported from the restored local legacy database.  Existing
ORM projections remain authoritative; this module fills in the tables that do
not yet have dedicated application models and restores legacy indexes.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Column,
    DateTime,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Unicode,
    UnicodeText,
    inspect,
    text,
)


MANIFEST_PATH = Path(__file__).with_name("legacy_schema_manifest.json")
POSTGRES_INDEX_COLUMN_LIMIT = 32


def load_legacy_schema_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _column_type(spec: dict):
    name = spec["type"].lower()
    length = spec.get("max_length")
    if name == "varchar":
        return Text() if length == -1 else String(length)
    if name == "nvarchar":
        return UnicodeText() if length == -1 else Unicode(length // 2)
    if name == "char":
        return CHAR(length)
    if name == "datetime":
        return DateTime(timezone=False)
    if name == "int":
        return Integer()
    if name == "bigint":
        return BigInteger()
    if name == "decimal":
        return Numeric(spec["precision"], spec["scale"])
    if name == "uniqueidentifier":
        return String(36)
    if name == "bit":
        return Boolean()
    if name == "varbinary":
        return LargeBinary(None if length == -1 else length)
    raise ValueError(f"Unsupported legacy SQL type: {name}")


def _attach_indexes(table: Table, indexes: list[dict]) -> None:
    existing_names = {index.name for index in table.indexes}
    for spec in indexes:
        if spec["name"] in existing_names:
            continue
        key_columns = [
            table.c[item["name"]].desc() if item["descending"] else table.c[item["name"]]
            for item in spec["columns"]
            if not item["included"]
        ]
        include_columns = [item["name"] for item in spec["columns"] if item["included"]]
        if not key_columns:
            continue
        kwargs = {"unique": bool(spec["unique"])}
        if include_columns:
            available = max(0, POSTGRES_INDEX_COLUMN_LIMIT - len(key_columns))
            kwargs["postgresql_include"] = include_columns[:available]
        Index(spec["name"], *key_columns, **kwargs)


def register_legacy_table(metadata: MetaData, table_spec: dict) -> Table:
    columns = []
    for spec in table_spec["columns"]:
        args = []
        if spec["identity"]:
            args.append(Identity(start=spec["identity_seed"], increment=spec["identity_increment"]))
        columns.append(
            Column(
                spec["name"],
                _column_type(spec),
                *args,
                nullable=bool(spec["nullable"]),
                primary_key=bool(spec["primary_key_ordinal"]),
            )
        )
    table = Table(table_spec["name"], metadata, *columns)
    _attach_indexes(table, table_spec["indexes"])
    return table


def legacy_table_from_manifest(metadata: MetaData, name: str) -> Table:
    table_spec = next(
        table for table in load_legacy_schema_manifest()["tables"] if table["name"] == name
    )
    return register_legacy_table(metadata, table_spec)


def register_legacy_schema(metadata: MetaData) -> dict[str, int]:
    manifest = load_legacy_schema_manifest()
    created = 0
    existing = 0
    for table_spec in manifest["tables"]:
        name = table_spec["name"]
        table = metadata.tables.get(name)
        if table is None:
            table = register_legacy_table(metadata, table_spec)
            created += 1
        else:
            existing += 1
            table.indexes.clear()
        _attach_indexes(table, table_spec["indexes"])
    return {"created": created, "existing": existing, "total": len(manifest["tables"])}


LEGACY_METADATA = MetaData()
LEGACY_SCHEMA_REGISTRATION = register_legacy_schema(LEGACY_METADATA)


def create_full_legacy_schema(connection) -> None:
    """Create all legacy tables without mixing them into application metadata."""

    if connection.dialect.name != "postgresql":
        return
    LEGACY_METADATA.create_all(connection, checkfirst=True)


def ensure_legacy_indexes(connection) -> None:
    """Create manifest indexes that create_all cannot add to existing tables."""

    if connection.dialect.name != "postgresql":
        return
    manifest_index_names = {
        index_spec["name"]
        for table_spec in load_legacy_schema_manifest()["tables"]
        for index_spec in table_spec["indexes"]
    }
    for table in LEGACY_METADATA.tables.values():
        for index in table.indexes:
            if index.name in manifest_index_names:
                index.create(connection, checkfirst=True)


def align_legacy_indexes(connection) -> None:
    """Remove projection-only indexes after all original indexes exist."""

    if connection.dialect.name != "postgresql":
        return
    inspector = inspect(connection)
    preparer = connection.dialect.identifier_preparer
    for table_spec in load_legacy_schema_manifest()["tables"]:
        table_name = table_spec["name"]
        expected = {index_spec["name"] for index_spec in table_spec["indexes"]}
        for index in inspector.get_indexes(table_name):
            name = index["name"]
            if name not in expected:
                connection.execute(text(f"DROP INDEX IF EXISTS {preparer.quote(name)}"))


def align_legacy_constraints(connection) -> None:
    """Apply narrowly-scoped, data-preserving constraint corrections."""

    if connection.dialect.name != "postgresql":
        return
    inspector = inspect(connection)
    table_name = "FCM_Contract_File"
    if table_name not in inspector.get_table_names():
        return
    primary_key = inspector.get_pk_constraint(table_name) or {}
    if primary_key.get("constrained_columns") == ["FileGuid"]:
        return
    invalid = connection.execute(
        text(
            'SELECT COUNT(*) FROM "FCM_Contract_File" '
            'WHERE "FileGuid" IS NULL OR "FileGuid" IN ('
            'SELECT "FileGuid" FROM "FCM_Contract_File" '
            'GROUP BY "FileGuid" HAVING COUNT(*) > 1)'
        )
    ).scalar_one()
    if invalid:
        raise RuntimeError(
            "Cannot align FCM_Contract_File primary key: FileGuid contains null or duplicate values"
        )
    constraint_name = primary_key.get("name")
    if constraint_name:
        quoted = connection.dialect.identifier_preparer.quote(constraint_name)
        connection.execute(text(f'ALTER TABLE "FCM_Contract_File" DROP CONSTRAINT {quoted}'))
    connection.execute(text('ALTER TABLE "FCM_Contract_File" ADD PRIMARY KEY ("FileGuid")'))


def _type_signature(column_type) -> tuple:
    if isinstance(column_type, CHAR):
        return ("char", column_type.length)
    if isinstance(column_type, Text):
        return ("text",)
    if isinstance(column_type, String):
        return ("string", column_type.length)
    if isinstance(column_type, BigInteger):
        return ("bigint",)
    if isinstance(column_type, Integer):
        return ("integer",)
    if isinstance(column_type, Numeric):
        return ("numeric", column_type.precision, column_type.scale)
    if isinstance(column_type, DateTime):
        return ("datetime", bool(column_type.timezone))
    if isinstance(column_type, Boolean):
        return ("boolean",)
    if isinstance(column_type, LargeBinary):
        return ("binary", column_type.length)
    return (column_type.__class__.__name__.lower(),)


def align_legacy_column_types(connection) -> None:
    """Widen or safely narrow existing projection columns to legacy types."""

    if connection.dialect.name != "postgresql":
        return
    inspector = inspect(connection)
    preparer = connection.dialect.identifier_preparer
    for table in LEGACY_METADATA.tables.values():
        actual_columns = {item["name"]: item for item in inspector.get_columns(table.name)}
        for desired in table.c:
            actual = actual_columns[desired.name]
            if _type_signature(actual["type"]) == _type_signature(desired.type):
                continue
            length = getattr(desired.type, "length", None)
            quoted_table = preparer.quote(table.name)
            quoted_column = preparer.quote(desired.name)
            if length is not None:
                maximum = connection.execute(
                    text(f"SELECT COALESCE(MAX(char_length({quoted_column})), 0) FROM {quoted_table}")
                ).scalar_one()
                if maximum > length:
                    raise RuntimeError(
                        f"Cannot align {table.name}.{desired.name}: existing length {maximum} exceeds {length}"
                    )
            target = desired.type.compile(dialect=connection.dialect)
            connection.execute(
                text(
                    f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_column} "
                    f"TYPE {target} USING {quoted_column}::{target}"
                )
            )


def audit_legacy_schema(connection) -> dict:
    """Return exact structural errors plus non-semantic column-order warnings."""

    inspector = inspect(connection)
    database_tables = set(inspector.get_table_names())
    errors = []
    order_warnings = []
    for expected_table in LEGACY_METADATA.tables.values():
        name = expected_table.name
        if name not in database_tables:
            errors.append({"table": name, "issue": "missing_table"})
            continue
        actual_list = inspector.get_columns(name)
        actual_columns = {column["name"]: column for column in actual_list}
        expected_names = list(expected_table.c.keys())
        actual_names = [column["name"] for column in actual_list]
        missing = sorted(set(expected_names) - set(actual_names))
        extra = sorted(set(actual_names) - set(expected_names))
        if missing or extra:
            errors.append({"table": name, "issue": "columns", "missing": missing, "extra": extra})
            continue
        if actual_names != expected_names:
            order_warnings.append(name)
        for expected in expected_table.c:
            actual = actual_columns[expected.name]
            if _type_signature(actual["type"]) != _type_signature(expected.type):
                errors.append({"table": name, "column": expected.name, "issue": "type"})
            if bool(actual["nullable"]) != bool(expected.nullable):
                errors.append({"table": name, "column": expected.name, "issue": "nullable"})
            if expected.identity is not None and connection.dialect.name == "postgresql":
                default = str(actual.get("default") or "")
                if not actual.get("identity") and "nextval(" not in default:
                    errors.append({"table": name, "column": expected.name, "issue": "identity"})
        expected_pk = {column.name for column in expected_table.primary_key.columns}
        actual_pk = set((inspector.get_pk_constraint(name) or {}).get("constrained_columns") or [])
        if actual_pk != expected_pk:
            errors.append(
                {"table": name, "issue": "primary_key", "expected": sorted(expected_pk), "actual": sorted(actual_pk)}
            )
        expected_indexes = {index.name for index in expected_table.indexes}
        actual_indexes = {index["name"] for index in inspector.get_indexes(name)}
        if actual_indexes != expected_indexes:
            errors.append(
                {
                    "table": name,
                    "issue": "indexes",
                    "missing": sorted(expected_indexes - actual_indexes),
                    "extra": sorted(actual_indexes - expected_indexes),
                }
            )
    return {
        "expected_tables": len(LEGACY_METADATA.tables),
        "errors": errors,
        "column_order_warnings": sorted(order_warnings),
    }

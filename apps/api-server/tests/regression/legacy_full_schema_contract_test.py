"""Full legacy schema registration and DDL regression checks."""

from sqlalchemy import create_engine, inspect

from app.legacy_schema import (
    LEGACY_METADATA,
    LEGACY_SCHEMA_REGISTRATION,
    _type_signature,
    load_legacy_schema_manifest,
    POSTGRES_INDEX_COLUMN_LIMIT,
    audit_legacy_schema,
)
from app.models import Base


def test_complete_manifest_is_registered() -> None:
    manifest = load_legacy_schema_manifest()
    assert manifest["table_count"] == 239
    assert len(manifest["tables"]) == 239
    assert sum(len(table["columns"]) for table in manifest["tables"]) == 3951
    assert sum(len(table["indexes"]) for table in manifest["tables"]) == 104
    assert LEGACY_SCHEMA_REGISTRATION == {"created": 239, "existing": 0, "total": 239}

    for table_spec in manifest["tables"]:
        table = LEGACY_METADATA.tables[table_spec["name"]]
        assert list(table.c.keys()) == [column["name"] for column in table_spec["columns"]]
        expected_pk = {
            column["name"]
            for column in table_spec["columns"]
            if column["primary_key_ordinal"]
        }
        assert {column.name for column in table.primary_key.columns} == expected_pk
        for index in table.indexes:
            include_count = len(index.dialect_options["postgresql"].get("include") or [])
            assert len(index.expressions) + include_count <= POSTGRES_INDEX_COLUMN_LIMIT


def test_complete_manifest_creates_on_empty_database() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    LEGACY_METADATA.create_all(engine)
    inspector = inspect(engine)

    manifest = load_legacy_schema_manifest()
    database_tables = set(inspector.get_table_names())
    for table_spec in manifest["tables"]:
        assert table_spec["name"] in database_tables
        actual_columns = inspector.get_columns(table_spec["name"])
        assert [column["name"] for column in actual_columns] == [
            column["name"] for column in table_spec["columns"]
        ]
    with engine.connect() as connection:
        report = audit_legacy_schema(connection)
    assert report["errors"] == []
    assert report["column_order_warnings"] == []


def test_dedicated_projection_tables_remain_in_application_metadata() -> None:
    manifest_names = {table["name"] for table in load_legacy_schema_manifest()["tables"]}
    projection_names = manifest_names.intersection(Base.metadata.tables)
    assert len(projection_names) == 18
    assert "Legal_Case" in projection_names
    assert list(Base.metadata.tables["Legal_Case"].c.keys()) == list(
        LEGACY_METADATA.tables["Legal_Case"].c.keys()
    )
    for table_name in projection_names:
        actual = Base.metadata.tables[table_name]
        expected = LEGACY_METADATA.tables[table_name]
        assert list(actual.c.keys()) == list(expected.c.keys())
        assert {column.name for column in actual.primary_key.columns} == {
            column.name for column in expected.primary_key.columns
        }
        for expected_column in expected.c:
            actual_column = actual.c[expected_column.name]
            assert actual_column.nullable == expected_column.nullable
            assert _type_signature(actual_column.type) == _type_signature(expected_column.type)

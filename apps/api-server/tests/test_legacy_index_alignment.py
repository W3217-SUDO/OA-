"""旧库索引对齐的持久化回归测试。"""

import unittest
from unittest.mock import patch

from sqlalchemy import Column, Index, Integer, MetaData, Table, create_engine, inspect, text

from app import legacy_schema


class LegacyIndexAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.metadata = MetaData()
        table = Table(
            "legacy_index_sample",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("code", Integer),
        )
        Index("ix_legacy_index_sample_code", table.c.code)
        self.metadata.create_all(self.engine)
        self.manifest = {
            "tables": [{
                "name": "legacy_index_sample",
                "indexes": [{"name": "ix_legacy_index_sample_code"}],
            }],
        }

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_preserves_application_index_and_reports_it_as_warning(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text(
                "CREATE INDEX ix_legacy_index_sample_app_query "
                "ON legacy_index_sample (id, code)"
            ))
            with patch.object(legacy_schema, "load_legacy_schema_manifest", return_value=self.manifest):
                with patch.object(connection.dialect, "name", "postgresql"):
                    legacy_schema.align_legacy_indexes(connection)
            report = self._audit(connection)
            indexes = {item["name"] for item in inspect(connection).get_indexes("legacy_index_sample")}

        self.assertEqual(indexes, {
            "ix_legacy_index_sample_code",
            "ix_legacy_index_sample_app_query",
        })
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["extra_index_warnings"], {
            "legacy_index_sample": ["ix_legacy_index_sample_app_query"],
        })

    def test_missing_manifest_index_remains_a_hard_error(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("DROP INDEX ix_legacy_index_sample_code"))
            with patch.object(legacy_schema, "load_legacy_schema_manifest", return_value=self.manifest):
                with patch.object(connection.dialect, "name", "postgresql"):
                    with self.assertRaisesRegex(RuntimeError, "ix_legacy_index_sample_code"):
                        legacy_schema.align_legacy_indexes(connection)
            report = self._audit(connection)

        self.assertEqual(report["errors"], [{
            "table": "legacy_index_sample",
            "issue": "indexes",
            "missing": ["ix_legacy_index_sample_code"],
        }])

    def _audit(self, connection):
        with patch.object(legacy_schema, "LEGACY_METADATA", self.metadata):
            return legacy_schema.audit_legacy_schema(connection)


if __name__ == "__main__":
    unittest.main()

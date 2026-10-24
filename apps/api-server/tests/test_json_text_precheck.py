import unittest

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from app.core.json_relation_query import TEXT_PRECHECK_MAX_CANDIDATES, json_scalar_overlap, json_text_precheck
from app.models import BusinessRecord


def _sql(condition, dialect):
    statement = select(BusinessRecord.id).where(condition)
    return " ".join(str(statement.compile(dialect=dialect, compile_kwargs={"literal_binds": True})).split())


class JsonTextPrecheckTest(unittest.TestCase):
    def test_small_ascii_candidates_add_substring_precheck_before_exact_match(self):
        sql = _sql(json_scalar_overlap(BusinessRecord.data, {12, "HZMS2600444"}), postgresql.dialect())
        self.assertIn("CAST(business_records.data AS TEXT) ~ '(12|HZMS2600444)'", sql)
        self.assertLess(sql.index(" ~ "), sql.index("jsonb_path_query"))

    def test_non_ascii_or_many_candidates_keep_original_scan(self):
        for values in ({"沪0101民初1号"}, {"a.b"}, set(range(TEXT_PRECHECK_MAX_CANDIDATES + 1))):
            sql = _sql(json_scalar_overlap(BusinessRecord.data, values), postgresql.dialect())
            self.assertNotIn(" ~ ", sql)
            self.assertIn("jsonb_path_query", sql)
            self.assertIsNone(json_text_precheck(BusinessRecord.data, values))
        self.assertIsNone(json_text_precheck(BusinessRecord.data, set()))

    def test_sqlite_precheck_is_neutral(self):
        sql = _sql(json_scalar_overlap(BusinessRecord.data, {1}), sqlite.dialect())
        self.assertIn("WHERE 1 = 1 AND EXISTS", sql)


if __name__ == "__main__":
    unittest.main()

"""11-06 改案件保存慢：sync_case_clues 的 6 个 OR 条件只有 linked_case_no 没索引，生产实测 1.8 s 逐行解析全部线索。"""

import re
import unittest

from sqlalchemy import or_, select
from sqlalchemy.dialects import postgresql

from app.core.schema_alignment import BUSINESS_RECORD_JSON_INDEXES
from app.core.startup_migrations import _apply_clue_linked_case_no_index
from app.models import BusinessRecord


class _Dialect:
    def __init__(self, name):
        self.name = name


class _Connection:
    def __init__(self, name="postgresql"):
        self.dialect = _Dialect(name)
        self.statements = []

    def execute(self, statement, *_args):
        self.statements.append(str(statement))


class ClueLinkedCaseNoIndexTest(unittest.TestCase):
    def test_every_or_condition_in_sync_case_clues_has_an_index(self):
        """OR 里缺一个索引，其余索引全部用不上；查询新增条件时这里会失败。"""
        indexed = {re.search(r"'(\w+)'", expression).group(1) for _, expression, _ in BUSINESS_RECORD_JSON_INDEXES}
        condition = or_(
            BusinessRecord.data["case_id"].as_integer() == 1,
            BusinessRecord.data["case_record_id"].as_integer() == 1,
            BusinessRecord.data["converted_case_id"].as_integer() == 1,
            BusinessRecord.data["case_no"].as_string() == "X",
            BusinessRecord.data["linked_case_no"].as_string() == "X",
            BusinessRecord.data["converted_case_no"].as_string() == "X",
        )
        sql = str(select(BusinessRecord.id).where(condition).compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertEqual(set(re.findall(r"data ->> '(\w+)'", sql)) - indexed, set())

    def test_revision_expression_matches_query_and_cannot_stall_writes(self):
        connection = _Connection()
        _apply_clue_linked_case_no_index(connection, lambda _: None)
        joined = "\n".join(connection.statements)
        self.assertIn("ON business_records ((data ->> 'linked_case_no'))", joined)
        self.assertNotIn("CONCURRENTLY", joined)  # 启动修订在事务里
        self.assertLess(joined.index("lock_timeout"), joined.index("CREATE INDEX"))

    def test_revision_skips_non_postgres(self):
        connection = _Connection("sqlite")
        _apply_clue_linked_case_no_index(connection, lambda _: None)
        self.assertEqual(connection.statements, [])


if __name__ == "__main__":
    unittest.main()

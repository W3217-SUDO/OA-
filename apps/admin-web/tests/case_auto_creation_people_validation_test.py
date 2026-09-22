"""自动创建案件的人员校验回归；仅捕获待持久化对象，不连接或写入数据库。"""

from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.areas.investigation.router import batch_create_cases_from_clues
from app.areas.legal.router import duplicate_case
from app.models import BusinessRecord, User
from app.models_shared import BatchClueCaseInput


class ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class CapturingSession:
    """只接受预期查询并记录对象；flush/commit 均不执行 SQL。"""

    def __init__(self, users, clues=()):
        self.users = users
        self.clues = list(clues)
        self.added = []
        self.commit = AsyncMock()
        self.refresh = AsyncMock()
        self.scalar = AsyncMock(return_value=users[0])

    async def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is BusinessRecord:
            return ScalarRows(self.clues)
        if entity is User:
            # 真实解析函数生成查询；替身模拟其有效用户和姓名过滤条件。
            sql = str(statement)
            assert "users.is_active IS true" in sql, sql
            params = statement.compile().params
            labels = {value for values in params.values() for value in values}
            return ScalarRows([
                user for user in self.users if user.is_active
                and (user.username in labels or user.display_name in labels)
            ])
        raise AssertionError(f"未预期的查询：{statement}")

    def add(self, record):
        self.added.append(record)

    def add_all(self, records):
        self.added.extend(records)

    async def flush(self):
        for index, record in enumerate(self.added, start=1000):
            if record.id is None:
                record.id = index

    @property
    def cases(self):
        return [row for row in self.added if isinstance(row, BusinessRecord) and row.module == "case"]


class CaseAutoCreationPeopleValidationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.identity = {"username": "operator", "role": "admin"}
        self.users = [
            User(username="lawyer", display_name="有效律师", is_active=True),
            User(username="assistant", display_name="有效助理", is_active=True),
            User(username="inactive", display_name="停用律师", is_active=False),
            User(username="duplicate1", display_name="同名律师", is_active=True),
            User(username="duplicate2", display_name="同名律师", is_active=True),
        ]
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        # 防止任何未隔离依赖意外连接真实数据库。
        self.patches.enter_context(patch("sqlalchemy.ext.asyncio.AsyncEngine.connect", side_effect=AssertionError("禁止连接数据库")))
        self.patches.enter_context(patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("禁止连接数据库")))

    def record(self, module, record_id, data):
        return BusinessRecord(
            id=record_id, module=module, serial_no=f"CODEX-{module}-{record_id}",
            title="人员校验", customer="测试客户", department="测试部门", owner="operator",
            status="已取证" if module == "clue" else "新案待分配", description="", data=data,
        )

    def mock_async(self, name, **kwargs):
        return self.patches.enter_context(patch(name, new_callable=AsyncMock, **kwargs))

    async def convert(self, clues, **overrides):
        db = CapturingSession(self.users, clues)
        contract = self.record("contract", 90, {})
        self.mock_async("app.core.permissions._record_scope_conditions", return_value=[])
        self.mock_async("app.core.contracts._resolve_clue_source_contract", return_value=(contract, ""))
        self.patches.enter_context(patch("app.core.contracts._contract_allows_downstream_creation", return_value=True))
        self.mock_async("app.core.cases._next_case_serial", side_effect=[f"CODEX-NEW-{i}" for i in range(len(clues))])
        self.mock_async("app.core.crm._persist_case_litigant_customers")
        self.mock_async("app.core.permissions._ensure_case_fixed_tasks")
        body = BatchClueCaseInput(clue_ids=[clue.id for clue in clues], **{"handling_lawyer": "", **overrides})
        return await batch_create_cases_from_clues(body, self.identity, db), db

    def prepare_copy(self, data):
        source = self.record("case", 30, {"case_type": "民事案件", **data})
        db = CapturingSession(self.users)
        self.mock_async("app.core.permissions._ensure_record_module", return_value=source)
        self.mock_async("app.core.cases._case_copy_root", return_value=source)
        self.mock_async("app.core.cases._next_case_copy_serial", return_value="CODEX-COPY-1")
        self.mock_async("app.core.system._allowed_field_keys", return_value=None)
        self.patches.enter_context(patch("app.core.system._record_dict", side_effect=lambda record, _: {"id": record.id, "data": record.data}))
        return source, db

    async def test_clue_invalid_people_return_errors_without_creating_cases(self):
        for name in ["不存在律师", "停用律师", "同名律师"]:
            with self.subTest(name=name):
                clue = self.record("clue", 1, {"handling_lawyers": [name]})
                result, db = await self.convert([clue])
                self.assertEqual((result["created"], result["failed"]), (0, 1))
                error = result["errors"][0]
                self.assertEqual((error["clue_id"], error["clue_no"]), (clue.id, clue.serial_no))
                self.assertIn("经办律师无效", error["error"])
                self.assertIn(name, error["error"])
                self.assertEqual(db.added, [])
                self.assertEqual(clue.status, "已取证")

    async def test_clue_valid_lawyer_writes_resolved_username(self):
        clue = self.record("clue", 1, {"handling_lawyers": ["有效律师"], "handling_lawyer_usernames": ["stale"]})
        result, db = await self.convert([clue])
        self.assertEqual((result["created"], result["failed"]), (1, 0))
        data = db.cases[0].data
        self.assertEqual(data["handling_lawyers"], ["有效律师"])
        self.assertEqual(data["handling_lawyer_usernames"], ["lawyer"])
        self.assertEqual(data["case_team_usernames"], ["lawyer"])
        self.assertEqual(result["created_ids"], [db.cases[0].id])
        self.assertEqual(clue.data["converted_case_id"], db.cases[0].id)
        db.commit.assert_awaited_once()

    async def test_clue_mixed_batch_continues_after_invalid_lawyer_and_assistant(self):
        clues = [
            self.record("clue", 1, {"handling_lawyers": ["不存在律师"]}),
            self.record("clue", 2, {"handling_lawyers": ["有效律师"], "assistant": "不存在助理"}),
            self.record("clue", 3, {"handling_lawyers": ["有效律师"], "assistant": "有效助理", "assistant_username": "stale"}),
        ]
        result, db = await self.convert(clues)
        self.assertEqual((result["created"], result["failed"]), (1, 2))
        self.assertIn("律师助理无效", result["errors"][1]["error"])
        self.assertIn("不存在助理", result["errors"][1]["error"])
        self.assertEqual(db.cases[0].data["clue_id"], 3)
        self.assertEqual(db.cases[0].data["assistant_username"], "assistant")
        self.assertEqual(db.cases[0].data["assistants"], ["有效助理"])

    async def test_clue_empty_lawyer_keeps_required_error(self):
        result, db = await self.convert([self.record("clue", 1, {})])
        self.assertEqual(result["errors"][0]["error"], "生成案件前请填写经办律师")
        self.assertEqual(db.added, [])

    async def test_clue_explicit_people_override_inherited_values(self):
        clue = self.record("clue", 1, {"handling_lawyers": ["不存在律师"], "assistant": "不存在助理"})
        result, db = await self.convert([clue], handling_lawyer="lawyer", assistant="assistant")
        self.assertEqual(result["failed"], 0)
        self.assertEqual(db.cases[0].data["case_team_usernames"], ["lawyer", "assistant"])

    async def test_copy_invalid_lawyer_raises_422_before_adding_records(self):
        for name in ["不存在律师", "停用律师", "同名律师"]:
            with self.subTest(name=name):
                source, db = self.prepare_copy({"handling_lawyers": [name]})
                with self.assertRaises(HTTPException) as caught:
                    await duplicate_case(source.id, self.identity, db)
                self.assertEqual(caught.exception.status_code, 422)
                for text in ["源案件", source.serial_no, "经办律师无效", name, "修正源案件"]:
                    self.assertIn(text, caught.exception.detail)
                self.assertEqual(db.added, [])
                db.commit.assert_not_awaited()

    async def test_copy_valid_lawyer_refreshes_team_and_preserves_source(self):
        source, db = self.prepare_copy({
            "handling_lawyers": ["有效律师"], "handling_lawyer_usernames": ["stale"],
            "assistant": "有效助理", "assistant_username": "stale-assistant", "custom_field": "保留内容",
        })
        original = deepcopy(source.data)
        result = await duplicate_case(source.id, self.identity, db)
        data = db.cases[0].data
        self.assertEqual(result["data"], data)
        self.assertEqual(data["handling_lawyers"], ["有效律师"])
        self.assertEqual(data["handling_lawyer_usernames"], ["lawyer"])
        self.assertEqual(data["assistant_username"], "assistant")
        self.assertEqual(data["case_team_usernames"], ["lawyer", "assistant"])
        self.assertEqual(data["custom_field"], "保留内容")
        self.assertEqual(source.data, original)
        db.commit.assert_awaited_once()

    async def test_copy_invalid_assistant_is_cleared(self):
        source, db = self.prepare_copy({"handling_lawyers": ["有效律师"], "assistant": "不存在助理", "assistant_username": "stale"})
        await duplicate_case(source.id, self.identity, db)
        data = db.cases[0].data
        self.assertEqual(data["assistant"], "")
        self.assertEqual(data["assistants"], [])
        self.assertEqual(data["assistant_username"], "")
        self.assertEqual(data["assistant_usernames"], [])
        self.assertEqual(data["case_team_usernames"], ["lawyer"])

    async def test_copy_assistant_list_keeps_only_valid_entries(self):
        source, db = self.prepare_copy({
            "handling_lawyers": ["有效律师"], "assistants": ["不存在助理", "有效助理", "停用律师", "同名律师"],
            "assistant": "不存在助理", "assistant_usernames": ["stale"],
        })
        original = deepcopy(source.data)
        await duplicate_case(source.id, self.identity, db)
        self.assertEqual(db.cases[0].data["assistants"], ["有效助理"])
        self.assertEqual(db.cases[0].data["assistant_usernames"], ["assistant"])
        self.assertEqual(source.data, original)

    async def test_copy_assistant_service_error_is_not_silently_ignored(self):
        source, db = self.prepare_copy({"handling_lawyers": ["有效律师"], "assistant": "有效助理"})
        original_scalars = db.scalars

        async def fail_assistant_query(statement):
            if "有效助理" in str(statement.compile().params):
                raise HTTPException(status_code=503, detail="人员查询服务不可用")
            return await original_scalars(statement)

        db.scalars = fail_assistant_query
        with self.assertRaises(HTTPException) as caught:
            await duplicate_case(source.id, self.identity, db)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(db.added, [])
        db.commit.assert_not_awaited()

    async def test_copy_empty_team_remains_empty(self):
        source, db = self.prepare_copy({})
        await duplicate_case(source.id, self.identity, db)
        self.assertEqual(db.cases[0].data["handling_lawyers"], [])
        self.assertEqual(db.cases[0].data["assistants"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

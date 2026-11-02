"""BUG20261030017（范文玲 11-02 确认）：新增调查辅助员，可多人、可多条线索，原调查员不变；辅助员能看到、修改、取证。"""
import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, RolePermission, User, WorkflowEvent

ADMIN = {"username": "codexadmin", "display_name": "", "role": "admin", "role_ids": ["admin"], "_actual_role": "admin",
         "_actual_role_ids": ["admin"], "_request_method": "POST", "action_keys": ["*"]}


def staff(username):
    return {"username": username, "display_name": username, "role": "staff", "role_ids": ["staff"], "_actual_role": "staff",
            "_actual_role_ids": ["staff"], "_request_method": "GET"}


class ClueAssistantTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            for username, department, role in (("codexadmin", "CODEX-A", "admin"), ("wangmu", "CODEX-A", "staff"),
                                               ("peihao", "CODEX-B", "staff"), ("hao", "CODEX-B", "staff")):
                db.add(User(username=username, display_name={"wangmu": "王木", "peihao": "裴浩"}.get(username, username),
                            password_hash="isolated-only", department=department, role=role, is_active=True))
            db.add(RolePermission(role="staff", display_name="CODEX-staff", data_scope="本人数据", menu_keys=["clue-my-collect"], field_keys=["*"]))
            db.add(BusinessRecord(id=1, module="clue", serial_no="P22084911", title="线索", status="待取证", owner="wangmu",
                                  department="CODEX-A", data={"investigator": "wangmu"}))
            db.add(BusinessRecord(id=2, module="clue", serial_no="P22084912", title="线索2", status="已取证", owner="wangmu",
                                  department="CODEX-A", data={"investigator": "wangmu", "investigation_assistant": "hao"}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def visible_clues(self, username):
        from app.core.permissions import _record_scope_conditions
        async with self.sessions() as db:
            return set((await db.scalars(select(BusinessRecord.serial_no).where(
                BusinessRecord.module == "clue", *(await _record_scope_conditions(staff(username), db))))).all())

    async def test_set_assistants_keeps_investigator_and_grants_access(self):
        from app.api_schemas.investigation import ClueAssistantInput
        from app.areas.investigation.router import set_clue_assistants
        from app.core.permissions import _require_record_owner_or_manager, clue_assistant_usernames
        self.assertEqual(await self.visible_clues("peihao"), set())
        async with self.sessions() as db:
            await set_clue_assistants(ClueAssistantInput(clue_ids=[1, 2], assistants=["peihao", "peihao"]), ADMIN, db)
        async with self.sessions() as db:
            first, second = await db.get(BusinessRecord, 1), await db.get(BusinessRecord, 2)
            # 原调查员不变；以本次名单为准（2 号原来的 hao 被换掉）；同一人去重。
            self.assertEqual((first.owner, first.data["investigator"]), ("wangmu", "wangmu"))
            self.assertEqual([clue_assistant_usernames(first.data), clue_assistant_usernames(second.data)], [["peihao"], ["peihao"]])
            self.assertEqual(first.data["investigation_assistant_display_name"], "裴浩")
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action == "设置调查辅助员"))).all()
            self.assertEqual(len(events), 2)
            # 辅助员和调查员一样可以修改、取证。
            await _require_record_owner_or_manager(first, {**staff("peihao"), "_request_method": "POST"}, db)
            with self.assertRaises(HTTPException):
                await _require_record_owner_or_manager(first, {**staff("hao"), "_request_method": "POST"}, db)
        self.assertEqual(await self.visible_clues("peihao"), {"P22084911", "P22084912"})
        # 按整个账号比：hao 不会因为 peihao 含 hao 就看到。
        self.assertEqual(await self.visible_clues("hao"), set())

    async def test_empty_list_clears_assistants(self):
        from app.api_schemas.investigation import ClueAssistantInput
        from app.areas.investigation.router import set_clue_assistants
        async with self.sessions() as db:
            await set_clue_assistants(ClueAssistantInput(clue_ids=[2], assistants=[]), ADMIN, db)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, 2)).data["investigation_assistant"], "")

    def test_case_investigators_include_assistants(self):
        from app.core.permissions import clue_assistant_usernames
        data = {"investigator": "wangmu", "investigation_assistant": "peihao、liubo"}
        joined = ",".join(dict.fromkeys([data.get("investigator"), *clue_assistant_usernames(data)]))
        self.assertEqual(joined, "wangmu,peihao,liubo")


if __name__ == "__main__":
    unittest.main()

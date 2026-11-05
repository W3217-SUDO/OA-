"""501631（tgn 11-05 22:45）：归档类案件只有真实系统管理员能用“分配”增减本案人员，记日志、不改阶段；
管理员离职转交时，接收人不是本案人员就自动加进案件“律师助理”栏。"""
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "上海分所"}
# 有页面权限被提升成 admin、但真实角色不是管理员的人
ELEVATED = {"username": "boss", "role": "admin", "role_ids": ["admin"], "_actual_role": "manager", "_actual_role_ids": ["manager"], "display_name": "部长", "department": "上海分所"}


class ArchivedCasePeopleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for username, name, active in (("admin", "管理者", True), ("boss", "部长", True), ("lawyer", "律师甲", True), ("gone", "离职乙", False), ("newbie", "王五", True)):
                db.add(User(username=username, display_name=name, department="上海分所", password_hash="x", role="admin" if username == "admin" else "user", is_active=active))
            case = BusinessRecord(module="case", serial_no="HZMS2600115", title="案", status="已归档", owner="lawyer", department="上海分所",
                                  data={"case_type": "民事案件", "hearing_lawyer": "律师甲", "handling_lawyers": ["律师甲"], "handling_lawyer_usernames": ["lawyer"],
                                        "assistant": "离职乙", "assistants": ["离职乙"], "assistant_username": "gone", "assistant_usernames": ["gone"]})
            db.add(case); await db.flush()
            task = BusinessRecord(module="task", serial_no="HZ-CT-17088", title="结算归档任务", status="处理中", owner="gone", department="上海分所",
                                  data={"initiator": "gone", "collaborators": ["gone"], "case_no": "HZMS2600115", "case_record_id": case.id})
            db.add(task); await db.commit()
            self.case_id, self.task_id = case.id, task.id
        app.dependency_overrides[get_db] = self._db
        self.identity = ADMIN
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://archived.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()

    async def test_only_actual_admin_can_reassign_archived_case(self):
        body = {"hearing_lawyer": "律师甲", "handling_lawyers": ["lawyer"], "assistants": ["gone", "newbie"], "customer_manager": "", "comment": "补人"}
        self.identity = ELEVATED
        blocked = await self.client.post(f"{API}/cases/{self.case_id}/assign", json=body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertIn("只有系统管理员", blocked.json()["detail"])

        self.identity = ADMIN
        response = await self.client.post(f"{API}/cases/{self.case_id}/assign", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            self.assertEqual(case.status, "已归档", "不改阶段")
            self.assertEqual(case.data["assistant_usernames"], ["newbie"], "离职的助理只保留显示名，新加的人有账号")
            self.assertEqual(case.data["assistants"], ["离职乙", "王五"])
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id, WorkflowEvent.action == "归档案件调整本案人员"))
            self.assertIn("改前", event.comment); self.assertIn("王五", event.comment)

    async def test_capability_lets_admin_assign_archived(self):
        from app.core.permissions import _case_detail_action_capabilities
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            self.assertTrue((await _case_detail_action_capabilities(case, ADMIN, db))["can_assign_team"])
            self.assertFalse((await _case_detail_action_capabilities(case, ELEVATED, db))["can_assign_team"])

    async def test_admin_handover_auto_adds_assistant(self):
        response = await self.client.post(f"{API}/hr/departure-tasks/handover", json={"from_username": "gone", "recipient": "newbie", "task_ids": [self.task_id]})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            self.assertIn("newbie", case.data["assistant_usernames"])
            self.assertEqual(case.status, "已归档")
            self.assertEqual((await db.get(BusinessRecord, self.task_id)).owner, "newbie")
            self.assertIsNotNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id, WorkflowEvent.action == "自动加入律师助理")))

    async def test_non_admin_handover_still_requires_member(self):
        self.identity = {"username": "boss", "role": "manager", "role_ids": ["manager"], "display_name": "部长", "department": "上海分所"}
        response = await self.client.post(f"{API}/hr/departure-tasks/handover", json={"from_username": "gone", "recipient": "newbie", "task_ids": [self.task_id]})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("本案人员", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()

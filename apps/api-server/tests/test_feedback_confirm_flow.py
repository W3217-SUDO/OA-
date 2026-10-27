"""问题处理中心：修改前提交人点“确认修改”（2026-10-27 用户要求）。

状态仍是 待处理 → 待验证 → 已解决；“确认修改”只记一条处理记录并通知，状态不变。
被指派的处理人也能替提交人确认（如非诉问题由指定的人确认）。
"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.system import feedback
from app.core import soft_delete
from app.core.dependencies import current_identity, get_db
from app.database import Base
from app.models import Notification, User, WorkflowEvent

ADMIN = {"username": "CODEXFCADMIN", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "确认流程管理员", "department": "CODEXFC"}
STAFF = {"username": "CODEXFCSTAFF", "role": "staff", "role_ids": ["staff"], "_actual_role_ids": ["staff"],
         "display_name": "确认流程提交人", "department": "CODEXFC"}
DECIDER = {"username": "CODEXFCDECIDER", "role": "staff", "role_ids": ["staff"], "_actual_role_ids": ["staff"],
           "display_name": "确认流程决定人", "department": "CODEXFC"}
API = "/api/v1/feedback"


class FeedbackConfirmFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add_all([User(username=item["username"], display_name=item["display_name"], password_hash="isolated-only",
                             department="CODEXFC", role=item["role"]) for item in (ADMIN, STAFF, DECIDER)])
            await db.commit()
        self.identity = dict(STAFF)
        app = FastAPI()
        app.include_router(feedback.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")
        created = await self.client.post(f"{API}/submit", json={"description": "CODEXFC 表头换行", "page": "工作台"})
        self.assertEqual(created.status_code, 200, created.text)
        self.feedback_id = created.json()["id"]

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _actions(self):
        response = await self.client.get(f"{API}/{self.feedback_id}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["available_actions"]

    async def _transition(self, action, comment=""):
        return await self.client.post(f"{API}/{self.feedback_id}/transitions", json={"action": action, "comment": comment})

    async def test_reporter_confirms_without_changing_status_then_handler_finishes(self):
        self.identity = dict(STAFF)
        self.assertEqual(await self._actions(), ["确认修改"])
        confirmed = await self._transition("确认修改")
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json(), {"status": "待处理"})
        async with self.sessions() as db:
            events = (await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.feedback_id, WorkflowEvent.action == "确认修改"))).all()
            self.assertEqual([(e.from_status, e.to_status, e.operator) for e in events], [("待处理", "待处理", STAFF["username"])])
            notices = (await db.scalars(select(Notification).where(Notification.source_id == self.feedback_id))).all()
            self.assertTrue(any(n.recipient == ADMIN["username"] and "确认修改" in n.title for n in notices))

        self.identity = dict(ADMIN)
        self.assertEqual(await self._actions(), ["处理完成，请验证"])
        self.assertEqual((await self._transition("确认修改")).status_code, 403)
        self.assertEqual((await self._transition("处理完成，请验证", "已修复")).json(), {"status": "待验证"})

        self.identity = dict(STAFF)
        self.assertEqual(await self._actions(), ["验证通过", "未解决，重新打开"])
        self.assertEqual((await self._transition("确认修改")).status_code, 409)

    async def test_assignee_can_confirm_for_reporter(self):
        self.identity = dict(DECIDER)
        self.assertEqual((await self.client.get(f"{API}/{self.feedback_id}")).status_code, 404)
        self.identity = dict(ADMIN)
        assigned = await self.client.put(f"{API}/{self.feedback_id}/assignee", json={"username": DECIDER["username"]})
        self.assertEqual(assigned.status_code, 200, assigned.text)
        self.identity = dict(DECIDER)
        self.assertEqual(await self._actions(), ["处理完成，请验证", "确认修改"])
        self.assertEqual((await self._transition("确认修改")).json(), {"status": "待处理"})


if __name__ == "__main__":
    unittest.main()

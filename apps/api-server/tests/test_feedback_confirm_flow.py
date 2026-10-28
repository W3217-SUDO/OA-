"""问题处理中心：修改前提交人确认（2026-10-27 用户要求；2026-10-28 加“待确认”状态）。

待处理 →（处理人“请确认修改方案”，写明怎么改）待确认 →（提交人“确认修改”）待处理 →（处理完成）待验证 → 已解决。
提交人在待确认时有意见直接回复，状态留在待确认；被指派的处理人也能替提交人确认（如非诉问题由指定的人确认）。
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

    async def test_plan_waits_for_reporter_confirmation_then_handler_finishes(self):
        self.identity = dict(STAFF)
        self.assertEqual(await self._actions(), [])
        self.assertEqual((await self._transition("确认修改")).status_code, 409)

        self.identity = dict(ADMIN)
        self.assertEqual(await self._actions(), ["请确认修改方案", "处理完成，请验证"])
        self.assertEqual((await self._transition("请确认修改方案")).status_code, 422)
        planned = await self._transition("请确认修改方案", "表头一律单行")
        self.assertEqual(planned.json(), {"status": "待确认"})
        self.assertEqual(await self._actions(), [])

        # 提交人有意见直接回复，状态还是待确认。
        self.identity = dict(STAFF)
        self.assertEqual(await self._actions(), ["确认修改"])
        replied = await self.client.post(f"{API}/{self.feedback_id}/replies", json={"content": "四个字的可以两行"})
        self.assertEqual(replied.json()["status"], "待确认")
        confirmed = await self._transition("确认修改")
        self.assertEqual(confirmed.json(), {"status": "待处理"})
        async with self.sessions() as db:
            events = (await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.feedback_id, WorkflowEvent.action.in_(["请确认修改方案", "确认修改"]))
                .order_by(WorkflowEvent.id))).all()
            self.assertEqual([(e.action, e.from_status, e.to_status) for e in events],
                             [("请确认修改方案", "待处理", "待确认"), ("确认修改", "待确认", "待处理")])
            notices = (await db.scalars(select(Notification).where(Notification.source_id == self.feedback_id))).all()
            self.assertTrue(any(n.recipient == ADMIN["username"] and "确认修改" in n.title for n in notices))

        self.identity = dict(ADMIN)
        self.assertEqual((await self._transition("确认修改")).status_code, 403)
        self.assertEqual((await self._transition("处理完成，请验证", "已修复")).json(), {"status": "待验证"})

        self.identity = dict(STAFF)
        self.assertEqual(await self._actions(), ["验证通过", "未解决，重新打开"])
        self.assertEqual((await self._transition("确认修改")).status_code, 409)

    async def test_status_counts_include_pending_confirmation(self):
        self.identity = dict(ADMIN)
        await self._transition("请确认修改方案", "打算这样改")
        counts = (await self.client.get(f"{API}/status-counts")).json()
        self.assertEqual(list(counts["counts"]), ["待处理", "待确认", "待验证", "已解决"])
        self.assertEqual(counts["counts"]["待确认"], 1)
        self.identity = dict(STAFF)
        mine = (await self.client.get(f"{API}/status-counts", params={"mine": True})).json()
        self.assertEqual(mine["counts"]["待确认"], 1)
        listed = (await self.client.get(API, params={"status": "待确认", "mine": True})).json()
        self.assertEqual([item["id"] for item in listed["items"]], [self.feedback_id])

    async def test_assignee_can_confirm_for_reporter(self):
        self.identity = dict(DECIDER)
        self.assertEqual((await self.client.get(f"{API}/{self.feedback_id}")).status_code, 404)
        self.identity = dict(ADMIN)
        assigned = await self.client.put(f"{API}/{self.feedback_id}/assignee", json={"username": DECIDER["username"]})
        self.assertEqual(assigned.status_code, 200, assigned.text)
        await self._transition("请确认修改方案", "打算这样改")
        self.identity = dict(DECIDER)
        self.assertEqual(await self._actions(), ["确认修改"])
        self.assertEqual((await self._transition("确认修改")).json(), {"status": "待处理"})


    async def test_bot_replies_show_as_assistant_and_roles_are_marked(self):
        """自动化用 feedback-bot 身份回复，显示为“问题处理助手”，与管理者本人区分；权限按管理员。"""
        self.identity = dict(feedback.FEEDBACK_BOT_IDENTITY)
        bot_reply = await self.client.post(f"{API}/{self.feedback_id}/replies", json={"content": "打算这样改"})
        self.assertEqual(bot_reply.status_code, 200, bot_reply.text)
        self.identity = dict(ADMIN)
        await self.client.post(f"{API}/{self.feedback_id}/replies", json={"content": "管理者补充"})
        self.identity = dict(STAFF)
        await self.client.post(f"{API}/{self.feedback_id}/replies", json={"content": "好的"})
        self.identity = dict(ADMIN)
        events = (await self.client.get(f"{API}/{self.feedback_id}")).json()["events"]
        speakers = [(e["action"], e["operator_display_name"], e["operator_role"]) for e in events]
        self.assertEqual(speakers, [
            ("提交反馈", "确认流程提交人", "reporter"),
            ("回复", "问题处理助手", "bot"),
            ("回复", "确认流程管理员", "admin"),
            ("回复", "确认流程提交人", "reporter"),
        ])
        self.identity = dict(feedback.FEEDBACK_BOT_IDENTITY)
        done = await self._transition("处理完成，请验证", "已修复")
        self.assertEqual(done.json(), {"status": "待验证"})


if __name__ == "__main__":
    unittest.main()

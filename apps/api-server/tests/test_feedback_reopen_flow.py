"""问题处理中心：待验证时“还有问题”转回待处理（陶威 11-01 定）。

原：修改前提交人确认（2026-10-27 用户要求；2026-10-28 加“待确认”状态）。

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


class FeedbackReopenFlowTest(unittest.IsolatedAsyncioTestCase):
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

    async def _to_verify(self):
        self.identity = dict(ADMIN)
        done = await self._transition("处理完成，请验证", "已改好")
        self.assertEqual(done.json(), {"status": "待验证"}, done.text)

    async def test_reporter_reply_keeps_status_and_marks_new_reply(self):
        await self._to_verify()
        self.identity = dict(STAFF)
        self.assertIn("未解决，重新打开", await self._actions())
        replied = await self.client.post(f"{API}/{self.feedback_id}/messages", data={"content": "好的，谢谢"})
        self.assertIn(replied.status_code, (200, 201), replied.text)
        self.identity = dict(ADMIN)
        detail = (await self.client.get(f"{API}/{self.feedback_id}")).json()
        self.assertEqual((detail["status"], detail["reporter_new_reply"]), ("待验证", True))
        listed = (await self.client.get(API)).json()["items"]
        self.assertTrue(next(item for item in listed if item["id"] == self.feedback_id)["reporter_new_reply"])
        # 处理人回复后标记清掉。
        await self.client.post(f"{API}/{self.feedback_id}/messages", data={"content": "收到"})
        self.assertFalse((await self.client.get(f"{API}/{self.feedback_id}")).json()["reporter_new_reply"])

    async def test_only_reporter_bot_and_admin_account_can_reopen(self):
        await self._to_verify()
        # 普通处理人（哪怕是管理员角色）不能代提交人转回。
        self.identity = dict(ADMIN)
        self.assertNotIn("未解决，重新打开", await self._actions())
        self.assertIn((await self._transition("未解决，重新打开", "代转")).status_code, (403, 409))
        # 问题处理助手可以，必须写依据。
        self.identity = dict(feedback.FEEDBACK_BOT_IDENTITY)
        self.assertIn("未解决，重新打开", await self._actions())
        self.assertEqual((await self._transition("未解决，重新打开")).status_code, 422)
        reopened = await self._transition("未解决，重新打开", "提交人 15:30 回复提了新需求：表头加粗")
        self.assertEqual(reopened.json(), {"status": "待处理"}, reopened.text)

    async def test_admin_account_can_reopen(self):
        await self._to_verify()
        self.identity = {**ADMIN, "username": "admin"}
        reopened = await self._transition("未解决，重新打开", "提交人在回复里说没解决")
        self.assertEqual(reopened.json(), {"status": "待处理"}, reopened.text)


    async def test_my_feedback_groups_open_and_closed(self):
        """BUG20261101005：我的反馈分“处理中”“已解决”，已撤回放进已解决。"""
        self.identity = dict(STAFF)
        open_ids = [item["id"] for item in (await self.client.get(API, params={"mine": True, "group": "open"})).json()["items"]]
        self.assertIn(self.feedback_id, open_ids)
        await self._to_verify()
        self.identity = dict(STAFF)
        self.assertEqual((await self._transition("验证通过")).json(), {"status": "已解决"})
        open_ids = [item["id"] for item in (await self.client.get(API, params={"mine": True, "group": "open"})).json()["items"]]
        closed_ids = [item["id"] for item in (await self.client.get(API, params={"mine": True, "group": "closed"})).json()["items"]]
        self.assertNotIn(self.feedback_id, open_ids)
        self.assertIn(self.feedback_id, closed_ids)
        self.assertEqual((await self.client.get(API, params={"group": "other"})).status_code, 422)


if __name__ == "__main__":
    unittest.main()

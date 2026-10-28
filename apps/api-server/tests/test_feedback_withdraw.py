"""问题反馈撤回（陶威 2026-10-28）：“没有动手改之前可以撤回，改了就不能撤回”。

只有提交人本人能撤回（管理员、被指派的处理人都不能替别人撤回）；待确认、从未确认修改过的待处理能撤回，
确认修改后的待处理、待验证（含旧“已处理”）、已解决不能（409“已开始修改，不能撤回”）；
撤回记一条“撤回”处理记录并通知其他参与人，不删数据；撤回后只读，也不能重新打开。
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
from app.models import BusinessRecord, Notification, User, WorkflowEvent

ADMIN = {"username": "CODEXFWADMIN", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "撤回管理员", "department": "CODEXFW"}
STAFF = {"username": "CODEXFWSTAFF", "role": "staff", "role_ids": ["staff"], "_actual_role_ids": ["staff"],
         "display_name": "撤回提交人", "department": "CODEXFW"}
HANDLER = {"username": "CODEXFWHANDLER", "role": "staff", "role_ids": ["staff"], "_actual_role_ids": ["staff"],
           "display_name": "撤回处理人", "department": "CODEXFW"}
API = "/api/v1/feedback"


class FeedbackWithdrawTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add_all([User(username=item["username"], display_name=item["display_name"], password_hash="isolated-only",
                             department="CODEXFW", role=item["role"]) for item in (ADMIN, STAFF, HANDLER)])
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
        self.feedback_id = await self._create()

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _create(self):
        self.identity = dict(STAFF)
        created = await self.client.post(f"{API}/submit", json={"description": "CODEXFW 列表错位", "page": "工作台"})
        self.assertEqual(created.status_code, 200, created.text)
        return created.json()["id"]

    async def _detail(self, feedback_id=None):
        response = await self.client.get(f"{API}/{feedback_id or self.feedback_id}")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def _transition(self, action, comment="", feedback_id=None):
        return await self.client.post(f"{API}/{feedback_id or self.feedback_id}/transitions",
                                      json={"action": action, "comment": comment})

    async def _set_status(self, status, feedback_id=None):
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, feedback_id or self.feedback_id)
            record.status = status
            await db.commit()

    async def test_only_owner_can_withdraw(self):
        self.identity = dict(ADMIN)
        self.assertEqual((await self.client.put(f"{API}/{self.feedback_id}/assignee", json={"username": HANDLER["username"]})).status_code, 200)
        detail = await self._detail()
        self.assertFalse(detail["can_withdraw"])
        self.assertNotIn("撤回", detail["available_actions"])
        self.assertEqual((await self._transition("撤回")).status_code, 403)
        self.identity = dict(HANDLER)
        self.assertFalse((await self._detail())["can_withdraw"])
        self.assertEqual((await self._transition("撤回")).status_code, 403)

        self.identity = dict(STAFF)
        detail = await self._detail()
        self.assertTrue(detail["can_withdraw"])
        # 撤回是页头按钮，不混在聊天框下面的状态操作里。
        self.assertNotIn("撤回", detail["available_actions"])
        withdrawn = await self._transition("撤回", "已经自己解决了")
        self.assertEqual(withdrawn.json(), {"status": "已撤回"})

        async with self.sessions() as db:
            event = (await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.feedback_id, WorkflowEvent.action == "撤回"))).one()
            self.assertEqual((event.from_status, event.to_status, event.operator, event.comment),
                             ("待处理", "已撤回", STAFF["username"], "已经自己解决了"))
            recipients = set((await db.scalars(select(Notification.recipient).where(
                Notification.source_id == self.feedback_id, Notification.title.contains("撤回")))).all())
            self.assertEqual(recipients, {HANDLER["username"]})
            self.assertIsNotNone(await db.get(BusinessRecord, self.feedback_id))

    async def test_admin_can_withdraw_own_feedback(self):
        self.identity = dict(ADMIN)
        created = await self.client.post(f"{API}/submit", json={"description": "CODEXFW 管理员自己的问题", "page": "工作台"})
        own_id = created.json()["id"]
        self.assertTrue((await self._detail(own_id))["can_withdraw"])
        self.assertEqual((await self._transition("撤回", feedback_id=own_id)).json(), {"status": "已撤回"})

    async def _assert_cannot_withdraw(self, feedback_id=None):
        self.identity = dict(STAFF)
        self.assertFalse((await self._detail(feedback_id))["can_withdraw"])
        refused = await self._transition("撤回", feedback_id=feedback_id)
        self.assertEqual((refused.status_code, refused.json()["detail"]), (409, "已开始修改，不能撤回"))

    async def test_withdraw_only_before_work_starts(self):
        # 处理人写了方案待确认：还没动手，可以撤回。
        self.identity = dict(ADMIN)
        self.assertEqual((await self._transition("请确认修改方案", "表头改单行")).status_code, 200)
        self.identity = dict(STAFF)
        self.assertTrue((await self._detail())["can_withdraw"])
        # 提交人确认修改后回到待处理，已经开始改了，不能撤回。
        self.assertEqual((await self._transition("确认修改")).status_code, 200)
        await self._assert_cannot_withdraw()
        # 处理完成待验证、验证通过已解决都不能撤回。
        self.identity = dict(ADMIN)
        self.assertEqual((await self._transition("处理完成，请验证")).status_code, 200)
        await self._assert_cannot_withdraw()
        self.assertEqual((await self._transition("验证通过")).status_code, 200)
        await self._assert_cannot_withdraw()

    async def test_reopened_or_legacy_handled_cannot_withdraw(self):
        # 处理人没写方案直接报处理完成，提交人重新打开回到待处理：改过了，不能撤回。
        self.identity = dict(ADMIN)
        self.assertEqual((await self._transition("处理完成，请验证")).status_code, 200)
        self.identity = dict(STAFF)
        self.assertEqual((await self._transition("未解决，重新打开", "还是错位")).status_code, 200)
        self.assertEqual((await self._detail())["status"], "待处理")
        await self._assert_cannot_withdraw()
        # 旧状态“已处理”按待验证算，不能撤回。
        legacy_id = await self._create()
        await self._set_status("已处理", legacy_id)
        await self._assert_cannot_withdraw(legacy_id)

    async def test_withdrawn_is_read_only_and_cannot_reopen(self):
        self.assertEqual((await self._transition("撤回")).status_code, 200)
        detail = await self._detail()
        self.assertEqual((detail["status"], detail["available_actions"], detail["can_withdraw"]), ("已撤回", [], False))
        for action in ("撤回", "未解决，重新打开", "验证通过", "确认修改"):
            self.assertEqual((await self._transition(action, "再看看")).status_code, 409, action)
        self.assertEqual((await self.client.post(f"{API}/{self.feedback_id}/replies", json={"content": "补充"})).status_code, 409)
        self.assertEqual((await self.client.post(f"{API}/{self.feedback_id}/messages", data={"content": "补充"})).status_code, 409)
        self.assertEqual((await self.client.post(f"{API}/{self.feedback_id}/files", params={"name": "a.txt"}, content=b"x")).status_code, 409)

        self.identity = dict(ADMIN)
        self.assertEqual((await self._detail())["available_actions"], [])
        for action in ("请确认修改方案", "处理完成，请验证"):
            self.assertEqual((await self._transition(action, "改好了")).status_code, 409, action)
        self.assertEqual((await self.client.put(f"{API}/{self.feedback_id}/assignee", json={"username": HANDLER["username"]})).status_code, 409)

    async def test_status_tab_and_filter_and_pending_counts(self):
        await self._create()
        self.assertEqual((await self._transition("撤回")).status_code, 200)
        self.identity = dict(ADMIN)
        counts = (await self.client.get(f"{API}/status-counts")).json()
        self.assertEqual((counts["counts"]["已撤回"], counts["counts"]["待处理"], counts["total"]), (1, 1, 2))
        listed = (await self.client.get(API, params={"status": "已撤回"})).json()
        self.assertEqual([item["id"] for item in listed["items"]], [self.feedback_id])
        self.identity = dict(STAFF)
        mine = (await self.client.get(f"{API}/status-counts", params={"mine": True})).json()
        self.assertEqual(mine["counts"]["已撤回"], 1)
        # 首页“问题反馈”待处理数只算待处理，不含已撤回。
        from app.core.dashboard_portals import _feedback_count
        async with self.sessions() as db:
            self.assertEqual(await _feedback_count("待处理", db), 1)

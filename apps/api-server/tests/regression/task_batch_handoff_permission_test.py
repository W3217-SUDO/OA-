"""批量交接和单条转交、前端批量菜单一样，要有“任务转交”功能；只有“批量修改”不够（501742 审查）。真实令牌，不替换 current_identity。"""
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.data_scope_gate import reset_gate_cache
from app.data_models.identity import JobRole
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import create_token, hash_password

API = settings.api_prefix


def person(username, role_name):
    return User(username=username, display_name=username, department="事务部", role="user", role_ids=["user"], is_active=True,
                password_hash=hash_password("FakeRev#12345678"), profile={"permission_role": role_name})


class BatchHandoffPermissionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                # 只有“批量修改”，没有任务页面带出的“任务转交”
                JobRole(code="R-BATCH", name="只批量", permissions=["dashboard", "action:task.batch.update"], field_keys=[], is_active=True),
                # 有任务页面：页面带出“任务转交”
                JobRole(code="R-TASK", name="有任务页", permissions=["task-my", "action:task.batch.update"], field_keys=[], is_active=True),
                person("batchonly", "只批量"), person("taskpage", "有任务页"), person("receiver", "有任务页"),
            ])
            for owner in ("batchonly", "taskpage"):
                db.add(BusinessRecord(module="task", serial_no=f"T-{owner}", title="任务", status="处理中", owner=owner, department="事务部",
                                      customer="", description="", data={"initiator": owner, "assignee": owner}))
            await db.commit()
            self.ids = {row.owner: row.id for row in (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()}

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()
        reset_gate_cache()

    async def batch(self, username, action, **extra):
        return await self.client.post(f"{API}/tasks/batch-lifecycle", headers={"Authorization": "Bearer " + create_token(username, "user", 30)},
                                      json={"task_ids": [self.ids[username]], "action": action, **extra})

    async def test_handoff_needs_handoff_action(self):
        response = await self.batch("batchonly", "handoff", recipient="receiver")
        self.assertEqual(response.status_code, 403, response.text)

    async def test_task_page_still_hands_off(self):
        response = await self.batch("taskpage", "handoff", recipient="receiver")
        self.assertNotEqual(response.status_code, 403, response.text)

    async def test_other_batch_actions_unchanged(self):
        response = await self.batch("batchonly", "withdraw", comment="不需要了")
        self.assertNotEqual(response.status_code, 403, "只补交接的检查，其他批量动作不变：" + response.text)


if __name__ == "__main__":
    unittest.main()

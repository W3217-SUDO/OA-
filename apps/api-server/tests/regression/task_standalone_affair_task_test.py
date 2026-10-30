"""任务中心直接新建“事务性任务”：不关联案件也能发给负责人；关联案件即为案件任务。"""

from __future__ import annotations

from datetime import date, timedelta
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, User
from app.security import current_identity
from tests.personnel_role_fixture import bind_system_role_pages


API = settings.api_prefix
INITIATOR = {"username": "affair-initiator", "role": "user", "display_name": "发起人", "department": "行政部"}
OWNER = {"username": "affair-owner", "role": "user", "display_name": "负责人", "department": "行政部"}


class StandaloneAffairTaskTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = INITIATOR
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=user["username"], display_name=user["display_name"], department=user["department"],
                     role="user", password_hash="x", is_active=True)
                for user in (INITIATOR, OWNER)
            ])
            # 只有任务中心菜单、没有案件任务权限的普通员工。
            db.add(RolePermission(role="user", display_name="普通员工", data_scope="本人及共享数据",
                                  menu_keys=["task", "task-my"], field_keys=[]))
            case = BusinessRecord(
                module="case", serial_no="CODEX-AFFAIR-CASE", title="事务任务测试案件", customer="测试客户",
                status="办理中", owner="someone-else", department="诉讼部", data={},
            )
            db.add(case)
            await db.commit()
            self.case_id = case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://affair.test")
        await bind_system_role_pages(self.sessions)

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    def body(self, **extra) -> dict:
        return {"title": "整理本月用印台账", "owner": OWNER["username"], "collaborators": [],
                "deadline": str(date.today() + timedelta(days=3)), "priority": "普通",
                "source": "事务性任务", "description": "行政事务", **extra}

    async def test_affair_task_without_case_goes_to_owner(self) -> None:
        created = await self.client.post(f"{API}/tasks", json=self.body())
        self.assertEqual(created.status_code, 201, created.text)
        task = created.json()
        self.assertEqual(task["status"], "待接收")
        async with self.sessions() as db:
            stored = await db.get(BusinessRecord, task["id"])
            self.assertEqual(stored.data["source"], "事务性任务")
            self.assertEqual(stored.data["case_nos"], [])
            self.assertIsNone(stored.data["case_id"])
            self.assertEqual(stored.owner, OWNER["username"])

        self.identity = OWNER
        accepted = await self.client.get(f"{API}/tasks", params={"scope": "mine", "relation": "owned"})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertIn(task["id"], [item["id"] for item in accepted.json()["items"]])

    async def test_linking_a_case_makes_it_a_case_task_and_keeps_case_permission(self) -> None:
        # 填了案件就按案件任务处理，仍要求案件任务权限；没有权限不能借事务性任务绕过。
        denied = await self.client.post(f"{API}/tasks", json=self.body(case_record_id=self.case_id, case_module="case"))
        self.assertIn(denied.status_code, {403, 404}, denied.text)
        async with self.sessions() as db:
            tasks = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()
            self.assertEqual(tasks, [])

    async def test_empty_source_without_case_defaults_to_affair_task(self) -> None:
        created = await self.client.post(f"{API}/tasks", json=self.body(source=""))
        self.assertEqual(created.status_code, 201, created.text)
        async with self.sessions() as db:
            stored = await db.get(BusinessRecord, created.json()["id"])
            self.assertEqual(stored.data["source"], "事务性任务")


if __name__ == "__main__":
    unittest.main()

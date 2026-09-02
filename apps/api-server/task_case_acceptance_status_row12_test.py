"""9.1 row 12: recipient acceptance controls a case task's workflow state."""

from __future__ import annotations

from datetime import date, timedelta
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
INITIATOR = {"username": "row12-initiator", "role": "user", "display_name": "发起人", "department": "诉讼部"}
OWNER = {"username": "row12-owner", "role": "user", "display_name": "负责人", "department": "诉讼部"}


class TaskCaseAcceptanceStatusRow12Test(unittest.IsolatedAsyncioTestCase):
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
                User(username=user["username"], display_name=user["display_name"], department=user["department"], role="user", password_hash="x", is_active=True)
                for user in (INITIATOR, OWNER)
            ])
            case = BusinessRecord(
                module="case", serial_no="CODEX-901-R12-CASE", title="第十二行案件", customer="第十二行客户",
                status="办理中", owner=INITIATOR["username"], department=INITIATOR["department"],
                data={"case_team_usernames": [INITIATOR["username"]], "handling_lawyer_usernames": [INITIATOR["username"]]},
            )
            db.add(case)
            await db.commit()
            self.case_id = case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row12.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_owner_accepts_before_case_task_enters_processing(self) -> None:
        created = await self.client.post(f"{API}/tasks", json={
            "title": "第十二行案件任务", "customer": "ignored", "owner": OWNER["username"], "collaborators": [],
            "case_record_id": self.case_id, "case_module": "case",
            "deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "案件任务", "description": "计时已开始",
        })
        self.assertEqual(created.status_code, 201, created.text)
        task_id = created.json()["id"]
        self.assertEqual(created.json()["workflow_status"], "待处理")

        initiated = await self.client.get(f"{API}/tasks", params={"scope": "mine", "relation": "initiated"})
        self.assertEqual(initiated.json()["items"][0]["status"], "进行中")
        self.assertEqual(initiated.json()["items"][0]["workflow_status"], "待处理")

        case_tasks = await self.client.get(f"{API}/cases/{self.case_id}/tasks")
        self.assertEqual(case_tasks.json()["items"][0]["status"], "进行中")
        self.assertEqual(case_tasks.json()["items"][0]["workflow_status"], "待处理")

        rejected = await self.client.post(
            f"{API}/tasks/{task_id}/accept",
            json={"comment": "发起人不得代替负责人接受"},
        )
        self.assertEqual(rejected.status_code, 403, rejected.text)
        unchanged = await self.client.get(f"{API}/tasks", params={"scope": "mine", "relation": "initiated"})
        self.assertEqual(unchanged.json()["items"][0]["workflow_status"], "待处理")

        self.identity = OWNER
        owned = await self.client.get(f"{API}/tasks", params={"scope": "mine", "relation": "owned"})
        self.assertEqual(owned.json()["summary"]["pending"], 1)
        self.assertEqual(owned.json()["summary"]["processing"], 0)
        self.assertEqual(owned.json()["items"][0]["status"], "待处理")

        accepted = await self.client.post(f"{API}/tasks/{task_id}/accept", json={"comment": "接受案件任务"})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["workflow_status"], "处理中")
        self.assertTrue(accepted.json()["accepted_at"])

        refreshed = await self.client.get(f"{API}/tasks", params={"scope": "mine", "relation": "owned"})
        self.assertEqual(refreshed.json()["summary"]["pending"], 0)
        self.assertEqual(refreshed.json()["summary"]["processing"], 1)
        self.assertEqual(refreshed.json()["items"][0]["status"], "进行中")


if __name__ == "__main__":
    unittest.main()

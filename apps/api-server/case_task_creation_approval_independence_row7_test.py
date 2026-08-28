"""8.13 row 7: case tasks can be published before creation approval."""

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
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row7-admin", "role": "admin", "display_name": "Row7 Admin", "department": "诉讼部"}


class CaseTaskCreationApprovalIndependenceRow7Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=ADMIN["username"], display_name=ADMIN["display_name"],
                department=ADMIN["department"], role="admin", password_hash="x", is_active=True,
            ))
            db.add_all([
                self._case("ROW7-PENDING", "待立案审批"),
                self._case("ROW7-HISTORICAL", "新案待分配", creation_step="basic"),
                self._case("ROW7-ARCHIVED", "已归档"),
            ])
            await db.flush()
            self.pending_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW7-PENDING"))
            self.historical_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW7-HISTORICAL"))
            self.archived_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW7-ARCHIVED"))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row7.test")

    @staticmethod
    def _case(serial_no: str, status: str, *, creation_step: str = "completed") -> BusinessRecord:
        return BusinessRecord(
            module="case", serial_no=serial_no, title=serial_no, customer="Row 7 Customer",
            status=status, owner=ADMIN["username"], department=ADMIN["department"],
            data={
                "case_type": "民事案件", "case_creation_step": creation_step,
                "case_creation_approval_status": "待审批",
                "handling_lawyer_usernames": [ADMIN["username"]],
                "case_team_usernames": [ADMIN["username"]],
            },
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_pending_approval_exposes_and_persists_case_task(self) -> None:
        capabilities = await self.client.get(f"{API}/cases/{self.pending_id}/action-capabilities")
        self.assertEqual(capabilities.status_code, 200, capabilities.text)
        self.assertTrue(capabilities.json()["can_write"])
        self.assertTrue(capabilities.json()["can_create_case_task"])

        created = await self.client.post(f"{API}/tasks", json={
            "title": "ROW7 browser task", "customer": "ignored customer",
            "owner": ADMIN["username"], "collaborators": [], "case_no": "ROW7-PENDING",
            "deadline": str(date.today() + timedelta(days=7)), "priority": "普通",
            "source": "案件任务", "description": "row 7 acceptance",
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["customer"], "Row 7 Customer")
        self.assertEqual(created.json()["case_no"], "ROW7-PENDING")

        async with self.sessions() as db:
            task = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == created.json()["serial_no"]))
            self.assertIsNotNone(task)
            self.assertEqual((task.data or {}).get("case_id"), self.pending_id)

        listed = await self.client.get(f"{API}/cases/{self.pending_id}/tasks")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["items"][0]["title"], "ROW7 browser task")

    async def test_historical_case_with_legacy_creation_marker_keeps_customer_task_action(self) -> None:
        capabilities = await self.client.get(f"{API}/cases/{self.historical_id}/action-capabilities")
        self.assertEqual(capabilities.status_code, 200, capabilities.text)
        self.assertTrue(capabilities.json()["can_create_case_task"])

        created = await self.client.post(f"{API}/tasks", json={
            "title": "ROW7 historical customer task", "customer": "ignored customer",
            "owner": ADMIN["username"], "collaborators": [], "case_no": "ROW7-HISTORICAL",
            "deadline": str(date.today() + timedelta(days=7)), "priority": "普通",
            "source": "客户任务", "description": "historical case acceptance",
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["case_no"], "ROW7-HISTORICAL")
        self.assertEqual(created.json()["source"], "客户任务")

        listed = await self.client.get(f"{API}/cases/{self.historical_id}/tasks")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["items"][0]["title"], "ROW7 historical customer task")
        self.assertEqual(listed.json()["items"][0]["source"], "客户任务")

    async def test_archived_case_keeps_case_tasks_read_only(self) -> None:
        capabilities = await self.client.get(f"{API}/cases/{self.archived_id}/action-capabilities")
        self.assertFalse(capabilities.json()["can_create_case_task"])
        response = await self.client.post(f"{API}/tasks", json={
            "title": "blocked", "customer": "Row 7 Customer", "owner": ADMIN["username"],
            "collaborators": [], "case_no": "ROW7-ARCHIVED",
            "deadline": str(date.today() + timedelta(days=7)), "priority": "普通",
            "source": "案件任务", "description": "",
        })
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()

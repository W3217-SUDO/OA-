"""8.13 row 3: company-case deletion is a real, permission-guarded workflow."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row3-admin", "role": "admin", "display_name": "Row 3 Admin", "department": "Row 3"}
EMPLOYEE = {"username": "row3-user", "role": "user", "display_name": "Row 3 User", "department": "Row 3"}


class CompanyCaseDeleteRow3Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True),
                User(username=EMPLOYEE["username"], display_name=EMPLOYEE["display_name"], department=EMPLOYEE["department"], role="user", password_hash="x", is_active=True),
            ])
            case = BusinessRecord(
                module="case", serial_no="CODEX-813-R3-CASE", title="Row 3 Company Case", customer="Row 3 Customer",
                status="新案待分配", owner=ADMIN["username"], department=ADMIN["department"], data={"case_type": "民事案件"},
            )
            db.add(case)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no="CODEX-813-R3-TASK", title="Row 3 Case Task", customer=case.customer,
                status="待接收", owner=ADMIN["username"], department=ADMIN["department"], data={"case_id": case.id},
            )
            db.add(task)
            db.add_all([
                WorkflowEvent(record_id=case.id, action="测试案件事件", operator=ADMIN["username"]),
                FileAttachment(record_id=case.id, original_name="row3.txt", stored_name="row3-delete-test.txt", path="row3-delete-test.txt", uploader=ADMIN["username"]),
            ])
            await db.commit()
            self.case_id, self.task_id = case.id, task.id
        self.identity = ADMIN
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row3.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_admin_delete_removes_case_owned_records(self) -> None:
        response = await self.client.delete(f"{API}/cases/{self.case_id}")
        self.assertEqual(response.status_code, 204, response.text)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(BusinessRecord, self.case_id))
            self.assertIsNone(await db.get(BusinessRecord, self.task_id))
            self.assertIsNone(await db.scalar(select(FileAttachment).where(FileAttachment.record_id == self.case_id)))
            self.assertIsNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id)))

    async def test_employee_cannot_delete_company_case(self) -> None:
        self.identity = EMPLOYEE
        response = await self.client.delete(f"{API}/cases/{self.case_id}")
        self.assertEqual(response.status_code, 403, response.text)
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(BusinessRecord, self.case_id))


if __name__ == "__main__":
    unittest.main()

"""8.13 row 6: case reminders and logs remain usable before creation approval."""

from __future__ import annotations

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
ADMIN = {"username": "row6-admin", "role": "admin", "display_name": "Row6 Admin", "department": "诉讼部"}


class CaseNoteCreationApprovalIndependenceRow6Test(unittest.IsolatedAsyncioTestCase):
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
                self._case("ROW6-PENDING", "待立案审批"),
                self._case("ROW6-HISTORICAL", "新案待分配", creation_step="basic"),
                self._case("ROW6-ARCHIVED", "已归档"),
            ])
            await db.flush()
            self.pending_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW6-PENDING"))
            self.historical_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW6-HISTORICAL"))
            self.archived_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW6-ARCHIVED"))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row6.test")

    @staticmethod
    def _case(serial_no: str, status: str, *, creation_step: str = "completed") -> BusinessRecord:
        return BusinessRecord(
            module="case", serial_no=serial_no, title=serial_no, customer="Row 6 Customer",
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

    async def test_pending_approval_exposes_and_persists_reminder_and_log_actions(self) -> None:
        capabilities = await self.client.get(f"{API}/cases/{self.pending_id}/action-capabilities")
        self.assertEqual(capabilities.status_code, 200, capabilities.text)
        self.assertFalse(capabilities.json()["can_write"])
        self.assertTrue(capabilities.json()["can_create_reminder"])
        self.assertTrue(capabilities.json()["can_delete_reminder"])
        self.assertTrue(capabilities.json()["can_create_log"])

        reminder = await self.client.post(f"{API}/cases/{self.pending_id}/reminders", json={
            "reminder_date": "2026-08-20", "deadline": "2026-08-21", "content": "ROW6 browser reminder",
        })
        self.assertEqual(reminder.status_code, 201, reminder.text)
        log = await self.client.post(f"{API}/cases/{self.pending_id}/logs", json={"content": "ROW6 browser log"})
        self.assertEqual(log.status_code, 201, log.text)

        reminders = await self.client.get(f"{API}/cases/{self.pending_id}/reminders")
        logs = await self.client.get(f"{API}/cases/{self.pending_id}/logs")
        self.assertEqual(reminders.json()["items"][0]["description"], "ROW6 browser reminder")
        self.assertEqual(logs.json()["items"][0]["content"], "ROW6 browser log")

        deleted = await self.client.delete(f"{API}/cases/{self.pending_id}/reminders/{reminder.json()['id']}")
        self.assertEqual(deleted.status_code, 204, deleted.text)

    async def test_historical_case_with_legacy_creation_marker_keeps_note_actions(self) -> None:
        capabilities = await self.client.get(f"{API}/cases/{self.historical_id}/action-capabilities")
        self.assertEqual(capabilities.status_code, 200, capabilities.text)
        self.assertTrue(capabilities.json()["can_create_reminder"])
        self.assertTrue(capabilities.json()["can_create_log"])

        reminder = await self.client.post(f"{API}/cases/{self.historical_id}/reminders", json={
            "reminder_date": "2026-08-22", "deadline": "2026-08-23", "content": "ROW6 historical reminder",
        })
        log = await self.client.post(f"{API}/cases/{self.historical_id}/logs", json={"content": "ROW6 historical log"})
        self.assertEqual(reminder.status_code, 201, reminder.text)
        self.assertEqual(log.status_code, 201, log.text)

    async def test_archived_case_keeps_notes_read_only(self) -> None:
        capabilities = await self.client.get(f"{API}/cases/{self.archived_id}/action-capabilities")
        self.assertFalse(capabilities.json()["can_create_reminder"])
        self.assertFalse(capabilities.json()["can_create_log"])
        response = await self.client.post(f"{API}/cases/{self.archived_id}/logs", json={"content": "blocked"})
        self.assertEqual(response.status_code, 409, response.text)


if __name__ == "__main__":
    unittest.main()

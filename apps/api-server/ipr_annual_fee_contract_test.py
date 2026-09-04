"""Isolated API contract for IPR annual-fee management and its in-app reminders."""

from datetime import date
import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IprCaseAnnualFee, IprCaseReminder, IprCaseReminderSuppression, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "annual-fee-admin", "role": "admin", "display_name": "Annual Fee Admin", "department": "IPR"}


class IprAnnualFeeContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="different-user", display_name="Different", department="Other", password_hash="test", role="user"))
            active = BusinessRecord(module="ipr_case", serial_no="CODEX-ANNUAL-001", title="Annual fee test case", customer="Test customer", status="在办", owner=ADMIN["username"], department="IPR", data={"annual_fee_year": 1})
            other = BusinessRecord(module="ipr_case", serial_no="CODEX-ANNUAL-002", title="Other annual fee case", customer="Test customer", status="在办", owner=ADMIN["username"], department="IPR", data={})
            archived = BusinessRecord(module="ipr_case", serial_no="CODEX-ANNUAL-003", title="Archived annual fee case", customer="Test customer", status="已归档", owner=ADMIN["username"], department="IPR", data={})
            db.add_all([active, other, archived])
            await db.flush()
            self.case_id, self.other_case_id, self.archived_case_id = active.id, other.id, archived.id
            await db.commit()
        self.identity = dict(ADMIN)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr-annual.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_crud_year_filter_and_real_reminder_lifecycle(self):
        create = await self.client.post(f"{API}/ipr/cases/{self.case_id}/annual-fees", json={
            "fee_year": 2026, "fee_name": "2026年度专利年费", "amount": 900.5,
            "currency": "cny", "due_date": "2026-08-31", "status": "待缴",
            "reminder_date": "2026-08-10", "notes": "CODEX annual fee",
        })
        self.assertEqual(create.status_code, 201, create.text)
        row = create.json()
        self.assertEqual(row["fee_year"], 2026)
        self.assertEqual(row["status"], "待缴")
        self.assertEqual(row["currency"], "CNY")
        self.assertIsNotNone(row["reminder_id"])
        self.assertEqual(row["reminder"]["event_type_id"], 4)
        annual_fee_id, first_reminder_id = row["id"], row["reminder_id"]

        listed = await self.client.get(f"{API}/ipr/cases/{self.case_id}/annual-fees", params={"fee_year": 2026})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["total"], 1)
        self.assertTrue(listed.json()["capabilities"]["can_manage"])

        paid = await self.client.put(f"{API}/ipr/cases/{self.case_id}/annual-fees/{annual_fee_id}", json={"status": "已缴", "paid_date": "2026-08-20"})
        self.assertEqual(paid.status_code, 200, paid.text)
        self.assertIsNone(paid.json()["reminder_id"])
        async with self.sessions() as db:
            self.assertIsNone(await db.get(IprCaseReminder, first_reminder_id))

        reopened = await self.client.put(f"{API}/ipr/cases/{self.case_id}/annual-fees/{annual_fee_id}", json={"status": "未缴", "paid_date": None, "reminder_date": "2026-08-10"})
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertIsNotNone(reopened.json()["reminder_id"])
        self.assertEqual(reopened.json()["reminder"]["reminder_date"], "2026-08-10")

        deleted = await self.client.delete(f"{API}/ipr/cases/{self.case_id}/annual-fees/{annual_fee_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(IprCaseAnnualFee)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(IprCaseReminder)), 0)

    async def test_suppressed_annual_fee_reminders_do_not_create_or_leave_rows(self):
        async with self.sessions() as db:
            db.add(IprCaseReminderSuppression(case_record_id=self.case_id, event_type_id=4, event_type="缴纳年费", operator=ADMIN["username"]))
            await db.commit()
        created = await self.client.post(f"{API}/ipr/cases/{self.case_id}/annual-fees", json={
            "fee_year": 2028, "fee_name": "suppressed", "amount": 1, "due_date": "2028-08-10", "reminder_date": "2028-08-01",
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.assertIsNone(created.json()["reminder_id"])
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(IprCaseReminder)), 0)

    async def test_validation_archive_cross_case_and_scope_guards(self):
        invalid = await self.client.post(f"{API}/ipr/cases/{self.case_id}/annual-fees", json={
            "fee_year": 2026, "fee_name": "invalid", "amount": 1, "due_date": "2026-08-10",
            "status": "已缴",
        })
        self.assertEqual(invalid.status_code, 422, invalid.text)

        created = await self.client.post(f"{API}/ipr/cases/{self.case_id}/annual-fees", json={
            "fee_year": 2027, "fee_name": "2027 annual", "amount": 1, "due_date": "2027-08-10",
            "reminder_date": "2027-08-01",
        })
        self.assertEqual(created.status_code, 201, created.text)
        annual_fee_id = created.json()["id"]
        cross_case = await self.client.put(f"{API}/ipr/cases/{self.other_case_id}/annual-fees/{annual_fee_id}", json={"notes": "cross case"})
        self.assertEqual(cross_case.status_code, 404, cross_case.text)

        archived = await self.client.post(f"{API}/ipr/cases/{self.archived_case_id}/annual-fees", json={
            "fee_year": 2026, "fee_name": "archived", "amount": 1, "due_date": "2026-08-10",
        })
        self.assertEqual(archived.status_code, 409, archived.text)

        self.identity = {"username": "different-user", "role": "user", "display_name": "Different", "department": "Other"}
        forbidden = await self.client.delete(f"{API}/ipr/cases/{self.case_id}/annual-fees/{annual_fee_id}")
        self.assertIn(forbidden.status_code, {403, 404}, forbidden.text)


if __name__ == "__main__":
    unittest.main()

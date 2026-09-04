"""Runtime contract tests for batch-changing case-fee notification dates."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {
    "username": "case-fee-inform-date-admin",
    "role": "admin",
    "display_name": "Case Fee Inform Date Admin",
    "department": "Finance",
}


class CaseFeeInformDateBatchUpdateContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with self.sessions() as db:
            fees = [
                BusinessRecord(
                    module="finance",
                    serial_no=f"CODEX-CASE-FEE-INFORM-DATE-{suffix}",
                    title=f"Case fee {suffix}",
                    customer="CODEX Customer",
                    status="pending",
                    owner=ADMIN["username"],
                    department=ADMIN["department"],
                    data={"case_id": 101, "amount": amount, "inform_date": old_date},
                )
                for suffix, amount, old_date in (
                    ("A", 100.0, "2026-08-01"),
                    ("B", 200.0, "2026-08-02"),
                )
            ]
            non_fee = BusinessRecord(
                module="case",
                serial_no="CODEX-CASE-FEE-INFORM-DATE-NON-FEE",
                title="Not a fee",
                customer="CODEX Customer",
                status="active",
                owner=ADMIN["username"],
                department=ADMIN["department"],
                data={"inform_date": "2026-08-03"},
            )
            db.add_all([*fees, non_fee])
            await db.commit()
            self.fee_ids = [fee.id for fee in fees]
            self.non_fee_id = non_fee.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://case-fee.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_multiple_fee_ids_update_and_write_one_audit_event_each(self) -> None:
        target_date = "2026-09-18"
        response = await self.client.post(
            f"{API}/finance/case-fees/batch-update",
            json={"fee_ids": self.fee_ids, "inform_date": target_date},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["updated"], 2)

        async with self.sessions() as db:
            fees = list((await db.scalars(
                select(BusinessRecord)
                .where(BusinessRecord.id.in_(self.fee_ids))
                .order_by(BusinessRecord.id)
            )).all())
            self.assertEqual([fee.data["inform_date"] for fee in fees], [target_date, target_date])

            events = list((await db.scalars(
                select(WorkflowEvent)
                .where(
                    WorkflowEvent.record_id.in_(self.fee_ids),
                    WorkflowEvent.action == "批量修改通知日期",
                )
                .order_by(WorkflowEvent.record_id)
            )).all())
            self.assertEqual([event.record_id for event in events], self.fee_ids)
            self.assertTrue(all(event.operator == ADMIN["username"] for event in events))
            self.assertTrue(all(target_date in event.comment for event in events))

    async def test_empty_ids_and_invalid_date_are_rejected(self) -> None:
        empty = await self.client.post(
            f"{API}/finance/case-fees/batch-update",
            json={"fee_ids": [], "inform_date": "2026-09-18"},
        )
        self.assertEqual(empty.status_code, 422, empty.text)

        invalid_date = await self.client.post(
            f"{API}/finance/case-fees/batch-update",
            json={"fee_ids": self.fee_ids, "inform_date": "18/09/2026"},
        )
        self.assertEqual(invalid_date.status_code, 422, invalid_date.text)

    async def test_missing_or_non_fee_target_rejects_atomically(self) -> None:
        async with self.sessions() as db:
            before = dict((await db.get(BusinessRecord, self.fee_ids[0])).data)

        for invalid_id in (999_999_999, self.non_fee_id):
            response = await self.client.post(
                f"{API}/finance/case-fees/batch-update",
                json={"fee_ids": [self.fee_ids[0], invalid_id], "inform_date": "2026-09-19"},
            )
            self.assertEqual(response.status_code, 404, response.text)

            async with self.sessions() as db:
                fee = await db.get(BusinessRecord, self.fee_ids[0])
                self.assertEqual(fee.data, before)
                events = list((await db.scalars(select(WorkflowEvent))).all())
                self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()

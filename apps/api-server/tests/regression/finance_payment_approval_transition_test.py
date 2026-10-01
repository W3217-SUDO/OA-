"""Regression tests for the fee approval to waiting-payment transition."""

import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.finance import _finance_fee_payment_status, _review_finance_fee_records
from app.database import Base
from app.models import BusinessRecord, WorkflowEvent


class FinancePaymentApprovalTransitionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def fee(self, *, status="待审批", payment_status="待审批"):
        return BusinessRecord(
            module="finance",
            serial_no="SYNTHETIC-PAYMENT-APPROVAL",
            title="Synthetic official fee",
            customer="Synthetic customer",
            status=status,
            owner="synthetic-admin",
            department="Synthetic department",
            data={"fee_type": "官方费用", "amount": 10, "payment_status": payment_status},
        )

    async def test_approval_persists_waiting_payment_status(self):
        fee = self.fee()
        async with self.sessions() as session:
            session.add(fee)
            await session.flush()
            fee_id = fee.id
            await _review_finance_fee_records(
                [fee], True, "approved", {"username": "synthetic-admin", "role": "admin"}, session,
            )
            await session.commit()
        async with self.sessions() as session:
            stored = await session.get(BusinessRecord, fee_id)
            self.assertEqual(stored.status, "已审批")
            self.assertEqual(stored.data["payment_status"], "待付款")
            self.assertEqual(_finance_fee_payment_status(stored), "待付款")
            events = (await session.scalars(
                select(WorkflowEvent).where(WorkflowEvent.record_id == fee_id)
            )).all()
            self.assertEqual([event.to_status for event in events], ["已审批"])

    async def test_rejection_persists_rejected_payment_status(self):
        fee = self.fee()
        async with self.sessions() as session:
            session.add(fee)
            await session.flush()
            fee_id = fee.id
            await _review_finance_fee_records(
                [fee], False, "rejected", {"username": "synthetic-admin", "role": "admin"}, session,
            )
            await session.commit()
        async with self.sessions() as session:
            stored = await session.get(BusinessRecord, fee_id)
            self.assertEqual(stored.status, "已驳回")
            self.assertEqual(stored.data["payment_status"], "已驳回")

    def test_stale_approved_record_is_visible_as_waiting_payment(self):
        self.assertEqual(
            _finance_fee_payment_status(self.fee(status="已审批", payment_status="待审批")),
            "待付款",
        )


if __name__ == "__main__":
    unittest.main()

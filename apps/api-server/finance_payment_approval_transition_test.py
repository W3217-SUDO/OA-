"""Regression tests for the fee approval to waiting-payment transition."""

import unittest

from app.core.finance import _finance_fee_payment_status, _review_finance_fee_records
from app.models import BusinessRecord


class RecordingSession:
    def __init__(self):
        self.added = []

    def add(self, value):
        self.added.append(value)


class FinancePaymentApprovalTransitionTest(unittest.IsolatedAsyncioTestCase):
    def fee(self, *, status="待审批", payment_status="待审批"):
        return BusinessRecord(
            id=910001,
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
        session = RecordingSession()
        await _review_finance_fee_records(
            [fee], True, "approved", {"username": "synthetic-admin", "role": "admin"}, session,
        )
        self.assertEqual(fee.status, "已审批")
        self.assertEqual(fee.data["payment_status"], "待付款")
        self.assertEqual(_finance_fee_payment_status(fee), "待付款")
        self.assertEqual(session.added[0].to_status, "已审批")

    async def test_rejection_persists_rejected_payment_status(self):
        fee = self.fee()
        await _review_finance_fee_records(
            [fee], False, "rejected", {"username": "synthetic-admin", "role": "admin"}, RecordingSession(),
        )
        self.assertEqual(fee.status, "已驳回")
        self.assertEqual(fee.data["payment_status"], "已驳回")

    def test_stale_approved_record_is_visible_as_waiting_payment(self):
        self.assertEqual(
            _finance_fee_payment_status(self.fee(status="已审批", payment_status="待审批")),
            "待付款",
        )


if __name__ == "__main__":
    unittest.main()

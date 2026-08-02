"""Backend contract tests for the fifth finance parity batch.

The fixtures are local-only, uniquely marked, and removed in ``finally``.
"""
import asyncio
import unittest
import uuid
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.main import (
    FinancePaymentCancelInput,
    FinancePaymentRollbackInput,
    cancel_finance_payment,
    get_finance_payment_source,
    list_finance_transactions,
    list_internal_payment_packages,
    rollback_finance_payment,
)
from app.models import BusinessRecord, FinanceTransaction, WorkflowEvent


ADMIN = {"username": "admin", "role": "admin", "department": "上海分所"}


class FinanceBackendContractTest(unittest.TestCase):
    def test_cancel_requires_reason_and_writes_audit_event(self):
        asyncio.run(self._cancel_requires_reason_and_writes_audit_event())

    async def _cancel_requires_reason_and_writes_audit_event(self):
        prefix = f"CODEX-FINANCE-F5-CANCEL-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            fee = BusinessRecord(
                module="finance", serial_no=prefix, title=prefix,
                customer=prefix, status="待付款", owner="admin",
                department="上海分所", data={"amount": 100, "fee_type": "官方费用"},
            )
            db.add(fee); await db.flush()
            try:
                with self.assertRaises(ValidationError):
                    FinancePaymentCancelInput(reason="")
                result = await cancel_finance_payment(
                    fee.id, FinancePaymentCancelInput(reason="CODEX cancel"), ADMIN, db,
                )
                self.assertEqual(result["status"], "已撤回")
                event = await db.scalar(
                    select(WorkflowEvent).where(
                        WorkflowEvent.record_id == fee.id,
                        WorkflowEvent.action == "付款申请撤回",
                    )
                )
                self.assertIsNotNone(event)
                self.assertEqual(event.from_status, "待付款")
                self.assertEqual(event.to_status, "已撤回")
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == fee.id))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id == fee.id))
                await db.commit()

    def test_rollback_is_role_and_state_guarded(self):
        asyncio.run(self._rollback_is_role_and_state_guarded())

    async def _rollback_is_role_and_state_guarded(self):
        prefix = f"CODEX-FINANCE-F5-ROLLBACK-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            fee = BusinessRecord(
                module="finance", serial_no=prefix, title=prefix,
                customer=prefix, status="待付款", owner="admin",
                department="上海分所", data={"amount": 100},
            )
            paid = BusinessRecord(
                module="finance", serial_no=f"{prefix}-PAID", title=prefix,
                customer=prefix, status="已付款", owner="admin",
                department="上海分所", data={"amount": 100},
            )
            db.add_all([fee, paid]); await db.flush()
            try:
                with self.assertRaises(HTTPException) as denied:
                    await rollback_finance_payment(
                        fee.id, FinancePaymentRollbackInput(comment="x"),
                        {"username": "admin", "role": "user", "department": "上海分所"}, db,
                    )
                self.assertEqual(denied.exception.status_code, 403)
                with self.assertRaises(HTTPException) as invalid:
                    await rollback_finance_payment(
                        paid.id, FinancePaymentRollbackInput(comment="x"), ADMIN, db,
                    )
                self.assertEqual(invalid.exception.status_code, 409)
                result = await rollback_finance_payment(
                    fee.id, FinancePaymentRollbackInput(comment="CODEX rollback"), ADMIN, db,
                )
                self.assertEqual(result["status"], "草稿")
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_([fee.id, paid.id])))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([fee.id, paid.id])))
                await db.commit()

    def test_source_lookup_uses_id_then_verifies_all_identity_fields(self):
        asyncio.run(self._source_lookup_uses_id_then_verifies_all_identity_fields())

    async def _source_lookup_uses_id_then_verifies_all_identity_fields(self):
        prefix = f"CODEX-FINANCE-F5-SOURCE-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            payment = BusinessRecord(
                module="contract_payment", serial_no=f"{prefix}-PAY", title=prefix,
                customer=f"{prefix}-CUSTOMER", status="待付款", owner="admin",
                department="上海分所", data={"contract_no": f"{prefix}-CONTRACT", "amount": 1250.5},
            )
            db.add(payment); await db.flush()
            try:
                result = await get_finance_payment_source(
                    payment.id, payment_no=payment.serial_no,
                    contract_no=payment.data["contract_no"], customer=payment.customer,
                    amount=1250.5, identity=ADMIN, db=db,
                )
                self.assertEqual(result["id"], payment.id)
                with self.assertRaises(HTTPException) as mismatch:
                    await get_finance_payment_source(
                        payment.id, payment_no=payment.serial_no,
                        contract_no="OTHER", customer=payment.customer,
                        amount=1250.5, identity=ADMIN, db=db,
                    )
                self.assertEqual(mismatch.exception.status_code, 404)
            finally:
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id == payment.id))
                await db.commit()

    def test_transactions_support_bounded_page_and_filters(self):
        asyncio.run(self._transactions_support_bounded_page_and_filters())

    async def _transactions_support_bounded_page_and_filters(self):
        prefix = f"CODEX-FINANCE-F5-TX-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            fee = BusinessRecord(
                module="finance", serial_no=prefix, title=prefix,
                customer=prefix, status="已付款", owner="admin",
                department="上海分所", data={"amount": 30},
            )
            db.add(fee); await db.flush()
            txs = [
                FinanceTransaction(finance_record_id=fee.id, transaction_type="付款", amount=10, transaction_date=date(2026, 8, 1), voucher_no=f"{prefix}-1", operator="admin"),
                FinanceTransaction(finance_record_id=fee.id, transaction_type="付款", amount=20, transaction_date=date(2026, 8, 2), voucher_no=f"{prefix}-2", operator="admin"),
            ]
            db.add_all(txs); await db.commit()
            try:
                result = await list_finance_transactions(
                    identity=ADMIN, db=db, page=2, page_size=1,
                    finance_record_id=fee.id, transaction_type="付款",
                )
                self.assertEqual(result["total"], 2)
                self.assertEqual(result["page"], 2)
                self.assertEqual(result["page_size"], 1)
                self.assertEqual(len(result["items"]), 1)
                legacy = await list_finance_transactions(identity=ADMIN, db=db, page=1, page_size=None, finance_record_id=None, transaction_type="", keyword="", date_from=None, date_to=None)
                self.assertGreaterEqual(legacy["total"], 2)
            finally:
                await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == fee.id))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id == fee.id))
                await db.commit()

    def test_payment_packages_support_status_page_and_legacy_call(self):
        asyncio.run(self._payment_packages_support_status_page_and_legacy_call())

    async def _payment_packages_support_status_page_and_legacy_call(self):
        prefix = f"CODEX-FINANCE-F5-PACKAGE-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            packages = [
                BusinessRecord(module="finance_package", serial_no=f"{prefix}-{i}", title=prefix, customer="", status="待核销", owner="admin", department="上海分所", data={"amount": i})
                for i in range(1, 4)
            ]
            db.add_all(packages); await db.commit()
            try:
                result = await list_internal_payment_packages(
                    identity=ADMIN, db=db, page=2, page_size=1, status_filter="待核销",
                )
                self.assertEqual(result["total"], 3)
                self.assertEqual(result["page"], 2)
                self.assertEqual(result["page_size"], 1)
                self.assertEqual(len(result["items"]), 1)
                legacy = await list_internal_payment_packages(identity=ADMIN, db=db, page=1, page_size=None, status_filter="")
                self.assertGreaterEqual(legacy["total"], 3)
            finally:
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([item.id for item in packages])))
                await db.commit()


if __name__ == "__main__":
    unittest.main()

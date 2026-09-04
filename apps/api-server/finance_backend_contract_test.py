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
    FinancePaymentPackageUpdateInput,
    FinancePaymentRollbackInput,
    cancel_finance_payment,
    cancel_internal_payment_package,
    export_payment_package_word,
    get_finance_payment_source,
    get_internal_payment_package,
    list_finance_transactions,
    list_internal_payment_packages,
    rollback_finance_payment,
    update_internal_payment_package,
)
from app.models import BusinessRecord, FinanceTransaction, WorkflowEvent


ADMIN = {"username": "admin", "role": "admin", "department": "上海分所"}


class FinanceBackendContractTest(unittest.TestCase):
    def test_payment_package_management_updates_fee_links_atomically(self):
        asyncio.run(self._payment_package_management_updates_fee_links_atomically())

    def test_payment_package_management_guards_and_delete_restore_links(self):
        asyncio.run(self._payment_package_management_guards_and_delete_restore_links())

    async def _payment_package_management_guards_and_delete_restore_links(self):
        prefix = f"CODEX-FINANCE-PACKAGE-GUARDS-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            linked = BusinessRecord(module="finance", serial_no=f"{prefix}-LINKED", title="内部提成", customer="", status="待核销", owner="admin", department="上海分所", data={"fee_type": "内部费用", "payee": "CODEX收款人", "amount": 10})
            same_payee = BusinessRecord(module="finance", serial_no=f"{prefix}-SAME", title="内部提成", customer="", status="已审批", owner="admin", department="上海分所", data={"fee_type": "内部费用", "payee": "CODEX收款人", "amount": 20})
            other_payee = BusinessRecord(module="finance", serial_no=f"{prefix}-OTHER", title="内部提成", customer="", status="已审批", owner="admin", department="上海分所", data={"fee_type": "内部费用", "payee": "CODEX另一收款人", "amount": 30})
            db.add_all([linked, same_payee, other_payee]); await db.flush()
            package = BusinessRecord(module="finance_package", serial_no=f"P260905-{uuid.uuid4().hex[:8].upper()}", title="CODEX付款包", customer="", status="待核销", owner="admin", department="上海分所", data={"fee_ids": [linked.id], "payee": "CODEX收款人", "amount": 10, "total_amount": 10, "items": [{"fee_id": linked.id, "amount": 10}], "fee_type": "内部提成"})
            db.add(package); await db.flush()
            linked.data = {**linked.data, "payment_package_id": package.id, "payment_package_no": package.serial_no, "payment_status": "待核销"}
            await db.commit()
            try:
                with self.assertRaises(HTTPException) as denied:
                    await update_internal_payment_package(package.id, FinancePaymentPackageUpdateInput(fee_ids=[linked.id]), {**ADMIN, "role": "user"}, db)
                self.assertEqual(denied.exception.status_code, 403)
                with self.assertRaises(HTTPException) as mixed:
                    await update_internal_payment_package(package.id, FinancePaymentPackageUpdateInput(fee_ids=[linked.id, other_payee.id]), ADMIN, db)
                self.assertEqual(mixed.exception.status_code, 409)
                await db.refresh(linked)
                self.assertEqual(linked.data["payment_package_id"], package.id)
                linked.data = {**linked.data, "payment_package_no": "CODEX-BAD-LINK"}; await db.commit()
                with self.assertRaises(HTTPException) as inconsistent:
                    await update_internal_payment_package(package.id, FinancePaymentPackageUpdateInput(fee_ids=[linked.id]), ADMIN, db)
                self.assertEqual(inconsistent.exception.status_code, 409)
                await db.refresh(package); package.status = "已付款"; linked.data = {**linked.data, "payment_package_no": package.serial_no}; await db.commit()
                with self.assertRaises(HTTPException) as paid:
                    await update_internal_payment_package(package.id, FinancePaymentPackageUpdateInput(fee_ids=[linked.id]), ADMIN, db)
                self.assertEqual(paid.exception.status_code, 409)
                package.status = "待核销"; await db.commit()
                response = await cancel_internal_payment_package(package.id, False, ADMIN, db)
                self.assertEqual(response.status_code, 204)
                await db.refresh(linked)
                self.assertEqual(linked.status, "已审批")
                self.assertNotIn("payment_package_id", linked.data)
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_([linked.id, same_payee.id, other_payee.id, package.id])))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([linked.id, same_payee.id, other_payee.id, package.id])))
                await db.commit()

    async def _payment_package_management_updates_fee_links_atomically(self):
        prefix = f"CODEX-FINANCE-PACKAGE-MANAGE-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            old_fee = BusinessRecord(module="finance", serial_no=f"{prefix}-OLD", title="内部提成", customer="", status="待核销", owner="admin", department="上海分所", data={"fee_type": "内部费用", "payee": "CODEX收款人", "amount": 10})
            new_fee = BusinessRecord(module="finance", serial_no=f"{prefix}-NEW", title="内部提成", customer="", status="已审批", owner="admin", department="上海分所", data={"fee_type": "内部费用", "payee": "CODEX收款人", "amount": 20})
            db.add_all([old_fee, new_fee]); await db.flush()
            package = BusinessRecord(module="finance_package", serial_no=f"P260905-{uuid.uuid4().hex[:8].upper()}", title="CODEX付款包", customer="", status="待核销", owner="admin", department="上海分所", data={"fee_ids": [old_fee.id], "payee": "CODEX收款人", "amount": 10, "total_amount": 10, "items": [{"fee_id": old_fee.id, "amount": 10}], "fee_type": "内部提成"})
            db.add(package); await db.flush()
            old_fee.data = {**old_fee.data, "payment_package_id": package.id, "payment_package_no": package.serial_no, "payment_status": "待核销"}
            await db.commit()
            try:
                result = await update_internal_payment_package(package.id, FinancePaymentPackageUpdateInput(fee_ids=[new_fee.id], comment="CODEX edit"), ADMIN, db)
                self.assertEqual(result["data"]["fee_ids"], [new_fee.id])
                self.assertEqual(result["data"]["total_amount"], 20.0)
                await db.refresh(old_fee); await db.refresh(new_fee)
                self.assertEqual(old_fee.status, "已审批")
                self.assertNotIn("payment_package_id", old_fee.data)
                self.assertEqual(new_fee.status, "待核销")
                self.assertEqual(new_fee.data["payment_package_id"], package.id)
                detail = await get_internal_payment_package(package.id, ADMIN, db)
                self.assertEqual(detail["serial_no"], package.serial_no)
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_([old_fee.id, new_fee.id, package.id])))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([old_fee.id, new_fee.id, package.id])))
                await db.commit()

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

    def test_payment_packages_support_legacy_page_id_status_mapping(self):
        asyncio.run(self._payment_packages_support_legacy_page_id_status_mapping())

    async def _payment_packages_support_legacy_page_id_status_mapping(self):
        prefix = f"CODEX-FINANCE-F5-PAGEID-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            pending = BusinessRecord(module="finance_package", serial_no=f"{prefix}-PENDING", title=prefix, customer="", status="待核销", owner="admin", department="上海分所", data={"amount": 1})
            paid = BusinessRecord(module="finance_package", serial_no=f"{prefix}-PAID", title=prefix, customer="", status="已付款", owner="admin", department="上海分所", data={"amount": 2})
            db.add_all([pending, paid]); await db.commit()
            try:
                legacy = await list_internal_payment_packages(
                    identity=ADMIN, db=db, page=1, page_size=None,
                    status_filter="", page_id="5001003006",
                )
                serials = {item["serial_no"] for item in legacy["items"]}
                self.assertIn(pending.serial_no, serials)
                self.assertNotIn(paid.serial_no, serials)
                explicit = await list_internal_payment_packages(
                    identity=ADMIN, db=db, page=1, page_size=None,
                    status_filter="已付款", page_id="5001003006",
                )
                explicit_serials = {item["serial_no"] for item in explicit["items"]}
                self.assertIn(paid.serial_no, explicit_serials)
                self.assertNotIn(pending.serial_no, explicit_serials)
            finally:
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([pending.id, paid.id])))
                await db.commit()

    def test_payment_package_word_export_returns_docx_blob(self):
        asyncio.run(self._payment_package_word_export_returns_docx_blob())

    async def _payment_package_word_export_returns_docx_blob(self):
        prefix = f"CODEX-FINANCE-F5-WORD-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            fee = BusinessRecord(
                module="finance", serial_no=f"{prefix}-FEE", title="内部提成",
                customer=prefix, status="已付款", owner="admin",
                department="上海分所", data={
                    "fee_type": "内部费用",
                    "case_no": f"{prefix}-CASE",
                    "contract_no": f"{prefix}-CONTRACT",
                    "contract_title": "Word 导出合同",
                    "amount": 880.5,
                    "payee": "测试收款人",
                    "applicant": "测试申请人",
                },
            )
            db.add(fee); await db.flush()
            package = BusinessRecord(
                module="finance_package", serial_no=f"P260804-{uuid.uuid4().hex[:8].upper()}",
                title="测试付款包", customer="", status="待核销", owner="admin",
                department="上海分所", data={
                    "fee_ids": [fee.id],
                    "payee": "测试收款人",
                    "amount": 880.5,
                    "total_amount": 880.5,
                    "payment_date": "2026-08-04",
                    "payment_status": "待核销",
                    "fee_type": "内部提成",
                    "items": [{
                        "fee_id": fee.id,
                        "request_no": fee.serial_no,
                        "case_no": f"{prefix}-CASE",
                        "case_name": "Word 导出案件",
                        "amount": 880.5,
                        "commission_type": "内部费用",
                        "payee": "测试收款人",
                        "remark": "DOCX contract",
                    }],
                    "submitted_by": "admin",
                },
            )
            db.add(package); await db.flush()
            fee.data = {**fee.data, "payment_package_id": package.id, "payment_package_no": package.serial_no}
            await db.commit()
            try:
                response = await export_payment_package_word(package.serial_no, "internal_fee", ADMIN, db)
                self.assertEqual(response.media_type, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.assertIn("Content-Disposition", response.headers)
                self.assertIn(package.serial_no, response.headers["Content-Disposition"])
                self.assertTrue(bytes(response.body).startswith(b"PK"))
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_([fee.id, package.id])))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([fee.id, package.id])))
                await db.commit()

    def test_payment_package_word_export_guards_role_and_status(self):
        asyncio.run(self._payment_package_word_export_guards_role_and_status())

    async def _payment_package_word_export_guards_role_and_status(self):
        prefix = f"CODEX-FINANCE-F5-WORD-GUARD-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            fee = BusinessRecord(
                module="finance", serial_no=f"{prefix}-FEE", title="内部提成",
                customer=prefix, status="已付款", owner="admin",
                department="上海分所", data={"fee_type": "内部费用", "amount": 100, "payee": "测试收款人"},
            )
            db.add(fee); await db.flush()
            package = BusinessRecord(
                module="finance_package", serial_no=f"P260804-{uuid.uuid4().hex[:8].upper()}",
                title="测试付款包", customer="", status="草稿", owner="admin",
                department="上海分所", data={
                    "fee_ids": [fee.id],
                    "payee": "测试收款人",
                    "amount": 100,
                    "total_amount": 100,
                    "fee_type": "内部提成",
                    "items": [{"fee_id": fee.id, "request_no": fee.serial_no, "amount": 100, "payee": "测试收款人"}],
                },
            )
            db.add(package); await db.flush()
            fee.data = {**fee.data, "payment_package_id": package.id, "payment_package_no": package.serial_no}
            await db.commit()
            try:
                with self.assertRaises(HTTPException) as denied:
                    await export_payment_package_word(
                        package.serial_no, "internal_fee",
                        {"username": "admin", "role": "user", "department": "上海分所"}, db,
                    )
                self.assertEqual(denied.exception.status_code, 403)
                with self.assertRaises(HTTPException) as invalid_status:
                    await export_payment_package_word(package.serial_no, "internal_fee", ADMIN, db)
                self.assertEqual(invalid_status.exception.status_code, 409)
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_([fee.id, package.id])))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_([fee.id, package.id])))
                await db.commit()


if __name__ == "__main__":
    unittest.main()

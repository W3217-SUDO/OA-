"""Runtime backend contract tests for finance invoice draft updates.

Evidence:
- Old FAM/Controllers/InvoiceController.cs uses InvoiceCreateUpdate and
  returns PostResponse with IsSuccess=false for business failures such as zero
  invoice amount or service-level validation errors.
- New FastAPI already has POST /finance/invoices for creating invoice drafts but
  no dedicated draft/rejected update command.
"""
import asyncio
import unittest
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.main import InvoiceApplicationInput, update_invoice_application
from app.models import BusinessRecord, FinanceTransaction, WorkflowEvent


ADMIN = {
    "username": "admin",
    "role": "admin",
    "department": "上海分所",
    "display_name": "系统管理员",
}
OTHER_USER = {
    "username": "finance-other",
    "role": "user",
    "department": "上海分所",
    "display_name": "其他用户",
}


def invoice_payload(prefix: str, *, amount: float = 345.67) -> InvoiceApplicationInput:
    return InvoiceApplicationInput(
        customer=f"{prefix}客户",
        case_no="",
        amount=amount,
        invoice_title=f"{prefix}发票抬头",
        taxpayer_id=f"TAX-{prefix}",
        invoice_phone="021-12345678",
        bank_account="",
        bank_name="",
        invoice_address=f"{prefix}地址",
        extra_amount=12.34,
        invoice_type="增值税普通发票",
        invoice_content="法律服务费",
        delivery_method="电子发票",
        recipient="",
        recipient_phone="",
        email=f"{prefix.lower()}@example.test",
        delivery_address="",
        remark=f"{prefix}更新备注",
    )


class FinanceInvoiceUpdateBackendContractTest(unittest.TestCase):
    def test_update_allows_draft_and_rejected_only_with_legacy_failure_envelope(self):
        asyncio.run(self._update_allows_draft_and_rejected_only_with_legacy_failure_envelope())

    async def _update_allows_draft_and_rejected_only_with_legacy_failure_envelope(self):
        prefix = f"CODEX-FIN-INV-UPD-{uuid.uuid4().hex[:8].upper()}"
        async with SessionLocal() as db:
            draft = BusinessRecord(
                module="invoice",
                serial_no=f"{prefix}-D",
                title="旧草稿发票",
                customer="旧客户",
                status="草稿",
                owner="admin",
                department="上海分所",
                description="旧备注",
                data={"amount": 1, "invoice_title": "旧抬头", "taxpayer_id": "OLD"},
            )
            rejected = BusinessRecord(
                module="invoice",
                serial_no=f"{prefix}-R",
                title="旧驳回发票",
                customer="旧客户",
                status="已驳回",
                owner="admin",
                department="上海分所",
                description="旧备注",
                data={"amount": 2, "invoice_title": "旧抬头", "taxpayer_id": "OLD"},
            )
            pending = BusinessRecord(
                module="invoice",
                serial_no=f"{prefix}-P",
                title="待审批发票",
                customer="锁定客户",
                status="待审批",
                owner="admin",
                department="上海分所",
                description="不能修改",
                data={"amount": 3, "invoice_title": "锁定抬头", "taxpayer_id": "LOCKED"},
            )
            db.add_all([draft, rejected, pending])
            await db.flush()
            draft_id, rejected_id, pending_id = draft.id, rejected.id, pending.id
            record_ids = [draft_id, rejected_id, pending_id]
            locked_before = dict(pending.data or {})
            try:
                draft_result = await update_invoice_application(draft_id, invoice_payload(prefix), ADMIN, db)
                self.assertEqual(draft_result["status"], "草稿")
                self.assertEqual(draft_result["customer"], f"{prefix}客户")
                self.assertEqual(draft_result["data"]["amount"], 345.67)
                self.assertEqual(draft_result["data"]["extra_amount"], 12.34)
                self.assertEqual(draft_result["data"]["invoice_title"], f"{prefix}发票抬头")

                rejected_result = await update_invoice_application(
                    rejected_id,
                    invoice_payload(f"{prefix}-REJECTED", amount=456.78),
                    ADMIN,
                    db,
                )
                self.assertEqual(rejected_result["status"], "已驳回")
                self.assertEqual(rejected_result["data"]["amount"], 456.78)

                with self.assertRaises(HTTPException) as denied:
                    await update_invoice_application(draft_id, invoice_payload(f"{prefix}-DENIED"), OTHER_USER, db)
                self.assertEqual(denied.exception.status_code, 403)

                failure = await update_invoice_application(pending_id, invoice_payload(f"{prefix}-LOCKED"), ADMIN, db)
                self.assertEqual(failure["IsSuccess"], False)
                self.assertIn("草稿或已驳回", failure["Message"])
                await db.refresh(pending)
                self.assertEqual(pending.status, "待审批")
                self.assertEqual(pending.data, locked_before)

                audit_events = (await db.scalars(select(WorkflowEvent).where(
                    WorkflowEvent.record_id.in_([draft_id, rejected_id]),
                    WorkflowEvent.action == "修改发票申请",
                ))).all()
                self.assertEqual(len(audit_events), 2)
                self.assertTrue(all(event.from_status == event.to_status for event in audit_events))

                invoice_transactions = (await db.scalars(select(FinanceTransaction).where(
                    FinanceTransaction.finance_record_id.in_(record_ids),
                ))).all()
                self.assertEqual(invoice_transactions, [])
            finally:
                await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id.in_(record_ids)))
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(record_ids)))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(record_ids)))
                await db.commit()


if __name__ == "__main__":
    unittest.main()

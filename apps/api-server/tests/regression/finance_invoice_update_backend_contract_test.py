"""Runtime backend contract tests for finance invoice draft updates."""
import asyncio
import unittest
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import InvoiceApplicationInput, update_invoice_application
from app.models import BusinessRecord, FinanceTransaction, User, WorkflowEvent


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


def invoice_payload(prefix: str, fee_id: int, *, amount: float = 345.67) -> InvoiceApplicationInput:
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
        case_fee_ids=[fee_id],
    )


class FinanceInvoiceUpdateBackendContractTest(unittest.TestCase):
    def test_update_allows_draft_and_rejected_only_with_conflict_for_pending(self):
        asyncio.run(self._update_allows_draft_and_rejected_only_with_conflict_for_pending())

    async def _update_allows_draft_and_rejected_only_with_conflict_for_pending(self):
        prefix = f"CODEX-FIN-INV-UPD-{uuid.uuid4().hex[:8].upper()}"
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            db.add(User(
                username="admin", role="admin", department="上海分所",
                display_name="系统管理员", password_hash="unused", is_active=True,
            ))
            source_fees = []
            for suffix in ("", "-REJECTED"):
                customer = f"{prefix}{suffix}客户"
                contract = BusinessRecord(
                    module="contract", serial_no=f"{prefix}{suffix}-CONTRACT",
                    title="测试合同", customer=customer, status="已审批", owner="admin",
                    department="上海分所", data={"contract_body": "律所"},
                )
                db.add(contract)
                await db.flush()
                fee = BusinessRecord(
                    module="finance", serial_no=f"{prefix}{suffix}-FEE",
                    title="可开票案件费用", customer=customer, status="已审批", owner="admin",
                    department="上海分所", data={
                        "fee_type": "官方费用", "expense_scope": "律所", "amount": 1000,
                        "contract_id": contract.id, "contract_no": contract.serial_no,
                    },
                )
                db.add(fee)
                source_fees.append(fee)
            await db.flush()
            draft_fee_id, rejected_fee_id = (fee.id for fee in source_fees)
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
                draft_result = await update_invoice_application(draft_id, invoice_payload(prefix, draft_fee_id), ADMIN, db)
                self.assertEqual(draft_result["status"], "草稿")
                self.assertEqual(draft_result["customer"], f"{prefix}客户")
                self.assertEqual(draft_result["data"]["amount"], 345.67)
                self.assertEqual(draft_result["data"]["extra_amount"], 12.34)
                self.assertEqual(draft_result["data"]["invoice_title"], f"{prefix}发票抬头")

                rejected_result = await update_invoice_application(
                    rejected_id,
                    invoice_payload(f"{prefix}-REJECTED", rejected_fee_id, amount=456.78),
                    ADMIN,
                    db,
                )
                self.assertEqual(rejected_result["status"], "已驳回")
                self.assertEqual(rejected_result["data"]["amount"], 456.78)

                with self.assertRaises(HTTPException) as denied:
                    await update_invoice_application(draft_id, invoice_payload(f"{prefix}-DENIED", draft_fee_id), OTHER_USER, db)
                self.assertEqual(denied.exception.status_code, 403)

                with self.assertRaises(HTTPException) as locked:
                    await update_invoice_application(
                        pending_id, invoice_payload(f"{prefix}-LOCKED", draft_fee_id), ADMIN, db,
                    )
                self.assertEqual(locked.exception.status_code, 409)
                self.assertIn("草稿或已驳回", locked.exception.detail)
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
        await engine.dispose()


if __name__ == "__main__":
    unittest.main()

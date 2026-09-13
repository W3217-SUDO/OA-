"""Focused regression coverage for per-fee contract payment ownership.

These tests intentionally use isolated CODEX records and remove them in the
same transaction scope. They are added as source coverage only in this handoff.
"""
import asyncio
import unittest
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.areas.contract.router import create_contract_payment_application
from app.areas.finance.router import submit_finance_fee
from app.core.finance import _contract_payment_candidate_rows, _fee_matches_contract, _validate_invoice_source_links
from app.database import SessionLocal
from app.models import BusinessRecord, ContractObject, ContractPaymentLine, SystemParameter, WorkflowEvent
from app.models_shared import ContractPaymentApplicationInput, ContractPaymentLineInput, FinanceActionInput, InvoiceApplicationInput


ADMIN = {"username": "admin", "role": "admin", "department": "上海分所"}


class FinanceFeeContractAssignmentTest(unittest.TestCase):
    def test_fee_contract_b_owns_candidates_and_reservations(self):
        asyncio.run(self._fee_contract_b_owns_candidates_and_reservations())

    async def _fee_contract_b_owns_candidates_and_reservations(self):
        prefix = f"CODEX-FEE-CONTRACT-{uuid.uuid4().hex[:10]}"
        async with SessionLocal() as db:
            contract_a = BusinessRecord(module="contract", serial_no=f"{prefix}-A", title="合同A", customer=prefix, status="审批通过", owner="admin", department="上海分所", data={"contract_body": "律所"})
            contract_b = BusinessRecord(module="contract", serial_no=f"{prefix}-B", title="合同B", customer=prefix, status="审批通过", owner="admin", department="上海分所", data={"contract_body": "律所"})
            case = BusinessRecord(module="case", serial_no=f"{prefix}-CASE", title="案件", customer=prefix, status="在办", owner="admin", department="上海分所", data={})
            payment_type = SystemParameter(category="payment_type", code=prefix, name="CODEX付款单位", extra={"nature": "案件付款", "payee": "CODEX收款方", "account_bank": "CODEX银行", "account": "123"}, is_active=True, created_by="admin", updated_by="admin")
            db.add_all([contract_a, contract_b, case, payment_type])
            await db.flush()
            case.data = {"contract_id": contract_a.id, "contract_no": contract_a.serial_no}
            # A retains a real historical object, while B intentionally has none.
            object_a = ContractObject(contract_record_id=contract_a.id, case_record_id=case.id, fee_type="官方费用", amount=100, remark="历史标的")
            fee_b = BusinessRecord(module="finance", serial_no=f"{prefix}-FEE-B", title="费用B", customer=prefix, status="草稿", owner="admin", department="上海分所", data={"case_id": case.id, "case_no": case.serial_no, "contract_id": contract_b.id, "contract_no": contract_b.serial_no, "fee_type": "官方费用", "amount": 100})
            fee_no_only = BusinessRecord(module="finance", serial_no=f"{prefix}-FEE-NO", title="费用号兼容", customer=prefix, status="草稿", owner="admin", department="上海分所", data={"case_id": case.id, "case_no": case.serial_no, "contract_no": contract_b.serial_no, "fee_type": "官方费用", "amount": 20})
            db.add_all([object_a, fee_b, fee_no_only])
            await db.commit()
            try:
                self.assertTrue(_fee_matches_contract(fee_b, contract_b))
                self.assertFalse(_fee_matches_contract(fee_b, contract_a))
                self.assertTrue(_fee_matches_contract(fee_no_only, contract_b))
                contradictory = BusinessRecord(module="finance", serial_no=f"{prefix}-BAD", title="矛盾费用", customer=prefix, status="草稿", owner="admin", department="上海分所", data={"contract_id": contract_b.id, "contract_no": contract_a.serial_no, "fee_type": "官方费用", "amount": 1})
                db.add(contradictory)
                await db.flush()
                self.assertFalse(_fee_matches_contract(contradictory, contract_b))

                candidates_b = await _contract_payment_candidate_rows(contract_b, ADMIN, db)
                self.assertEqual({row["case_fee_id"] for row in candidates_b}, {fee_b.id, fee_no_only.id})
                self.assertTrue(all(row["contract_object_id"] is None for row in candidates_b))
                self.assertEqual(await _contract_payment_candidate_rows(contract_a, ADMIN, db), [])

                invoice_body = InvoiceApplicationInput(customer=prefix, case_no=case.serial_no, case_record_id=case.id, contract_record_id=contract_b.id, case_fee_ids=[fee_b.id], amount=100, invoice_title=prefix, taxpayer_id="CODEX-TAX")
                _, invoice_contract, _, _ = await _validate_invoice_source_links(invoice_body, ADMIN, db, require_source=True)
                self.assertEqual(invoice_contract.id, contract_b.id)
                _, number_only_contract, _, _ = await _validate_invoice_source_links(
                    invoice_body.model_copy(update={"case_fee_ids": [fee_no_only.id], "amount": 20}), ADMIN, db, require_source=True,
                )
                self.assertEqual(number_only_contract.id, contract_b.id)
                with self.assertRaises(HTTPException) as invoice_a:
                    await _validate_invoice_source_links(
                        invoice_body.model_copy(update={"contract_record_id": contract_a.id}), ADMIN, db, require_source=True,
                    )
                self.assertEqual(invoice_a.exception.status_code, 409)
                with self.assertRaises(HTTPException) as conflicting_invoice:
                    await _validate_invoice_source_links(
                        invoice_body.model_copy(update={"case_fee_ids": [contradictory.id], "amount": 1}), ADMIN, db, require_source=True,
                    )
                self.assertEqual(conflicting_invoice.exception.status_code, 409)

                # Direct fee payment reserves the same source before contract payment can use it.
                await submit_finance_fee(fee_b.id, FinanceActionInput(amount=40, payment_type_id=payment_type.id), ADMIN, db)
                candidates_b = await _contract_payment_candidate_rows(contract_b, ADMIN, db)
                fee_b_candidate = next(row for row in candidates_b if row["case_fee_id"] == fee_b.id)
                self.assertEqual(fee_b_candidate["remaining_amount"], 60)
                with self.assertRaises(HTTPException) as over_reserved:
                    await create_contract_payment_application(
                        contract_b.id,
                        ContractPaymentApplicationInput(payment_type_id=payment_type.id, application_date=date.today(), lines=[ContractPaymentLineInput(case_fee_id=fee_b.id, amount=70)]),
                        ADMIN,
                        db,
                    )
                self.assertEqual(over_reserved.exception.status_code, 422)

                created = await create_contract_payment_application(
                    contract_b.id,
                    ContractPaymentApplicationInput(payment_type_id=payment_type.id, application_date=date.today(), lines=[ContractPaymentLineInput(case_fee_id=fee_b.id, amount=60)]),
                    ADMIN,
                    db,
                )
                self.assertEqual(created["data"]["lines"][0]["case_fee_id"], fee_b.id)
                self.assertIsNone(created["data"]["lines"][0]["contract_object_id"])
                self.assertEqual(await db.scalar(select(ContractPaymentLine).where(ContractPaymentLine.payment_record_id == created["id"])), None)
            finally:
                ids = [contract_a.id, contract_b.id, case.id, fee_b.id, fee_no_only.id, contradictory.id]
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(ids)))
                await db.execute(delete(ContractPaymentLine).where(ContractPaymentLine.contract_object_id == object_a.id))
                await db.execute(delete(ContractObject).where(ContractObject.id == object_a.id))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(ids)))
                await db.execute(delete(SystemParameter).where(SystemParameter.id == payment_type.id))
                await db.commit()

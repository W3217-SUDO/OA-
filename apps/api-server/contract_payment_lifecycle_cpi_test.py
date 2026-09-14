"""CPI05/07/09: real routers, disposable in-memory SQLite only; no app lifespan."""
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.areas.contract import router as routes
from app.core.contract_payment_lifecycle import normalized_payment, query_payments
from app.core.contract_payment_lifecycle import payment_query_line_match, payment_query_amount
from app.core.finance import _contract_payment_candidate_rows
from app.database import Base, get_db
from app.models import BusinessRecord, ContractObject, ContractPaymentLine, FinanceTransaction, SystemParameter, User, WorkflowEvent
from app.models_shared import (ContractPaymentApplicationInput, ContractPaymentPayInput,
    ContractPaymentReviewInput, ContractPaymentWriteoffInput, FinancePaymentCancelInput, FinancePaymentRollbackInput)
from app.core.dependencies import current_identity

ADMIN = {"username": "admin", "role": "admin", "department": "CODEX-CPI"}
NOTE = FinancePaymentRollbackInput(comment="CODEX-CPI note")


class ContractPaymentLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.db.add(User(username="admin", password_hash="isolated-not-a-login", department="CODEX-CPI"))
        self.contract = self.record("contract", "CONTRACT", status="草稿", data={"contract_body": "律所"})
        self.case = self.record("case", "CASE", status="在办", data={"stage": "一审"})
        self.payment_type = SystemParameter(category="payment_type", code="CODEX-CPI-TYPE", name="CODEX-PAYEE",
            extra={"nature": "案件付款", "payee": "CODEX-PAYEE", "account_bank": "CODEX-BANK", "account": "CODEX-ACCOUNT"},
            is_active=True, created_by="admin", updated_by="admin")
        self.db.add(self.payment_type)
        await self.db.flush()
        self.fee = self.record("finance", "FEE", data={"case_id": self.case.id, "case_no": self.case.serial_no,
            "contract_id": self.contract.id, "contract_no": self.contract.serial_no, "fee_type": "官方费用", "amount": 100})
        await self.db.commit()
        self.app = FastAPI()
        self.app.include_router(routes.router)
        self.app.dependency_overrides[current_identity] = lambda: ADMIN
        async def isolated_db():
            try:
                yield self.db
            except Exception:
                await self.db.rollback()
                raise
        self.app.dependency_overrides[get_db] = isolated_db
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.close()
        await self.engine.dispose()

    def record(self, module, suffix, status="草稿", data=None, owner="admin"):
        record = BusinessRecord(module=module, serial_no=f"CODEX-CPI-{suffix}", title=f"CODEX-{suffix}", customer="CODEX-CUSTOMER",
            status=status, owner=owner, department="CODEX-CPI", data=data or {})
        self.db.add(record)
        return record

    def body(self, amount=60, **changes):
        return ContractPaymentApplicationInput(payment_type_id=self.payment_type.id, application_date=date(2026, 9, 14),
            remark="CODEX-REMARK", lines=[{"case_fee_id": self.fee.id, "amount": amount, "remark": "CODEX-LINE"}], **changes)

    async def create(self, amount=60):
        return await routes.create_contract_payment_application(self.contract.id, self.body(amount), ADMIN, self.db)

    async def remaining(self):
        return (await _contract_payment_candidate_rows(self.contract, ADMIN, self.db))[0]["remaining_amount"]

    async def test_reject_edit_resubmit_keeps_identity_and_history(self):
        original = await self.create()
        self.assertEqual(await self.remaining(), 40)
        await routes.review_contract_payment_application(original["id"], ContractPaymentReviewInput(approved=False, comment="CODEX-reject"), ADMIN, self.db)
        self.assertEqual(await self.remaining(), 100)
        context = await self.client.get(f"/api/v1/contract-payment-applications/{original['id']}/edit-context")
        self.assertEqual(context.status_code, 200, context.text)
        self.assertEqual(set(context.json()), {"payment", "contract", "payment_types", "items"})
        edited = await self.client.put(f"/api/v1/contract-payment-applications/{original['id']}", json=self.body(80).model_dump(mode="json"))
        self.assertEqual(edited.status_code, 200, edited.text)
        submitted = await routes.submit_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        self.assertEqual((submitted["id"], submitted["serial_no"]), (original["id"], original["serial_no"]))
        self.assertEqual(submitted["data"]["audit_round"], 2)
        self.assertEqual(await self.remaining(), 20)
        event_count = await self.db.scalar(select(func.count(WorkflowEvent.id)))
        await routes.submit_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        self.assertEqual(await self.db.scalar(select(func.count(WorkflowEvent.id))), event_count)
        events = list((await self.db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == original["id"]))).all())
        self.assertEqual(len(events), 4)
        self.assertTrue(all(event.operator == "admin" and event.to_status and event.comment for event in events))

    async def test_rollback_and_cancel_release_once_and_other_payment_blocks_resubmit(self):
        original = await self.create(80)
        await routes.review_contract_payment_application(original["id"], ContractPaymentReviewInput(approved=True), ADMIN, self.db)
        rolled = await routes.rollback_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        self.assertEqual(rolled["status"], "待提交")
        self.assertEqual(await self.remaining(), 100)
        await routes.rollback_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        other = await self.create(40)
        with self.assertRaises(HTTPException) as caught:
            await routes.submit_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        self.assertEqual(caught.exception.status_code, 422)
        await self.db.rollback()
        cancel = FinancePaymentCancelInput(reason="CODEX-cancel")
        await routes.cancel_contract_payment_application(other["id"], cancel, ADMIN, self.db)
        await routes.cancel_contract_payment_application(other["id"], cancel, ADMIN, self.db)
        await routes.submit_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        self.assertEqual(await self.remaining(), 20)

    async def test_paid_and_writeoff_block_all_mutations_and_duplicate_pay(self):
        original = await self.create()
        await routes.review_contract_payment_application(original["id"], ContractPaymentReviewInput(approved=True), ADMIN, self.db)
        pay = ContractPaymentPayInput(paid_date=date.today(), voucher_no="CODEX-VOUCHER")
        await routes.pay_contract_payment_application(original["id"], pay, ADMIN, self.db)
        for operation in [routes.rollback_contract_payment_application, routes.submit_contract_payment_application]:
            with self.assertRaises(HTTPException):
                await operation(original["id"], NOTE, ADMIN, self.db)
        with self.assertRaises(HTTPException):
            await routes.pay_contract_payment_application(original["id"], pay, ADMIN, self.db)
        self.assertEqual(await self.db.scalar(select(func.count(FinanceTransaction.id))), 1)
        await routes.writeoff_contract_payment_application(original["id"], ContractPaymentWriteoffInput(writeoff_date=date.today(), voucher_no="CODEX-WRITEOFF"), ADMIN, self.db)
        response = await self.client.put(f"/api/v1/contract-payment-applications/{original['id']}", json=self.body(20).model_dump(mode="json"))
        self.assertEqual(response.status_code, 409)

    async def test_transaction_blocks_corrupted_pending_state(self):
        original = await self.create()
        self.db.add(FinanceTransaction(finance_record_id=original["id"], transaction_type="合同付款", amount=1,
            transaction_date=date.today(), operator="admin"))
        await self.db.commit()
        with self.assertRaises(HTTPException):
            await routes.rollback_contract_payment_application(original["id"], NOTE, ADMIN, self.db)

    async def test_current_reservation_excluded_but_other_reservation_kept(self):
        original = await self.create(60)
        await self.create(30)
        payment = await self.db.get(BusinessRecord, original["id"])
        result = await normalized_payment(self.body(70), self.contract, ADMIN, self.db, payment)
        self.assertEqual(result["amount"], 70)
        with self.assertRaises(HTTPException):
            await normalized_payment(self.body(71), self.contract, ADMIN, self.db, payment)

    async def test_contract_object_details_and_reservation_are_symmetric(self):
        obj_case = self.record("case", "OBJECT-CASE", status="在办")
        await self.db.flush()
        obj = ContractObject(contract_record_id=self.contract.id, case_record_id=obj_case.id, fee_type="官方费用", amount=100, created_by="admin", updated_by="admin")
        self.db.add(obj)
        await self.db.commit()
        body = ContractPaymentApplicationInput(payment_type_id=self.payment_type.id, application_date=date.today(),
            lines=[{"contract_object_id": obj.id, "amount": 80}])
        original = await routes.create_contract_payment_application(self.contract.id, body, ADMIN, self.db)
        await routes.rollback_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        await routes.update_contract_payment_application(original["id"], body.model_copy(update={"lines": self.body(40).lines}), ADMIN, self.db)
        self.assertEqual(await self.db.scalar(select(func.count(ContractPaymentLine.id))), 0)
        await routes.submit_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
        self.assertEqual(await self.remaining(), 60)

    async def test_query_interleaved_sources_all_pages_and_500_limit(self):
        expected = []
        for index in range(225):
            row = self.record("finance" if index % 2 else "contract_payment", f"QUERY-{index:03}", status="待审批",
                data={"legacy_kind": "ap_payment", "amount": 2, "applicant": "admin", "fee_type": "官方费用"})
            row.created_at = datetime(2026, 9, 14)
            expected.append(row)
        await self.db.commit()
        ids = []
        for page in range(1, 5):
            response = await self.client.get("/api/v1/finance/payment-applications/query", params={"keyword": "QUERY", "page": page, "page_size": 70})
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["total"], 225)
            self.assertEqual(payload["totals"]["amount"], 450)
            ids.extend(row["id"] for row in payload["items"])
        self.assertEqual(ids, [row.id for row in reversed(expected)])
        large = await self.client.get("/api/v1/finance/payment-applications/query", params={"keyword": "QUERY", "page_size": 500})
        self.assertEqual(len(large.json()["items"]), 225)
        invalid = await self.client.get("/api/v1/finance/payment-applications/query", params={"page_size": 501})
        self.assertEqual(invalid.status_code, 422)

    async def test_query_waiting_payment_recovers_approved_fee_with_stale_extended_status(self):
        stale = self.record(
            "finance", "STALE-WAITING", status="已审批",
            data={
                "legacy_kind": "ap_payment",
                "amount": 10,
                "applicant": "admin",
                "fee_type": "官方费用",
                "payment_status": "待审批",
            },
        )
        await self.db.commit()
        result = await query_payments(
            {"statuses": "待付款", "keyword": "STALE-WAITING", "page": 1, "page_size": 20},
            ADMIN,
            self.db,
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], stale.id)
        self.assertEqual(result["items"][0]["data"]["payment_status"], "待付款")

    async def test_query_filters_apply_equally_to_both_sources_before_paging(self):
        original = await self.create()
        self.record("finance", "MATCH", status="待审批", data={"legacy_kind": "ap_payment", "amount": 60,
            "applicant": "admin", "payee": "CODEX-PAYEE", "fee_type": "官方费用", "case_no": self.case.serial_no,
            "case_stage": "一审", "application_date": "2026-09-14", "finance_scope": "firm"})
        self.record("finance", "IGNORE-INVOICE", data={"legacy_kind": "invoice", "amount": 999})
        await self.db.commit()
        response = await self.client.get("/api/v1/finance/payment-applications/query", params={
            "record_status": "待审批", "scope": "mine", "finance_scope": "firm", "applicant": "admin",
            "fee_type": "官方", "payee": "CODEX-PAYEE", "case_no": self.case.serial_no, "stage": "一审",
            "application_date_start": "2026-09-14", "application_date_end": "2026-09-14", "page_size": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 2)
        self.assertEqual(len(response.json()["items"]), 1)

    async def test_scope_and_field_permissions_are_not_bypassed_by_union(self):
        self.db.add(User(username="CODEX-USER", password_hash="isolated", role="staff", department="CODEX-CPI"))
        self.record("contract_payment", "OWN", owner="CODEX-USER", data={"amount": 10})
        self.record("finance", "OTHER", data={"legacy_kind": "ap_payment", "amount": 20})
        await self.db.commit()
        identity = {"username": "CODEX-USER", "role": "staff"}
        permission = {"data_scope": "本人数据", "menu_keys": ["finance-payment-query"], "field_keys": [], "action_keys": []}
        with patch("app.core.permissions._user_permission_payload", AsyncMock(return_value=permission)), \
             patch("app.core.permissions._require_record_module_menu", AsyncMock()), \
             patch("app.core.system._allowed_field_keys", AsyncMock(return_value=set())):
            result = await query_payments({"page": 1, "page_size": 20}, identity, self.db)
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"][0]["owner"], "CODEX-USER")
            self.assertEqual(result["totals"], {})
            with self.assertRaises(HTTPException) as caught:
                await routes.rollback_contract_payment_application((await self.create())["id"], NOTE, identity, self.db)
            self.assertEqual(caught.exception.status_code, 404)

    async def test_invoice_candidates_keep_partial_balance_and_real_search_fields(self):
        self.contract.data = {**self.contract.data, "external_contract_no": "CODEX-EXTERNAL"}
        self.case.data = {**self.case.data, "court_name": "CODEX-COURT", "hearing_lawyer": "CODEX-LAWYER",
            "investigator": "CODEX-INVESTIGATOR", "assistant": "CODEX-ASSISTANT", "case_stage": "一审"}
        self.fee.data = {**self.fee.data, "payer_name": "CODEX-PAYER", "payment_mode": "转账", "received_date": "2026-09-12"}
        self.record("invoice", "PARTIAL-INVOICE", status="待审批", data={
            "amount": 30, "case_fee_ids": [self.fee.id], "case_fee_allocations": [{"fee_id": self.fee.id, "amount": 30}]})
        await self.db.commit()
        result = await routes.contract_invoice_candidates(self.contract.id, ADMIN, self.db)
        self.assertEqual(result["total"], 1)
        row = result["items"][0]
        self.assertEqual((row["amount"], row["invoiceable_amount"], row["invoiced_amount"]), (100, 70, 30))
        self.assertEqual(row["contract_no"], self.contract.serial_no)
        self.assertEqual(row["external_contract_no"], "CODEX-EXTERNAL")
        for key, value in {"court_name": "CODEX-COURT", "court_lawyer": "CODEX-LAWYER", "investigator": "CODEX-INVESTIGATOR",
                           "case_assistant": "CODEX-ASSISTANT", "payer_name": "CODEX-PAYER", "payment_mode": "转账",
                           "received_date": "2026-09-12"}.items():
            self.assertEqual(row[key], value, key)

    async def test_stale_second_session_cannot_pay_after_rollback(self):
        original = await self.create()
        await routes.review_contract_payment_application(original["id"], ContractPaymentReviewInput(approved=True), ADMIN, self.db)
        async with async_sessionmaker(self.engine, expire_on_commit=False)() as other:
            stale = await other.get(BusinessRecord, original["id"])
            self.assertEqual(stale.status, "待付款")
            await other.commit()
            await routes.rollback_contract_payment_application(original["id"], NOTE, ADMIN, self.db)
            with self.assertRaises(HTTPException) as caught:
                await routes.pay_contract_payment_application(original["id"], ContractPaymentPayInput(paid_date=date.today(), voucher_no="CODEX-STALE"), ADMIN, other)
            self.assertEqual(caught.exception.status_code, 409)
            self.assertEqual(await other.scalar(select(func.count(FinanceTransaction.id))), 0)

    async def test_invoice_candidates_count_other_applicant_without_disclosing_invoice(self):
        from app.core.finance import _invoice_fee_details
        from app.core.permissions import _ensure_record_visible
        self.db.add(User(username="CODEX-OTHER", password_hash="isolated", role="staff", department="CODEX-OTHER"))
        own_invoice = self.record("invoice", "OWN-INVOICE", status="待审批", data={
            "amount": 10, "case_fee_ids": [self.fee.id],
            "case_fee_allocations": [{"fee_id": self.fee.id, "amount": 10}], "invoice_no": "CODEX-OWN-INVOICE"})
        hidden = self.record("invoice", "PRIVATE-INVOICE", status="待审批", owner="CODEX-OTHER", data={
            "amount": 30, "case_fee_ids": [self.fee.id], "invoice_no": "CODEX-PRIVATE-NUMBER",
            "invoice_date": "2026-09-13", "case_fee_allocations": [{"fee_id": self.fee.id, "amount": 30}]})
        self.record("invoice", "PRIVATE-RELEASED", status="已撤回", owner="CODEX-OTHER", data={
            "amount": 40, "case_fee_ids": [self.fee.id], "case_fee_allocations": [{"fee_id": self.fee.id, "amount": 40}]})
        forbidden_fee = self.record("finance", "PRIVATE-FEE", owner="CODEX-OTHER", data={
            **self.fee.data, "amount": 200})
        await self.db.flush()
        self.record("invoice", "PRIVATE-UNRELATED", status="待审批", owner="CODEX-OTHER", data={
            "amount": 90, "case_fee_ids": [forbidden_fee.id],
            "case_fee_allocations": [{"fee_id": forbidden_fee.id, "amount": 90}]})
        await self.db.commit()
        reader = {"username": "admin", "role": "staff"}
        permission = {"data_scope": "本人数据", "menu_keys": ["contract-mine"], "field_keys": ["finance.amount"], "action_keys": []}
        with patch("app.core.permissions._user_permission_payload", AsyncMock(return_value=permission)), \
             patch("app.core.permissions._require_record_module_menu", AsyncMock()), \
             patch("app.core.system._allowed_field_keys", AsyncMock(return_value={"finance.amount"})):
            with self.assertRaises(HTTPException):
                await _ensure_record_visible(hidden.id, reader, self.db)
            result = await routes.contract_invoice_candidates(self.contract.id, reader, self.db)
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"][0]["invoiceable_amount"], 60)
            self.assertEqual(result["items"][0]["invoiced_amount"], 40)
            details = await _invoice_fee_details(reader, self.db, ids={self.fee.id, forbidden_fee.id})
            self.assertEqual([item["id"] for item in details], [self.fee.id])
            self.assertEqual(details[0]["data"]["invoice_record_id"], own_invoice.id)
            self.assertEqual(details[0]["data"]["invoice_no"], "CODEX-OWN-INVOICE")
            self.assertNotIn("CODEX-PRIVATE", str(result) + str(details))
            own_invoice.status = "已撤回"
            await self.db.commit()
            hidden_only = (await _invoice_fee_details(reader, self.db, ids={self.fee.id}))[0]["data"]
            self.assertEqual(hidden_only["remaining_invoice_amount"], 70)
            self.assertIsNone(hidden_only["invoice_record_id"])
            self.assertEqual(hidden_only["invoice_no"], "")
            self.assertEqual(hidden_only["invoice_date"], "")

    async def test_concurrent_creates_cannot_reserve_more_than_fee(self):
        import asyncio
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="CODEX-CPI-ISOLATED-") as directory:
            engine = create_async_engine(f"sqlite+aiosqlite:///{(Path(directory) / 'isolated.db').as_posix()}")
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                async with sessions() as db:
                    db.add(User(username="admin", password_hash="isolated", department="CODEX-CPI"))
                    contract = BusinessRecord(module="contract", serial_no="CODEX-RACE-C", title="CODEX", customer="CODEX", owner="admin", department="CODEX-CPI", status="草稿", data={})
                    case = BusinessRecord(module="case", serial_no="CODEX-RACE-CASE", title="CODEX", customer="CODEX", owner="admin", department="CODEX-CPI", status="在办", data={})
                    payment_type = SystemParameter(category="payment_type", code="CODEX-RACE-TYPE", name="CODEX",
                        extra={"nature": "案件付款", "payee": "CODEX", "account_bank": "CODEX", "account": "CODEX"},
                        is_active=True, created_by="admin", updated_by="admin")
                    db.add_all([contract, case, payment_type])
                    await db.flush()
                    fee = BusinessRecord(module="finance", serial_no="CODEX-RACE-FEE", title="CODEX", customer="CODEX", owner="admin", department="CODEX-CPI", status="草稿",
                        data={"contract_id": contract.id, "case_id": case.id, "case_no": case.serial_no, "fee_type": "官方费用", "amount": 100})
                    db.add(fee)
                    await db.commit()
                    body = ContractPaymentApplicationInput(payment_type_id=payment_type.id, application_date=date.today(), lines=[{"case_fee_id": fee.id, "amount": 70}])
                    contract_id = contract.id
                async def writer():
                    async with sessions() as db:
                        try:
                            await routes.create_contract_payment_application(contract_id, body, ADMIN, db)
                            return "created"
                        except HTTPException as exc:
                            await db.rollback()
                            return exc.status_code
                outcomes = await asyncio.gather(writer(), writer())
                self.assertEqual(outcomes.count("created"), 1, outcomes)
                self.assertTrue(any(value in {409, 422} for value in outcomes), outcomes)
                async with sessions() as db:
                    payments = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "contract_payment"))).all())
                    self.assertEqual(sum(row.data["amount"] for row in payments), 70)
            finally:
                await engine.dispose()

    async def test_legacy_scalar_lines_and_empty_amount_do_not_break_query(self):
        for index, lines in enumerate([None, {}, "legacy", 1]):
            self.record("contract_payment", f"SCALAR-{index}", data={"lines": lines, "amount": ""})
        self.record("contract_payment", "SCALAR-DECIMAL", data={"lines": [], "amount": "12.50"})
        await self.db.commit()
        filtered = await query_payments({"keyword": "SCALAR", "fee_type": "official"}, ADMIN, self.db)
        self.assertEqual(filtered["total"], 0)
        total = await query_payments({"keyword": "SCALAR"}, ADMIN, self.db)
        self.assertEqual(total["totals"]["amount"], 12.5)


class PostgreSQLPaymentQueryShapeTest(unittest.TestCase):
    def test_json_array_and_amount_casts_are_guarded(self):
        from sqlalchemy.dialects import postgresql
        statement = select(BusinessRecord.id, payment_query_amount(BusinessRecord, "postgresql")).where(
            payment_query_line_match(BusinessRecord, "fee_type", "official", "postgresql"))
        sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("json_array_elements(CASE WHEN", sql)
        self.assertIn("json_typeof", sql)
        self.assertIn("ELSE CAST('[]' AS JSON)", sql)
        self.assertIn("~", sql)
        self.assertIn("CASE WHEN", sql)
        self.assertIn("AS FLOAT", sql)


if __name__ == "__main__":
    unittest.main()

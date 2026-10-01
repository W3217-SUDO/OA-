"""8.31 row 19: case fee links retain contract, receipt and invoice relations."""

from __future__ import annotations

from datetime import date
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row19-admin", "role": "admin", "display_name": "第十九行管理员", "department": "财务部"}


class CaseFeeLegacyLinksRow19Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True))
            customer = BusinessRecord(module="customer", serial_no="CODEX-831-19-CUSTOMER", title="第十九行客户", customer="第十九行客户", status="active", owner=ADMIN["username"], department=ADMIN["department"])
            contract = BusinessRecord(module="contract", serial_no="CODEX-831-19-CONTRACT", title="第十九行合同", customer=customer.title, status="approved", owner=ADMIN["username"], department=ADMIN["department"])
            db.add_all([customer, contract]); await db.flush()
            case_record = BusinessRecord(module="case", serial_no="CODEX-831-19-CASE", title="第十九行案件", customer=customer.title, status="一审准备开庭", owner=ADMIN["username"], department=ADMIN["department"], data={"contract_id": contract.id, "contract_no": contract.serial_no, "plaintiff": customer.title})
            db.add(case_record); await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-831-19-FEE", title="诉讼费", customer=customer.title, status="草稿", owner=ADMIN["username"], department=ADMIN["department"], data={"amount": 8400, "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "诉讼代理费", "case_id": case_record.id, "case_no": case_record.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no})
            db.add(fee); await db.flush()
            payment = IncomingPayment(receipt_no="CODEX-831-19-RECEIPT-A", received_date=date(2026, 8, 30), amount=6000, payer_name="第十九行付款人甲", bank_reference="CODEX-831-19-BANK-A", status="待分配", claimed_customer=customer.title, claimant=ADMIN["username"], operator=ADMIN["username"])
            payment2 = IncomingPayment(receipt_no="CODEX-831-19-RECEIPT-B", received_date=date(2026, 8, 31), amount=2400, payer_name="第十九行付款人乙", bank_reference="CODEX-831-19-BANK-B", status="待分配", claimed_customer=customer.title, claimant=ADMIN["username"], operator=ADMIN["username"])
            invoice = BusinessRecord(module="invoice", serial_no="CODEX-831-19-INVOICE", title="第十九行发票", customer=customer.title, status="已开票", owner=ADMIN["username"], department=ADMIN["department"], data={"case_fee_ids": [fee.id], "invoice_no": "FP-831-19", "invoice_date": "2026-08-31"})
            db.add_all([payment, payment2, invoice]); await db.commit()
            self.case_id, self.fee_id, self.payment_ids, self.invoice_id = case_record.id, fee.id, [payment.id, payment2.id], invoice.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row19.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_case_relations_expose_clickable_legacy_targets(self) -> None:
        for payment_id, amount in zip(self.payment_ids, (6000, 2400), strict=True):
            allocation = await self.client.post(f"{API}/finance/incoming-payments/{payment_id}/allocate", json={"allocations": [{
                "fee_record_id": self.fee_id,
                "amount": amount,
                "case_no": "CODEX-831-19-CASE",
                "payment_method": "bank",
                "settlement_items": [{"fee_record_id": self.fee_id, "fee_type": "官方费用", "amount": amount, "settlement_amount": amount, "archive_fee": 0}],
            }]})
            self.assertEqual(allocation.status_code, 200, allocation.text)
        response = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(response.status_code, 200, response.text)
        fee = next(item for item in response.json()["fees"] if item["id"] == self.fee_id)
        self.assertEqual(fee["data"]["contract_no"], "CODEX-831-19-CONTRACT")
        self.assertEqual(fee["data"]["incoming_payment_id"], self.payment_ids[1])
        self.assertEqual(fee["data"]["receipt_no"], "CODEX-831-19-RECEIPT-B")
        self.assertEqual(fee["data"]["received_at"], "2026-08-31")
        self.assertEqual(fee["data"]["received_amount"], 8400)
        self.assertEqual(
            [(item["receipt_no"], item["allocated_amount"]) for item in fee["data"]["incoming_payments"]],
            [("CODEX-831-19-RECEIPT-B", 2400), ("CODEX-831-19-RECEIPT-A", 6000)],
        )
        self.assertEqual(fee["data"]["invoice_record_id"], self.invoice_id)
        self.assertEqual(fee["data"]["invoice_no"], "FP-831-19")
        self.assertEqual(fee["data"]["invoice_date"], "2026-08-31")


if __name__ == "__main__":
    unittest.main()

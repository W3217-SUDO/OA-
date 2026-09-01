"""9.1 row 30: allocated receipts remain visible on their case fee."""

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
ADMIN = {"username": "row30-admin", "role": "admin", "display_name": "Row 30 Admin", "department": "Finance"}


class CaseFeeReceiptProjectionRow30Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True))
            customer = BusinessRecord(module="customer", serial_no="ROW30-CUSTOMER", title="Row 30 Customer", customer="Row 30 Customer", status="active", owner=ADMIN["username"], department=ADMIN["department"])
            contract = BusinessRecord(module="contract", serial_no="ROW30-CONTRACT", title="Row 30 Contract", customer=customer.title, status="approved", owner=ADMIN["username"], department=ADMIN["department"])
            db.add_all([customer, contract]); await db.flush()
            case_record = BusinessRecord(module="case", serial_no="ROW30-CASE", title="Row 30 Case", customer=customer.title, status="active", owner=ADMIN["username"], department=ADMIN["department"], data={"contract_id": contract.id, "contract_no": contract.serial_no})
            db.add(case_record); await db.flush()
            fee = BusinessRecord(module="finance", serial_no="ROW30-FEE", title="Row 30 Fee", customer=customer.title, status="pending", owner=ADMIN["username"], department=ADMIN["department"], data={"amount": 8400, "fee_type": "court fee", "case_id": case_record.id, "case_no": case_record.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no})
            payment = IncomingPayment(receipt_no="ROW30-RECEIPT", received_date=date(2026, 8, 28), amount=8400, payer_name="Row 30 Payer", bank_reference="ROW30-BANK", status="待分配", claimed_customer=customer.title, claimant=ADMIN["username"], operator=ADMIN["username"])
            db.add_all([fee, payment]); await db.commit()
            self.case_id, self.fee_id, self.payment_id = case_record.id, fee.id, payment.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row30.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_real_allocation_survives_customer_name_change(self) -> None:
        allocation = await self.client.post(f"{API}/finance/incoming-payments/{self.payment_id}/allocate", json={"allocations": [{
            "fee_record_id": self.fee_id,
            "amount": 8400,
            "case_no": "ROW30-CASE",
            "payment_method": "bank",
            "settlement_items": [{"fee_record_id": self.fee_id, "fee_type": "court fee", "amount": 8400, "settlement_amount": 8400, "archive_fee": 0}],
        }]})
        self.assertEqual(allocation.status_code, 200, allocation.text)

        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, self.case_id)
            case_record.customer = "Row 30 Customer Renamed"
            await db.commit()

        response = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(response.status_code, 200, response.text)
        fee = next(item for item in response.json()["fees"] if item["id"] == self.fee_id)
        self.assertEqual(fee["data"]["received_amount"], 8400)
        self.assertEqual(fee["data"]["received_at"], "2026-08-28")
        self.assertEqual(fee["data"]["incoming_payments"][0]["id"], self.payment_id)
        self.assertEqual(fee["data"]["incoming_payments"][0]["allocated_amount"], 8400)


if __name__ == "__main__":
    unittest.main()

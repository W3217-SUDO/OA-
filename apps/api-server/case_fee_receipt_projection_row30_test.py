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
            # Legacy cases can predate the contract relation while a newly entered
            # fee carries both stable case and contract ids.
            case_record = BusinessRecord(module="case", serial_no="ROW30-CASE", title="Row 30 Case", customer=customer.title, status="active", owner=ADMIN["username"], department=ADMIN["department"], data={"case_type": "Civil dispute"})
            db.add(case_record); await db.flush()
            fee = BusinessRecord(module="finance", serial_no="ROW30-FEE", title="Row 30 Fee", customer=customer.title, status="pending", owner=ADMIN["username"], department=ADMIN["department"], data={"amount": 8400, "fee_type": "court fee", "case_id": case_record.id, "case_no": case_record.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no, "legacy_case_fee_id": 42738})
            payment = IncomingPayment(receipt_no="ROW30-RECEIPT", received_date=date(2026, 8, 28), amount=8400, payer_name="Row 30 Payer", bank_reference="ROW30-BANK", bank_source="Bank transfer", status="待分配", claimed_customer=customer.title, claimant=ADMIN["username"], operator=ADMIN["username"])
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
            "case_id": self.case_id,
            "contract_no": "ROW30-CONTRACT",
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
        receipt = fee["data"]["incoming_payments"][0]
        self.assertEqual(receipt["contract_no"], "ROW30-CONTRACT")
        self.assertEqual(receipt["customer_name"], "Row 30 Customer")
        self.assertEqual(receipt["amount"], 8400)
        self.assertEqual(receipt["assigned_official_fee"], 8400)
        self.assertEqual(receipt["assigned_agency_fee"], 0)
        self.assertEqual(receipt["payment_method"], "bank")

        detail_response = await self.client.get(f"{API}/finance/incoming-payments/{self.payment_id}")
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        detail = detail_response.json()
        self.assertEqual(detail["receipt_no"], "ROW30-RECEIPT")
        self.assertEqual(detail["contract_no"], "ROW30-CONTRACT")
        self.assertEqual(detail["payment_method"], "bank")
        self.assertEqual(detail["allocated_amount"], 8400)
        self.assertEqual(detail["remaining_amount"], 0)
        self.assertEqual(detail["claimant_display_name"], ADMIN["display_name"])
        self.assertEqual(detail["assigned_official_fee"], 8400)
        self.assertEqual(len(detail["allocation_details"]), 1)
        allocation_detail = detail["allocation_details"][0]
        self.assertEqual(allocation_detail["case_type"], "Civil dispute")
        self.assertEqual(allocation_detail["case_name"], "Row 30 Case")
        self.assertEqual(allocation_detail["case_no"], "ROW30-CASE")
        self.assertEqual(allocation_detail["contract_no"], "ROW30-CONTRACT")
        self.assertEqual(allocation_detail["fee_total_amount"], 8400)
        self.assertEqual(allocation_detail["fee_allocated_amount"], 8400)
        self.assertEqual(allocation_detail["current_amount"], 8400)

    async def test_migrated_allocation_resolves_legacy_case_fee_id(self) -> None:
        async with self.sessions() as db:
            payment = await db.get(IncomingPayment, self.payment_id)
            payment.allocations = [{
                "case_no": "ROW30-CASE",
                "amount": 8400,
                "settlement_items": [{
                    "legacy_case_fee_id": 42738,
                    "fee_type": "court fee",
                    "amount": 0,
                    "settlement_amount": 8400,
                }],
            }]
            db.add(IncomingPayment(
                receipt_no="ROW30-OTHER-CASE-RECEIPT",
                received_date=date(2026, 8, 29),
                amount=999,
                payer_name="Other case payer",
                bank_reference="ROW30-OTHER-BANK",
                status="allocated",
                claimed_customer="Other customer",
                claimant=ADMIN["username"],
                operator=ADMIN["username"],
                allocations=[{
                    "case_no": "ROW30-OTHER-CASE",
                    "amount": 999,
                    "settlement_items": [{
                        "legacy_case_fee_id": 42738,
                        "amount": 0,
                        "settlement_amount": 999,
                    }],
                }],
            ))
            await db.commit()

        response = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(response.status_code, 200, response.text)
        fee = next(item for item in response.json()["fees"] if item["id"] == self.fee_id)
        self.assertEqual(fee["data"]["received_amount"], 8400)
        self.assertEqual(fee["data"]["received_at"], "2026-08-28")
        self.assertEqual(fee["data"]["incoming_payments"][0]["receipt_no"], "ROW30-RECEIPT")


if __name__ == "__main__":
    unittest.main()

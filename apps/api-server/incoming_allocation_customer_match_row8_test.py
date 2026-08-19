"""8.18 row 8: allocation candidates must stay inside the claimed customer."""

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
ADMIN = {
    "username": "row8-admin",
    "role": "admin",
    "display_name": "Row 8 Admin",
    "department": "Finance",
}


class IncomingAllocationCustomerMatchRow8Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username="row8-admin", display_name="Row 8 Admin",
                department="Finance", role="admin", password_hash="x", is_active=True,
            ))
            customer_a = BusinessRecord(
                module="customer", serial_no="CODEX-818-R8-CUSTOMER-A",
                title="CODEX Row 8 Customer A", customer="CODEX Row 8 Customer A",
                status="active", owner="row8-admin", department="Finance",
            )
            customer_b = BusinessRecord(
                module="customer", serial_no="CODEX-818-R8-CUSTOMER-B",
                title="CODEX Row 8 Customer B", customer="CODEX Row 8 Customer B",
                status="active", owner="row8-admin", department="Finance",
            )
            contract_a = BusinessRecord(
                module="contract", serial_no="CODEX-818-R8-CONTRACT-A",
                title="CODEX Row 8 Contract A", customer=customer_a.customer,
                status="approved", owner="row8-admin", department="Finance",
            )
            contract_b = BusinessRecord(
                module="contract", serial_no="CODEX-818-R8-CONTRACT-B",
                title="CODEX Row 8 Contract B", customer=customer_b.customer,
                status="approved", owner="row8-admin", department="Finance",
            )
            db.add_all([customer_a, customer_b, contract_a, contract_b])
            await db.flush()
            valid_case = BusinessRecord(
                module="case", serial_no="CODEX-818-R8-CASE-A",
                title="CODEX Row 8 Valid Case", customer=customer_a.customer,
                status="open", owner="row8-admin", department="Finance",
                data={"contract_id": contract_a.id, "contract_no": contract_a.serial_no},
            )
            stale_customer_fee = BusinessRecord(
                module="finance", serial_no="CODEX-818-R8-FEE-STALE",
                title="CODEX Row 8 Stale Customer Fee", customer=customer_a.customer,
                status="paid", owner="row8-admin", department="Finance",
                data={"amount": 100, "fee_type": "代理费", "case_id": 0,
                      "case_no": "CODEX-818-R8-CASE-A", "contract_id": contract_b.id,
                      "contract_no": contract_b.serial_no},
            )
            valid_fee = BusinessRecord(
                module="finance", serial_no="CODEX-818-R8-FEE-VALID",
                title="CODEX Row 8 Valid Fee", customer=customer_a.customer,
                status="paid", owner="row8-admin", department="Finance",
                data={"amount": 100, "fee_type": "代理费", "case_id": 0,
                      "case_no": valid_case.serial_no, "contract_id": contract_a.id,
                      "contract_no": contract_a.serial_no},
            )
            payment = IncomingPayment(
                receipt_no="CODEX-818-R8-RECEIPT", received_date=date.today(),
                amount=100, payer_name="CODEX Row 8 Payer",
                bank_reference="CODEX-818-R8-BANK", status="待分配",
                claimed_customer=customer_a.customer, claimant="row8-admin",
                operator="row8-admin",
            )
            db.add_all([valid_case, stale_customer_fee, valid_fee, payment])
            await db.commit()
            self.payment_id = payment.id
            self.valid_fee_id = valid_fee.id
            self.valid_case_no = valid_case.serial_no

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row8.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_candidates_filter_linked_contract_customer(self) -> None:
        response = await self.client.get(
            f"{API}/finance/incoming-payments/{self.payment_id}/allocation-candidates",
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()["items"]
        self.assertEqual([row["fee_record_id"] for row in rows], [self.valid_fee_id])
        self.assertEqual(rows[0]["case_no"], self.valid_case_no)

        allocation = await self.client.post(
            f"{API}/finance/incoming-payments/{self.payment_id}/allocate",
            json={"allocations": [{
                "fee_record_id": self.valid_fee_id,
                "case_no": self.valid_case_no,
                "amount": 100,
            }]},
        )
        self.assertEqual(allocation.status_code, 200, allocation.text)


if __name__ == "__main__":
    unittest.main()

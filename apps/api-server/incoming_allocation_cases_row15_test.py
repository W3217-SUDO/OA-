"""8.14 row 15: show every unpaid customer case and split one plan across cases."""

from __future__ import annotations

from datetime import date
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, ReceivablePlan, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {
    "username": "row15-admin",
    "role": "admin",
    "display_name": "Row 15 Admin",
    "department": "Finance",
}


class IncomingAllocationCasesRow15Test(unittest.IsolatedAsyncioTestCase):
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
                username="row15-admin", display_name="Row 15 Admin",
                department="Finance", role="admin", password_hash="x", is_active=True,
            ))
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-814-R15-CUSTOMER",
                title="CODEX Row 15 Customer", customer="CODEX Row 15 Customer",
                status="签约", owner="row15-admin", department="Finance", data={},
            )
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-814-R15-CONTRACT",
                title="CODEX Row 15 Contract", customer="CODEX Row 15 Customer",
                status="履行中", owner="row15-admin", department="Finance", data={},
            )
            db.add_all([customer, contract])
            await db.flush()
            case_one = BusinessRecord(
                module="case", serial_no="CODEX-814-R15-CASE-1",
                title="Row 15 Case One", customer=contract.customer,
                status="一审立案受理", owner="row15-admin", department="Finance",
                data={"contract_id": contract.id, "plaintiff": "原告甲", "defendant": "被告甲", "case_stage": "一审立案受理"},
            )
            case_two = BusinessRecord(
                module="case", serial_no="CODEX-814-R15-CASE-2",
                title="Row 15 Case Two", customer=contract.customer,
                status="一审和解结案", owner="row15-admin", department="Finance",
                data={"contract_no": contract.serial_no, "plaintiff": "原告乙", "defendant": "被告乙", "case_stage": "一审和解结案"},
            )
            plan = ReceivablePlan(
                contract_record_id=contract.id, phase="律师代理费",
                due_date=date.today(), amount=3000, received_amount=0,
                status="待收款", payer=contract.customer,
            )
            payment = IncomingPayment(
                receipt_no="CODEX-814-R15-RECEIPT", received_date=date.today(),
                amount=3000, payer_name="CODEX Row 15 Payer",
                bank_reference="CODEX-814-R15-BANK", status="待分配",
                claimed_customer=contract.customer, claimant="row15-admin",
                operator="row15-admin",
            )
            db.add_all([case_one, case_two, plan, payment])
            await db.commit()
            self.payment_id = payment.id
            self.plan_id = plan.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row15.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_candidates_and_split_allocation_cover_all_customer_cases(self) -> None:
        response = await self.client.get(
            f"{API}/finance/incoming-payments/{self.payment_id}/allocation-candidates",
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()["items"]
        self.assertEqual({row["case_no"] for row in rows}, {
            "CODEX-814-R15-CASE-1", "CODEX-814-R15-CASE-2",
        })
        self.assertTrue(all(row["remaining_amount"] == 3000 for row in rows))

        allocation = await self.client.post(
            f"{API}/finance/incoming-payments/{self.payment_id}/allocate",
            json={
                "allocations": [
                    {"receivable_plan_id": self.plan_id, "case_no": rows[0]["case_no"], "amount": 1200},
                    {"receivable_plan_id": self.plan_id, "case_no": rows[1]["case_no"], "amount": 1800},
                ],
                "comment": "row 15 split allocation",
            },
        )
        self.assertEqual(allocation.status_code, 200, allocation.text)
        self.assertEqual(allocation.json()["status"], "已分配")
        self.assertEqual(len(allocation.json()["allocations"]), 2)
        async with self.sessions() as db:
            plan = await db.get(ReceivablePlan, self.plan_id)
            self.assertEqual(plan.received_amount, 3000)
            self.assertEqual(plan.status, "已收款")


if __name__ == "__main__":
    unittest.main()

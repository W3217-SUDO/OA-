"""8.14 row 14: claimed receipts expose the linked customer's manager name."""

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
ADMIN = {
    "username": "row14-admin",
    "role": "admin",
    "display_name": "Row 14 Admin",
    "department": "Finance",
}


class IncomingCustomerManagerRow14Test(unittest.IsolatedAsyncioTestCase):
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
            db.add_all([
                User(
                    username="row14-admin",
                    display_name="Row 14 Admin",
                    department="Finance",
                    role="admin",
                    password_hash="x",
                    is_active=True,
                ),
                User(
                    username="row14-manager",
                    display_name="真实客户管理人",
                    department="Brand Department",
                    role="user",
                    password_hash="x",
                    is_active=True,
                ),
                BusinessRecord(
                    module="customer",
                    serial_no="CODEX-814-R14-CUSTOMER",
                    title="CODEX Row 14 Customer",
                    customer="CODEX Row 14 Customer",
                    status="签约",
                    owner="row14-manager",
                    department="Brand Department",
                    data={"customer_managers": ["row14-manager"]},
                ),
                IncomingPayment(
                    receipt_no="CODEX-814-R14-RECEIPT",
                    received_date=date.today(),
                    amount=1,
                    payer_name="CODEX Row 14 Payer",
                    bank_reference="CODEX-814-R14-BANK",
                    status="待分配",
                    claimed_customer="CODEX Row 14 Customer",
                    claimant="row14-admin",
                    operator="row14-admin",
                ),
            ])
            await db.commit()

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row14.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_list_returns_customer_manager_username_and_display_name(self) -> None:
        response = await self.client.get(f"{API}/finance/incoming-payments")
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["customer_manager"], "row14-manager")
        self.assertEqual(item["customer_manager_display_name"], "真实客户管理人")
        self.assertEqual(item["claimant_display_name"], "Row 14 Admin")


if __name__ == "__main__":
    unittest.main()

"""8.31 row 5: receipt claiming searches customers and preserves a missing bank reference."""

import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {
    "username": "row5-admin",
    "role": "admin",
    "display_name": "第五行管理员",
    "department": "上海分所",
}
CUSTOMER = "CODEX 8.31 系统客户"


class FinanceReceiptClaimRow5Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username="row5-admin",
                display_name="第五行管理员",
                department="上海分所",
                role="admin",
                password_hash="test",
                is_active=True,
            ))
            db.add_all([
                BusinessRecord(
                    module="customer",
                    serial_no="CODEX-831-R5-CUSTOMER",
                    title=CUSTOMER,
                    customer=CUSTOMER,
                    status="正常",
                    owner="row5-admin",
                    department="上海分所",
                    data={"customer_type": "客户"},
                ),
                BusinessRecord(
                    module="customer",
                    serial_no="CODEX-831-R5-LITIGANT",
                    title="CODEX 8.31 当事人",
                    customer="CODEX 8.31 当事人",
                    status="正常",
                    owner="row5-admin",
                    department="上海分所",
                    data={"customer_type": "当事人"},
                ),
            ])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://row5.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_blank_bank_references_remain_blank_and_customer_can_be_claimed(self):
        created_ids = []
        for suffix in ("A", "B"):
            response = await self.client.post(f"{API}/finance/incoming-payments", json={
                "received_date": "2026-08-31",
                "amount": 5,
                "payer_name": f"CODEX 8.31 回款单位{suffix}",
                "bank_reference": "",
            })
            self.assertEqual(response.status_code, 201, response.text)
            self.assertIsNone(response.json()["bank_reference"])
            created_ids.append(response.json()["id"])

        options = await self.client.get(
            f"{API}/finance/customer-options",
            params={"keyword": "8.31"},
        )
        self.assertEqual(options.status_code, 200, options.text)
        self.assertEqual(
            [(item["title"], item["serial_no"]) for item in options.json()["items"]],
            [(CUSTOMER, "CODEX-831-R5-CUSTOMER")],
        )

        claimed = await self.client.post(
            f"{API}/finance/incoming-payments/{created_ids[0]}/claim",
            json={"customer": CUSTOMER, "comment": "第5行认领验收"},
        )
        self.assertEqual(claimed.status_code, 200, claimed.text)
        self.assertEqual(claimed.json()["claimed_customer"], CUSTOMER)
        self.assertEqual(claimed.json()["status"], "待分配")
        self.assertIsNone(claimed.json()["bank_reference"])

        async with self.sessions() as db:
            blank_count = await db.scalar(
                select(func.count()).select_from(IncomingPayment).where(
                    IncomingPayment.bank_reference.is_(None)
                )
            )
            self.assertEqual(blank_count, 2)

    async def test_real_bank_reference_remains_unique(self):
        payload = {
            "received_date": "2026-08-31",
            "amount": 10,
            "payer_name": "CODEX 8.31 已生成单号",
            "bank_reference": "260831-12345",
        }
        first = await self.client.post(f"{API}/finance/incoming-payments", json=payload)
        second = await self.client.post(f"{API}/finance/incoming-payments", json=payload)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 409, second.text)


if __name__ == "__main__":
    unittest.main()

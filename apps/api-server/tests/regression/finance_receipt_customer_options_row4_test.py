"""8.31 row 4: receipt customer search uses customer records, not litigants."""

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row4-admin", "role": "admin", "display_name": "第4行管理员", "department": "上海分所"}


class FinanceReceiptCustomerOptionsRow4Test(unittest.IsolatedAsyncioTestCase):
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
            db.add(User(username="row4-admin", display_name="第4行管理员", department="上海分所", role="admin", password_hash="test", is_active=True))
            db.add_all([
                BusinessRecord(module="customer", serial_no="CODEX-831-CUSTOMER", title="CODEX 8.31 系统客户", customer="CODEX 8.31 系统客户", status="正常", owner="row4-admin", department="上海分所", data={"customer_type": "客户"}),
                BusinessRecord(module="customer", serial_no="CODEX-831-LITIGANT", title="CODEX 8.31 当事人", customer="CODEX 8.31 当事人", status="正常", owner="row4-admin", department="上海分所", data={"customer_type": "当事人"}),
                BusinessRecord(module="customer", serial_no="CODEX-831-RECYCLED", title="CODEX 8.31 回收客户", customer="CODEX 8.31 回收客户", status="已回收", owner="row4-admin", department="上海分所", data={"customer_type": "客户"}),
            ])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row4.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_keyword_returns_only_active_system_customer(self):
        response = await self.client.get(f"{API}/finance/customer-options", params={"keyword": "8.31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [{
            "id": response.json()["items"][0]["id"],
            "title": "CODEX 8.31 系统客户",
            "serial_no": "CODEX-831-CUSTOMER",
        }])

    async def test_non_finance_registration_role_is_denied(self):
        app.dependency_overrides[current_identity] = lambda: {**ADMIN, "role": "user"}
        response = await self.client.get(f"{API}/finance/customer-options")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

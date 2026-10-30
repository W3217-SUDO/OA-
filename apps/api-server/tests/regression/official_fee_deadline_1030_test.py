"""BUG20261030002（范明明 2026-10-30）：官方费用申请付款必须有缴费截止日期，没填不能提交。"""

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
IDENTITY = {"username": "r1030-002", "role": "admin", "display_name": "R1030", "department": "上海分所"}


class OfficialFeeDeadlineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="R1030", department="上海分所", role="admin",
                        password_hash="x", is_active=True))
            self.fees = {}
            for name, fee_type, extra in (("official", "官方费用", {}), ("official_with_deadline", "官方费用", {"deadline": "2026-11-10"}),
                                          ("other", "其他费用", {})):
                fee = BusinessRecord(module="finance", serial_no=f"FY-R1030-{name}", title=name, status="草稿",
                                     owner=IDENTITY["username"], department="上海分所", data={
                                         "fee_type": fee_type, "expense_scope": "律所", "expense_subtype": "一审诉讼费",
                                         "amount": 100, "handler": IDENTITY["username"], **extra,
                                     })
                db.add(fee)
                await db.flush()
                self.fees[name] = fee.id
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://r1030.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def submit(self, name, **extra):
        return await self.client.post(f"{API}/finance/fees/{self.fees[name]}/submit", json={"amount": 100, "comment": "申请付款", **extra})

    async def fee_data(self, name):
        async with self.sessions() as db:
            return (await db.get(BusinessRecord, self.fees[name])).data

    async def test_official_fee_without_deadline_is_rejected(self):
        response = await self.submit("official")
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("缴费截止日期", response.text)

    async def test_deadline_from_request_is_saved(self):
        response = await self.submit("official", deadline="2026-11-05")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.fee_data("official"))["deadline"], "2026-11-05")

    async def test_existing_fee_deadline_counts(self):
        response = await self.submit("official_with_deadline")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.fee_data("official_with_deadline"))["deadline"], "2026-11-10")

    async def test_other_fee_needs_no_deadline(self):
        async with self.sessions() as db:
            from app.models import SystemParameter
            parameter = SystemParameter(category="payment_type", code="R1030", name="R1030 收款单位",
                                        extra={"payee": "R1030 收款单位", "account": "6222", "account_bank": "工行", "nature": "其他费用"})
            db.add(parameter)
            await db.commit()
            payment_type_id = parameter.id
        response = await self.submit("other", payment_type_id=payment_type_id)
        self.assertNotEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()

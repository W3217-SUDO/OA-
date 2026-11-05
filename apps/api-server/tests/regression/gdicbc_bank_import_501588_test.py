"""501588（审核管理 11-05）：回款(国定工行)改成和工行一样上传导入；工行页不带国定工行的流水。"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance import bank_flows, incoming_payments
from app.core import soft_delete
from app.core.dependencies import get_db
from app.database import Base
from app.models import BankStatementLine, IncomingPayment, User
from app.security import current_identity

ADMIN = {"username": "fadmin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "管理员", "department": "财务部", "action_keys": ["*"]}
API = "/api/v1"
CSV = "对方户名,银行流水号,到账日期,到账金额\n甲公司,BF-1,2026-10-30,100\n乙公司,BF-2,2026-10-31,250.5\n".encode("utf-8-sig")


class GdicbcBankImport501588Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add(User(username="fadmin", display_name="管理员", password_hash="x", department="财务部", role="admin"))
            await db.commit()
        app = FastAPI()
        app.include_router(incoming_payments.router)
        app.include_router(bank_flows.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ADMIN)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _upload(self, bank):
        params = {"finance_scope": "firm"}
        preview = await self.client.post(f"{API}/finance/incoming-payments/import", params=params,
                                         files={"file": ("bank.csv", CSV, "text/csv")}, data={"bank_source": bank})
        self.assertEqual(preview.status_code, 200, preview.text)
        confirmed = await self.client.post(f"{API}/finance/incoming-payments/import", params=params,
                                           files={"file": ("bank.csv", CSV, "text/csv")},
                                           data={"bank_source": bank, "confirmation_token": preview.json()["confirmation_token"]})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        return confirmed.json()

    async def _receipts(self, bank):
        response = await self.client.get(f"{API}/finance/incoming-payments",
                                         params={"finance_scope": "firm", "view": f"finance-receipts-{bank}", "bank_source": bank})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        return data["items"] if isinstance(data, dict) else data

    async def test_gdicbc_upload_generates_receipts_only_on_its_own_page(self):
        self.assertEqual((await self._upload("gdicbc"))["created"], 2)
        lines = (await self.client.get(f"{API}/finance/bank-flows/lines", params={"finance_scope": "firm", "bank": "gdicbc"})).json()
        self.assertEqual(lines["total"], 2)
        self.assertEqual({item["bank_label"] for item in lines["items"]}, {"国定工行"})
        generated = await self.client.post(f"{API}/finance/bank-flows/generate", params={"finance_scope": "firm"},
                                           json={"ids": [item["id"] for item in lines["items"]]})
        self.assertEqual(generated.status_code, 200, generated.text)
        async with self.sessions() as db:
            sources = {row.bank_source for row in (await db.scalars(select(IncomingPayment))).all()}
        self.assertEqual(sources, {"国定工行"})
        self.assertEqual(len(await self._receipts("gdicbc")), 2)
        self.assertEqual(await self._receipts("icbc"), [], "工行页不显示国定工行的流水")


if __name__ == "__main__":
    unittest.main()

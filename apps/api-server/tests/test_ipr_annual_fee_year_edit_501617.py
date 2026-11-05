"""501617（fwl 11-05）：专利年费“修改首年年度及减缓比例”批量处理。"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity
from sqlalchemy import select

ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "知产"}


class AnnualYearEditTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理者", department="知产", password_hash="x", role="admin", is_active=True))
            self.case = BusinessRecord(module="ipr_case", serial_no="HDPI2000001", title="专利", customer="甲", status="在办", owner="admin",
                                       department="知产", data={"case_kind": "专利", "first_annual_year": 1, "cost_slow_rate": "1.00"})
            db.add(self.case); await db.commit()
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://year.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()

    async def test_batch_edit(self):
        url = f"{settings.api_prefix}/ipr/annual-fee-monitor/annual-year"
        bad = await self.client.post(url, json={"case_ids": [self.case.id], "first_annual_year": 3, "cost_slow_rate": "0.5"})
        self.assertEqual(bad.status_code, 422)
        response = await self.client.post(url, json={"case_ids": [self.case.id], "first_annual_year": 3, "cost_slow_rate": "0.85"})
        self.assertEqual(response.json(), {"updated": 1}, response.text)
        async with self.sessions() as db:
            data = (await db.get(BusinessRecord, self.case.id)).data
            self.assertEqual((data["first_annual_year"], data["annual_fee_year"], data["cost_slow_rate"], data["rate"]), (3, 3, "0.85", "0.85"))
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case.id))).all()
            self.assertEqual(events[-1].comment, "第1年度 / 1.00 → 第3年度 / 减缓85%")
        from app.areas.ipr.annual_fee_monitor import _relief_rate
        self.assertEqual(_relief_rate(data), 0.85)


if __name__ == "__main__":
    unittest.main()

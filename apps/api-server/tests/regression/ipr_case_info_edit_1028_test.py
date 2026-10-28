"""知识产权案件页“修改/保存”（BUG20261028001，陶国南 2026-10-28 确认）：迁移案件也能改，写回案件页读取的字段并记系统日志。"""

from datetime import datetime, timezone
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.ipr import case_files, case_info
from app.config import settings
from app.database import Base, get_db
from app.models import BusinessRecord, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "ipr-info-admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
            "display_name": "IPR Info Admin", "department": "IPR"}
app = FastAPI()
app.include_router(case_info.router)
app.include_router(case_files.router)


class IprCaseInfoEditTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            now = datetime(2026, 10, 28, tzinfo=timezone.utc)
            case = BusinessRecord(
                module="ipr_case", serial_no="SHPU1810971", title="一种耐火光缆", customer="上海汉欣", status="受理",
                owner=IDENTITY["username"], department="IPR", created_at=now, updated_at=now,
                data={"case_kind": "专利", "legacy_ipr_case_id": 5386, "case_phase": "受理", "case_name": "一种耐火光缆",
                      "cost_slow_rate": "0.85", "has_relief": "T", "case_request_no": "201821235593X"},
            )
            db.add(case)
            await db.commit()
            self.case_id = case.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_legacy_case_info_can_be_saved(self):
        response = await self.client.patch(f"{API}/ipr/cases/{self.case_id}/info", json={
            "case_phase": "授权", "case_name": "一种新型耐火光缆", "authorization_date": "2019-03-31",
            "first_annual_year": 2, "cost_slow_rate": "0.70", "has_relief": True, "has_priority": True,
        })
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.case_id)
            self.assertEqual(record.title, "一种新型耐火光缆")
            self.assertEqual(record.data["case_phase"], "授权")
            self.assertEqual(record.data["authorization_date"], "2019-03-31")
            self.assertEqual((record.data["first_annual_year"], record.data["annual_fee_year"]), ("2", "2"))
            self.assertEqual((record.data["cost_slow_rate"], record.data["rate"]), ("0.70", "0.70"))
            self.assertEqual((record.data["has_relief"], record.data["has_priority"]), ("T", "T"))
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))).all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].action, "修改案件信息")
            for label in ("案件阶段", "名称", "授权日", "首年年费年度", "费用减缓比例", "优先权"):
                self.assertIn(label, events[0].comment)
            self.assertNotIn("费用减缓、", events[0].comment)
        bad = await self.client.patch(f"{API}/ipr/cases/{self.case_id}/info", json={"cost_slow_rate": "0.5"})
        self.assertEqual(bad.status_code, 422)

    async def test_phase_options_and_files_fall_back_without_legacy_tables(self):
        options = await self.client.get(f"{API}/ipr/cases/{self.case_id}/phase-options")
        self.assertEqual(options.json(), {"items": ["受理"]})
        files = await self.client.get(f"{API}/ipr/cases/{self.case_id}/files")
        self.assertEqual(files.status_code, 200, files.text)


if __name__ == "__main__":
    unittest.main()

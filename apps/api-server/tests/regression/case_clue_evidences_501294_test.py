"""501294：案件详情“线索信息”带上每条线索的证物（公证书号、状态、仓库、库位、件数）。"""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "p294-handler",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "经办人294",
    "department": "诉讼部",
}


class CaseClueEvidences501294Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department="诉讼部", role="admin", role_ids=["admin"],
                        password_hash="x", profile={}, is_active=True))
            clue = BusinessRecord(module="clue", serial_no="M294", title="店铺", customer="客户", status="已转案件", owner="sugq", department="调查部",
                                  data={"store_url": "https://v.douyin.com/x/"})
            db.add(clue)
            await db.flush()
            case = BusinessRecord(module="case", serial_no="P294-CASE", title="案件294", customer="客户", status="文书准备", owner=IDENTITY["username"],
                                  department="诉讼部", data={"case_type": "民事争议", "investigation_clue_ids": [clue.id], "investigation_clue_nos": ["M294"]})
            db.add(case)
            db.add(BusinessRecord(module="evidence", serial_no="EV294", title="证物", customer="客户", status="已出库", owner="sugq", department="调查部",
                                  data={"clue_record_id": clue.id, "clue_no": "M294", "certificate_no": "(2025)赣洪江证内字第4981号",
                                        "nc_inbound_date": "2026-01-06T13:59:11", "warehouse": "上海一仓", "storage_location_name": "4-5",
                                        "evidence_status": "已出库", "legacy_record": {"NcStatus": 20, "InvoiceNo": "3件"}}))
            await db.commit()
            self.case_id = case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: {**IDENTITY, "role": "admin", "role_ids": ["admin"]}
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://p294.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_clue_list_carries_evidences(self) -> None:
        response = await self.client.get(f"{API}/cases/{self.case_id}/clues")
        self.assertEqual(response.status_code, 200, response.text)
        evidence = response.json()["items"][0]["evidences"][0]
        self.assertEqual(evidence["certificate_no"], "(2025)赣洪江证内字第4981号")
        self.assertEqual(evidence["certificate_status"], "已入库")
        self.assertEqual(evidence["item_count"], "3件")
        self.assertEqual(evidence["warehouse_name"], "上海一仓")
        self.assertEqual(evidence["warehouse_location"], "4-5")
        self.assertEqual(evidence["evidence_status"], "已出库")


if __name__ == "__main__":
    unittest.main()

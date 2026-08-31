"""8.28 row 22: converted cases retain cause and expose their source clue."""

from __future__ import annotations

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
ADMIN = {"username": "row22-admin", "role": "admin", "display_name": "第22行管理员", "department": "调查部"}


class CaseClueConversionRelationRow22Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True))
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-828-R22-CLUE", title="第22行店铺", customer="第22行客户",
                status="已取证", owner=ADMIN["username"], department=ADMIN["department"],
                data={"shop_name": "第22行店铺", "shop_address": "上海市测试路22号", "collected_at": "2026-08-28T09:22:00", "evidence_status": "已入库"},
            )
            imported_clue = BusinessRecord(
                module="clue", serial_no="CODEX-828-R22-IMPORTED-CLUE", title="迁移线索", customer="迁移客户",
                status="已转案件", owner=ADMIN["username"], department=ADMIN["department"], data={"shop_name": "迁移店铺"},
            )
            imported_case = BusinessRecord(
                module="case", serial_no="CODEX-828-R22-IMPORTED-CASE", title="迁移案件", customer="迁移客户",
                status="等待公证书", owner=ADMIN["username"], department=ADMIN["department"], data={"clue_no": "CODEX-828-R22-IMPORTED-CLUE"},
            )
            db.add_all([clue, imported_clue, imported_case])
            await db.commit()
            self.clue_id = clue.id
            self.imported_case_id = imported_case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row22.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_conversion_preserves_cause_and_source_clue_relation(self) -> None:
        converted = await self.client.post(f"{API}/investigations/clues/batch-cases", json={
            "clue_ids": [self.clue_id], "case_type": "民事案件", "client_position": "原告",
            "cause_or_charge": "侵害商标权纠纷", "case_phase": "等待公证书",
            "handling_lawyer": ADMIN["username"], "assistant": ADMIN["username"],
        })
        self.assertEqual(converted.status_code, 201, converted.text)
        self.assertEqual(converted.json()["created"], 1)
        case_id = converted.json()["created_ids"][0]

        detail = await self.client.get(f"{API}/records/{case_id}")
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["data"]["cause_or_charge"], "侵害商标权纠纷")
        self.assertEqual(detail.json()["data"]["cause_of_action"], "侵害商标权纠纷")
        self.assertEqual(detail.json()["data"]["clue_record_id"], self.clue_id)
        self.assertEqual(detail.json()["data"]["investigation_clue_nos"], ["CODEX-828-R22-CLUE"])

        relations = await self.client.get(f"{API}/cases/{case_id}/relations")
        self.assertEqual(relations.status_code, 200, relations.text)
        self.assertEqual([item["serial_no"] for item in relations.json()["clues"]], ["CODEX-828-R22-CLUE"])
        self.assertEqual(relations.json()["clues"][0]["data"]["shop_address"], "上海市测试路22号")

    async def test_migrated_case_with_only_clue_number_still_resolves_relation(self) -> None:
        relations = await self.client.get(f"{API}/cases/{self.imported_case_id}/relations")
        self.assertEqual(relations.status_code, 200, relations.text)
        self.assertEqual([item["serial_no"] for item in relations.json()["clues"]], ["CODEX-828-R22-IMPORTED-CLUE"])


if __name__ == "__main__":
    unittest.main()

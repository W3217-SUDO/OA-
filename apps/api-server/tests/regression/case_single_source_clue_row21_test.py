"""9.1 row 21: a case generated from one clue exposes only that source clue."""

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
ADMIN = {"username": "row21-admin", "role": "admin", "display_name": "第21行管理员", "department": "调查部"}


class CaseSingleSourceClueRow21Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=ADMIN["username"], display_name=ADMIN["display_name"],
                department=ADMIN["department"], role="admin", password_hash="x", is_active=True,
            ))
            selected = BusinessRecord(
                module="clue", serial_no="M26085930", title="选中的已取证线索", customer="第21行客户",
                status="已转案件", owner=ADMIN["username"], department=ADMIN["department"], data={},
            )
            unrelated = BusinessRecord(
                module="clue", serial_no="M26085841", title="同客户的其他线索", customer="第21行客户",
                status="已转案件", owner=ADMIN["username"], department=ADMIN["department"], data={},
            )
            db.add_all([selected, unrelated])
            await db.flush()
            case_record = BusinessRecord(
                module="case", serial_no="SHMS2600438", title="第21行案件", customer="第21行客户",
                status="等待公证书", owner=ADMIN["username"], department=ADMIN["department"],
                data={
                    "clue_id": selected.id,
                    "clue_record_id": selected.id,
                    "investigation_clue_id": selected.id,
                    "investigation_clue_ids": [selected.id],
                    "clue_no": selected.serial_no,
                    "investigation_clue_nos": [selected.serial_no],
                },
            )
            db.add(case_record)
            await db.flush()
            # Simulate the stale reverse link that previously polluted the case relation list.
            unrelated.data = {"case_id": case_record.id, "case_no": case_record.serial_no}
            await db.commit()
            self.case_id = case_record.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row21.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_explicit_source_id_excludes_stale_reverse_link(self) -> None:
        response = await self.client.get(f"{API}/cases/{self.case_id}/relations")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["serial_no"] for item in response.json()["clues"]], ["M26085930"])
        self.assertEqual(response.json()["clue_total"], 1)


if __name__ == "__main__":
    unittest.main()

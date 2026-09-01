"""9.1 row 22: every personal clue queue is private even for administrators."""

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
ADMIN = {"username": "admin", "role": "admin", "display_name": "管理员", "department": "调查部"}


class InvestigationMyClueScopeRow22Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", department="调查部", role="admin", password_hash="x", is_active=True),
                User(username="other", display_name="其他调查员", department="调查部", role="user", password_hash="x", is_active=True),
            ])
            for status in ("草稿", "已取证"):
                db.add_all([
                    BusinessRecord(module="clue", serial_no=f"MINE-{status}", title="本人线索", customer="客户", status=status, owner="admin", department="调查部"),
                    BusinessRecord(module="clue", serial_no=f"OTHER-{status}", title="他人线索", customer="客户", status=status, owner="other", department="调查部"),
                ])
            db.add_all([
                BusinessRecord(module="clue", serial_no="MINE-NO-FEE", title="本人未申请费用", customer="客户", status="已取证", owner="admin", department="调查部", data={}),
                BusinessRecord(module="clue", serial_no="OTHER-NO-FEE", title="他人未申请费用", customer="客户", status="已取证", owner="other", department="调查部", data={}),
            ])
            await db.commit()
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

    async def _serials(self, statuses: str) -> list[str]:
        response = await self.client.get(f"{API}/records", params={
            "module": "clue", "scope": "mine", "statuses": statuses, "page_size": 100,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return [item["serial_no"] for item in response.json()["items"]]

    async def test_admin_personal_draft_queue_excludes_other_investigators(self) -> None:
        self.assertEqual(await self._serials("草稿"), ["MINE-草稿"])

    async def test_admin_personal_collected_queue_excludes_other_investigators(self) -> None:
        serials = await self._serials("已取证")
        self.assertEqual(set(serials), {"MINE-已取证", "MINE-NO-FEE"})
        self.assertNotIn("OTHER-NO-FEE", serials)


if __name__ == "__main__":
    unittest.main()

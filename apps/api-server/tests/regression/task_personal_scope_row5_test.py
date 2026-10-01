"""8.14 row 5: personal task pages stay personal for administrators too."""

from __future__ import annotations

from datetime import date, timedelta
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
ADMIN = {"username": "row5-admin", "role": "admin", "display_name": "Row 5 Admin", "department": "事务部"}


class TaskPersonalScopeRow5Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="row5-admin", display_name="Row 5 Admin", department="事务部", role="admin", password_hash="x", is_active=True),
                User(username="row5-other", display_name="Row 5 Other", department="事务部", role="user", password_hash="x", is_active=True),
                BusinessRecord(module="task", serial_no="CODEX-814-R5-MINE", title="Mine", customer="", status="待接收", owner="row5-admin", department="事务部", data={"deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "人工", "initiator": "row5-admin", "collaborators": []}),
                BusinessRecord(module="task", serial_no="CODEX-814-R5-OTHER", title="Other", customer="", status="待接收", owner="row5-other", department="事务部", data={"deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "自动", "initiator": "row5-other", "collaborators": []}),
            ])
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row5.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_administrator_personal_and_company_ranges_are_distinct(self) -> None:
        personal = await self.client.get(f"{API}/tasks", params={"scope": "mine", "relation": "initiated"})
        self.assertEqual(personal.status_code, 200, personal.text)
        self.assertEqual([item["serial_no"] for item in personal.json()["items"]], ["CODEX-814-R5-MINE"])

        company = await self.client.get(f"{API}/tasks", params={"scope": "company", "relation": "initiated"})
        self.assertEqual(company.status_code, 200, company.text)
        self.assertEqual({item["serial_no"] for item in company.json()["items"]}, {"CODEX-814-R5-MINE", "CODEX-814-R5-OTHER"})


if __name__ == "__main__":
    unittest.main()

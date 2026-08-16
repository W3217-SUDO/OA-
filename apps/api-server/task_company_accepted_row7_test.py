"""8.14 row 7: company accepted tasks include other employees' assignments."""

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
VIEWER = {
    "username": "row7-viewer", "role": "user", "display_name": "Row 7 Viewer",
    "department": "诉讼一部",
}


class TaskCompanyAcceptedRow7Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="row7-viewer", display_name="Row 7 Viewer", department="诉讼一部", role="user", password_hash="x", is_active=True),
                User(username="row7-owner", display_name="Row 7 Owner", department="调查部", role="user", password_hash="x", is_active=True),
            ])
            db.add(BusinessRecord(
                module="task", serial_no="CODEX-814-R7-TASK", title="Accepted company task",
                customer="", status="待接收", owner="row7-owner", department="调查部",
                data={
                    "deadline": str(date.today() + timedelta(days=7)), "priority": "普通",
                    "source": "案件任务", "initiator": "row7-owner", "collaborators": [],
                },
            ))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: VIEWER
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row7.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_company_accepted_tasks_include_another_owner(self) -> None:
        response = await self.client.get(f"{API}/tasks", params={
            "scope": "company", "relation": "owned", "serial_no": "CODEX-814-R7-TASK",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["owner"], "row7-owner")


if __name__ == "__main__":
    unittest.main()

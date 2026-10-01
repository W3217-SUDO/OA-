"""8.14 row 8: company collaboration lists every collaborative task only."""

from __future__ import annotations

from datetime import date, timedelta
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, User
from app.security import current_identity


API = settings.api_prefix
VIEWER = {
    "username": "row8-viewer", "role": "user", "display_name": "Row 8 Viewer",
    "department": "诉讼一部",
}


class TaskCompanyCollaboratingRow8Test(unittest.IsolatedAsyncioTestCase):
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
                User(username="row8-viewer", display_name="Row 8 Viewer", department="诉讼一部", role="user", password_hash="x", is_active=True),
                User(username="row8-owner", display_name="Row 8 Owner", department="诉讼二部", role="user", password_hash="x", is_active=True),
                User(username="row8-collaborator", display_name="Row 8 Collaborator", department="调查部", role="user", password_hash="x", is_active=True),
                RolePermission(role="user", display_name="Company task reader", data_scope="全所数据", menu_keys=["task-company"], field_keys=[]),
            ])
            base_data = {
                "deadline": str(date.today() + timedelta(days=7)), "priority": "普通",
                "source": "案件任务", "initiator": "row8-owner",
            }
            db.add_all([
                BusinessRecord(
                    module="task", serial_no="CODEX-814-R8-COLLAB", title="Company collaboration",
                    customer="", status="待接收", owner="row8-owner", department="诉讼二部",
                    data={**base_data, "collaborators": ["row8-collaborator"]},
                ),
                BusinessRecord(
                    module="task", serial_no="CODEX-814-R8-PLAIN", title="No collaborator",
                    customer="", status="待接收", owner="row8-owner", department="诉讼二部",
                    data={**base_data, "collaborators": []},
                ),
            ])
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: VIEWER
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row8.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_company_collaboration_is_global_but_excludes_plain_tasks(self) -> None:
        personal = await self.client.get(f"{API}/tasks", params={
            "scope": "mine", "relation": "collaborating", "serial_no": "CODEX-814-R8-COLLAB",
        })
        self.assertEqual(personal.status_code, 200, personal.text)
        self.assertEqual(personal.json()["total"], 0)

        company = await self.client.get(f"{API}/tasks", params={
            "scope": "company", "relation": "collaborating", "serial_no": "CODEX-814-R8",
        })
        self.assertEqual(company.status_code, 200, company.text)
        self.assertEqual(company.json()["total"], 1)
        self.assertEqual(company.json()["items"][0]["serial_no"], "CODEX-814-R8-COLLAB")


if __name__ == "__main__":
    unittest.main()

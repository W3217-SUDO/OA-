"""8.14 row 9: every employee can read relation-specific department tasks."""

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
    "username": "row9-viewer", "role": "user", "display_name": "Row 9 Viewer",
    "department": "品牌一部",
}


class TaskDepartmentScopeRow9Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            users = [
                ("row9-viewer", "品牌一部"), ("row9-peer", "品牌一部"),
                ("row9-other", "品牌二部"),
            ]
            db.add_all([
                User(username=name, display_name=name, department=department, role="user", password_hash="x", is_active=True)
                for name, department in users
            ])
            base = {"deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "案件任务"}
            db.add_all([
                BusinessRecord(module="task", serial_no="CODEX-814-R9-INIT", title="Department initiated", customer="", status="待接收", owner="row9-other", department="品牌一部", data={**base, "initiator": "row9-peer", "collaborators": []}),
                BusinessRecord(module="task", serial_no="CODEX-814-R9-OWN", title="Department accepted", customer="", status="待接收", owner="row9-peer", department="品牌二部", data={**base, "initiator": "row9-other", "collaborators": []}),
                BusinessRecord(module="task", serial_no="CODEX-814-R9-COLLAB", title="Department collaborating", customer="", status="待接收", owner="row9-other", department="品牌二部", data={**base, "initiator": "row9-other", "collaborators": ["row9-peer"]}),
                BusinessRecord(module="task", serial_no="CODEX-814-R9-HIDDEN", title="Other department", customer="", status="待接收", owner="row9-other", department="品牌二部", data={**base, "initiator": "row9-other", "collaborators": []}),
            ])
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: VIEWER
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row9.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_department_relation_matrix_for_ordinary_employee(self) -> None:
        expected = {
            "initiated": "CODEX-814-R9-INIT",
            "owned": "CODEX-814-R9-OWN",
            "collaborating": "CODEX-814-R9-COLLAB",
        }
        for relation, serial_no in expected.items():
            response = await self.client.get(f"{API}/tasks", params={
                "scope": "department", "relation": relation, "serial_no": "CODEX-814-R9",
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([item["serial_no"] for item in response.json()["items"]], [serial_no])


if __name__ == "__main__":
    unittest.main()

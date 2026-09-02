"""9.1 row 11: manually published task numbers stay compact."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import _next_manual_task_serial, app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row11-admin", "role": "admin", "display_name": "Row 11 Admin", "department": "诉讼部"}


class TaskSerialNumberRow11Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"],
                role="admin", password_hash="x", is_active=True,
            ))
            db.add(BusinessRecord(
                module="task", serial_no="RW20260901134253891085", title="历史长编号任务", customer="历史客户",
                status="进行中", owner=ADMIN["username"], department=ADMIN["department"], data={"source": "案件任务"},
            ))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row11.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def _create_task(self, title: str) -> dict:
        response = await self.client.post(f"{API}/tasks", json={
            "title": title, "customer": "Row 11 Customer", "owner": ADMIN["username"], "collaborators": [],
            "deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "日常任务",
            "description": "9.1 row 11 focused test",
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_new_numbers_match_legacy_shape_and_history_is_unchanged(self) -> None:
        before_prefix = datetime.now().strftime("%H%M%S")
        with patch("app.main.secrets.randbelow", side_effect=[25191, 69344]):
            first = await self._create_task("第一条短编号任务")
            second = await self._create_task("第二条短编号任务")
        after_prefix = datetime.now().strftime("%H%M%S")

        self.assertRegex(first["serial_no"], r"^\d{11}$")
        self.assertRegex(second["serial_no"], r"^\d{11}$")
        self.assertIn(first["serial_no"][:6], {before_prefix, after_prefix})
        self.assertIn(second["serial_no"][:6], {before_prefix, after_prefix})
        self.assertEqual(first["serial_no"][-5:], "25191")
        self.assertEqual(second["serial_no"][-5:], "69344")
        self.assertNotEqual(first["serial_no"], second["serial_no"])

        historical = await self.client.get(f"{API}/tasks", params={"serial_no": "RW20260901134253891085"})
        self.assertEqual(historical.status_code, 200, historical.text)
        self.assertEqual(historical.json()["items"][0]["serial_no"], "RW20260901134253891085")

    async def test_collision_retries_and_exhaustion_fails_without_writing(self) -> None:
        fixed_now = datetime(2026, 9, 2, 14, 6, 52)
        async with self.sessions() as db:
            db.add(BusinessRecord(
                module="task", serial_no="14065225191", title="旧系统形态占用号", customer="",
                status="进行中", owner=ADMIN["username"], department=ADMIN["department"], data={},
            ))
            await db.commit()
            with patch("app.main.secrets.randbelow", side_effect=[25191, 69344]):
                self.assertEqual(await _next_manual_task_serial(db, now=fixed_now), "14065269344")
            with patch("app.main.secrets.randbelow", return_value=25191):
                with self.assertRaises(HTTPException) as rejected:
                    await _next_manual_task_serial(db, now=fixed_now)
            self.assertEqual(rejected.exception.status_code, 503)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord)), 2)


if __name__ == "__main__":
    unittest.main()

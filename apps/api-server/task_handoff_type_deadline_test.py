"""Isolated SQLite contract tests for evidenced legacy handoff deadlines."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
OWNER = {"username": "CODEX-handoff-owner", "role": "staff", "display_name": "交接发起人", "department": "事务部"}
RECIPIENT = {"username": "CODEX-handoff-recipient", "role": "staff", "display_name": "交接接收人", "department": "事务部"}


class TaskHandoffTypeDeadlineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for identity in (OWNER, RECIPIENT):
                db.add(User(username=identity["username"], display_name=identity["display_name"], department=identity["department"], role=identity["role"], password_hash="x", is_active=True))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: OWNER
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://task-handoff-type.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def create_task(self, suffix: str, data: dict) -> int:
        async with self.sessions() as db:
            task = BusinessRecord(module="task", serial_no=f"CODEX-HANDOFF-{suffix}", title="期限交接测试", customer="", status="处理中", owner=OWNER["username"], department="事务部", data={"deadline": "2099-01-01", **data})
            db.add(task)
            await db.commit()
            return task.id

    async def handoff(self, task_id: int, **payload: str) -> httpx.Response:
        return await self.client.post(f"{API}/tasks/{task_id}/handoff", json={"recipient": RECIPIENT["username"], "comment": "CODEX isolated test", **payload})

    async def persisted_data(self, task_id: int) -> dict:
        async with self.sessions() as db:
            task = await db.get(BusinessRecord, task_id)
            return task.data or {}

    async def test_legacy_type_clamps_requested_end_at_and_keeps_five_day_auto_complete(self) -> None:
        task_id = await self.create_task("known", {"legacy_task_type_id": 101023})
        before = datetime.now()
        response = await self.handoff(task_id, end_at=(before + timedelta(days=90)).isoformat(timespec="seconds"))
        after = datetime.now()
        self.assertEqual(response.status_code, 200, response.text)
        data = await self.persisted_data(task_id)
        actual_end_at = datetime.fromisoformat(data["end_at"])
        self.assertLessEqual(actual_end_at, before + timedelta(days=15, seconds=1))
        self.assertGreaterEqual(actual_end_at, after + timedelta(days=15, seconds=-1))
        self.assertEqual(data["deadline"], actual_end_at.date().isoformat())
        self.assertEqual(response.json()["end_at"], data["end_at"])
        self.assertEqual(data["handoff_limit_days"], 15)
        self.assertEqual(data["handoff_auto_complete_at"], str(before.date() + timedelta(days=5)))

    async def test_old_type_alias_and_auto_task_type_resolve_without_using_gap_days(self) -> None:
        alias_task = await self.create_task("alias", {"TaskTypeId": 1001001})
        auto_task = await self.create_task("auto", {"auto_task_type": "document_preparation_stage"})
        requested = (datetime.now() + timedelta(days=500)).isoformat(timespec="seconds")
        self.assertEqual((await self.handoff(alias_task, end_at=requested)).status_code, 200)
        self.assertEqual((await self.handoff(auto_task, end_at=requested)).status_code, 200)
        self.assertEqual((datetime.fromisoformat((await self.persisted_data(alias_task))["end_at"]) - datetime.now()).days, 364)
        self.assertEqual((datetime.fromisoformat((await self.persisted_data(auto_task))["end_at"]) - datetime.now()).days, 29)

    async def test_parameter_projection_overrides_verified_type_only(self) -> None:
        async with self.sessions() as db:
            db.add(SystemParameter(category="legacy_task_type", code="101023", name="旧和解任务", extra={"skip_days": 8}, is_active=True))
            await db.commit()
        task_id = await self.create_task("configured", {"legacy_task_type_id": 101023})
        response = await self.handoff(task_id, end_at=(datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((datetime.fromisoformat((await self.persisted_data(task_id))["end_at"]) - datetime.now()).days, 7)

    async def test_legacy_whole_day_limit_boundary_is_not_a_strict_instant_minimum(self) -> None:
        frozen_now = datetime(2032, 1, 2, 9, 30, 0)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen_now if tz is None else frozen_now.replace(tzinfo=tz)

        within_one_day = frozen_now + timedelta(days=15, hours=12)
        at_one_whole_day = frozen_now + timedelta(days=16)
        within_task = await self.create_task("whole-day-within", {"legacy_task_type_id": 101023, "start_at": (frozen_now - timedelta(days=1)).isoformat(timespec="seconds")})
        beyond_task = await self.create_task("whole-day-beyond", {"legacy_task_type_id": 101023, "start_at": (frozen_now - timedelta(days=1)).isoformat(timespec="seconds")})

        with patch("app.areas.tp.router.datetime", FrozenDateTime):
            self.assertEqual((await self.handoff(within_task, end_at=within_one_day.isoformat(timespec="seconds"))).status_code, 200)
            self.assertEqual((await self.handoff(beyond_task, end_at=at_one_whole_day.isoformat(timespec="seconds"))).status_code, 200)

        self.assertEqual((await self.persisted_data(within_task))["end_at"], within_one_day.isoformat(timespec="seconds"))
        self.assertEqual((await self.persisted_data(beyond_task))["end_at"], (frozen_now + timedelta(days=15)).isoformat(timespec="seconds"))

    async def test_generic_or_unknown_parameter_cannot_override_a_legacy_type(self) -> None:
        async with self.sessions() as db:
            db.add_all([
                SystemParameter(category="task_type", code="101023", name="泛用类型", extra={"skip_days": 1}, is_active=True),
                SystemParameter(category="legacy_task_type", code="999999", name="未知旧类型", extra={"skip_days": 1, "legacy_task_type_id": 101023}, is_active=True),
            ])
            await db.commit()
        task_id = await self.create_task("no-config-collision", {"legacy_task_type_id": 101023})
        response = await self.handoff(task_id, end_at=(datetime.now() + timedelta(days=30)).isoformat(timespec="seconds"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_data(task_id))["handoff_limit_days"], 15)

    async def test_unknown_type_and_legacy_payload_do_not_receive_a_static_default(self) -> None:
        unknown_task = await self.create_task("unknown", {"auto_task_type": "unverified_scheduler_job", "legacy_task_type_id": 999999})
        requested = (datetime.now() + timedelta(days=90)).isoformat(timespec="seconds")
        response = await self.handoff(unknown_task, end_at=requested)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_data(unknown_task))["end_at"], requested)

        legacy_task = await self.create_task("legacy-payload", {"legacy_task_type_id": 101023, "deadline": "2030-01-01"})
        response = await self.handoff(legacy_task)
        self.assertEqual(response.status_code, 200, response.text)
        data = await self.persisted_data(legacy_task)
        self.assertEqual(data["handoff_limit_days"], 15)
        self.assertLessEqual(datetime.fromisoformat(data["end_at"]), datetime.now() + timedelta(days=15, seconds=1))

    async def test_rejects_end_at_at_or_before_task_start(self) -> None:
        start_at = datetime.now() + timedelta(days=10)
        task_id = await self.create_task("invalid-range", {"legacy_task_type_id": 101023, "start_at": start_at.isoformat(timespec="seconds")})
        response = await self.handoff(task_id, end_at=(start_at - timedelta(minutes=1)).isoformat(timespec="seconds"))
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("开始时间", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()

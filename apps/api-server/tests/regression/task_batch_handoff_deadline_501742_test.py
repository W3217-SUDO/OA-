"""501742：批量交接可填期限，选填；规则同单条转交。"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
OWNER = {"username": "h742-owner", "role": "admin", "display_name": "负责人", "department": "事务部"}


class BatchHandoffDeadlineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for name in ("h742-owner", "h742-recipient"):
                db.add(User(username=name, display_name=name, department="事务部", role="admin", password_hash="x", is_active=True))
            await db.commit()
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.db
        app.dependency_overrides[current_identity] = lambda: OWNER
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def db(self):
        async with self.sessions() as session:
            yield session

    async def task(self, suffix: str, **data) -> int:
        async with self.sessions() as db:
            row = BusinessRecord(module="task", serial_no=f"T742-{suffix}", title=f"任务{suffix}", status="处理中", owner="h742-owner",
                                 department="事务部", customer="", description="", data={"initiator": "h742-owner", **data})
            db.add(row)
            await db.commit()
            return row.id

    async def batch(self, ids: list[int], **extra):
        return await self.client.post(f"{API}/tasks/batch-lifecycle", json={"task_ids": ids, "action": "handoff", "recipient": "h742-recipient", **extra})

    async def data_of(self, task_id: int) -> tuple[str, dict]:
        async with self.sessions() as db:
            row = await db.get(BusinessRecord, task_id)
            return row.owner, row.data

    async def test_no_deadline_keeps_original_even_when_overdue(self):
        past = (datetime.now() - timedelta(days=9)).isoformat(timespec="seconds")
        far = (datetime.now() + timedelta(days=300)).isoformat(timespec="seconds")
        first, second = await self.task("a", end_at=past, deadline=past[:10]), await self.task("b", end_at=far, task_type_id=101002)
        response = await self.batch([first, second])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["deadline_limited"], [])
        owner, data = await self.data_of(first)
        self.assertEqual((owner, data["end_at"]), ("h742-recipient", past))  # 已过期也能转，原期限不变
        self.assertEqual((await self.data_of(second))[1]["end_at"], far)  # 不填时不按类型上限改

    async def test_same_deadline_applied_to_all_and_recorded(self):
        ids = [await self.task("c", end_at="2026-01-01T00:00:00", deadline="2026-01-01"), await self.task("d")]
        target = (datetime.now() + timedelta(days=5)).replace(microsecond=0)
        response = await self.batch(ids, end_at=target.isoformat())
        self.assertEqual(response.status_code, 200, response.text)
        for task_id in ids:
            data = (await self.data_of(task_id))[1]
            self.assertEqual((data["end_at"], data["deadline"]), (target.isoformat(), str(target.date())))
        async with self.sessions() as db:
            comments = (await db.scalars(select(WorkflowEvent.comment).where(WorkflowEvent.action == "批量任务交接"))).all()
        self.assertTrue(all("交接结束时间" in comment for comment in comments), comments)

    async def test_task_type_limit_shortens_and_is_reported(self):
        limited, free = await self.task("e", task_type_id=101002), await self.task("f")
        target = (datetime.now() + timedelta(days=200)).replace(microsecond=0)
        response = await self.batch([limited, free], end_at=target.isoformat())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["serial_no"] for item in response.json()["deadline_limited"]], ["T742-e"])
        self.assertLess((await self.data_of(limited))[1]["end_at"], target.isoformat())
        self.assertEqual((await self.data_of(free))[1]["end_at"], target.isoformat())

    async def test_invalid_deadline_rejects_whole_batch(self):
        good = await self.task("g")
        late_start = (datetime.now() + timedelta(days=20)).isoformat(timespec="seconds")
        bad = await self.task("h", start_at=late_start)
        response = await self.batch([good, bad], end_at=(datetime.now() + timedelta(days=5)).isoformat(timespec="seconds"))
        self.assertEqual(response.status_code, 422)
        self.assertIn("T742-h", response.json()["detail"])
        self.assertEqual((await self.data_of(good))[0], "h742-owner")  # 整批不动
        past = await self.batch([good], end_at=(datetime.now() - timedelta(days=1)).isoformat(timespec="seconds"))
        self.assertEqual(past.status_code, 422)

    async def test_single_handoff_rule_unchanged(self):
        task_id = await self.task("i", task_type_id=101002)
        target = (datetime.now() + timedelta(days=200)).replace(microsecond=0)
        response = await self.client.post(f"{API}/tasks/{task_id}/handoff", json={"recipient": "h742-recipient", "end_at": target.isoformat()})
        self.assertEqual(response.status_code, 200, response.text)
        data = (await self.data_of(task_id))[1]
        self.assertLess(data["end_at"], target.isoformat())
        self.assertEqual(data["handoff_limit_days"], 30)


if __name__ == "__main__":
    unittest.main()

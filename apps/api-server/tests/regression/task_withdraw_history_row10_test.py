"""8.14 row 10: task withdrawal remains visible in the full task history."""

from __future__ import annotations

import unittest

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
INITIATOR = {
    "username": "row10-initiator",
    "role": "user",
    "display_name": "Row 10 Initiator",
    "department": "Brand Department",
}


class TaskWithdrawHistoryRow10Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(
                    username="row10-initiator",
                    display_name="Row 10 Initiator",
                    department="Brand Department",
                    role="user",
                    password_hash="x",
                    is_active=True,
                ),
                User(
                    username="row10-owner",
                    display_name="Row 10 Owner",
                    department="Brand Department",
                    role="user",
                    password_hash="x",
                    is_active=True,
                ),
            ])
            task = BusinessRecord(
                module="task",
                serial_no="CODEX-814-R10-TASK",
                title="Withdraw with history",
                customer="",
                status="处理中",
                owner="row10-owner",
                department="Brand Department",
                data={"initiator": "row10-initiator", "collaborators": []},
            )
            db.add(task)
            await db.flush()
            db.add_all([
                WorkflowEvent(
                    record_id=task.id,
                    action="创建任务",
                    from_status="",
                    to_status="待接收",
                    operator="row10-initiator",
                    comment="Created",
                ),
                WorkflowEvent(
                    record_id=task.id,
                    action="接受任务",
                    from_status="待接收",
                    to_status="处理中",
                    operator="row10-owner",
                    comment="Accepted",
                ),
                WorkflowEvent(
                    record_id=task.id,
                    action="任务沟通",
                    from_status="处理中",
                    to_status="处理中",
                    operator="row10-initiator",
                    comment="Persistent progress note",
                ),
            ])
            await db.commit()
            self.task_id = task.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: INITIATOR
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row10.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_withdraw_appends_event_without_losing_prior_history(self) -> None:
        response = await self.client.post(
            f"{API}/tasks/{self.task_id}/withdraw",
            json={"comment": "Initiator withdrew the task"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "已撤回")

        async with self.sessions() as db:
            events = (await db.execute(
                select(WorkflowEvent)
                .where(WorkflowEvent.record_id == self.task_id)
                .order_by(WorkflowEvent.id)
            )).scalars().all()
        self.assertEqual(
            [event.action for event in events],
            ["创建任务", "接受任务", "任务沟通", "撤回任务"],
        )
        self.assertEqual(events[-1].from_status, "处理中")
        self.assertEqual(events[-1].to_status, "已撤回")
        self.assertEqual(events[-1].comment, "Initiator withdrew the task")


if __name__ == "__main__":
    unittest.main()

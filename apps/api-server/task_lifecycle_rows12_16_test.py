"""9.2 rows 12-16: legacy task action/state parity."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import _ensure_case_fixed_tasks, app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
INITIATOR = {"username": "row12-initiator", "role": "staff", "display_name": "发起人", "department": "事务部"}
OWNER = {"username": "row15-owner", "role": "staff", "display_name": "负责人", "department": "事务部"}
RECIPIENT = {"username": "row15-recipient", "role": "staff", "display_name": "接收人", "department": "事务部"}


class TaskLifecycleRows12To16Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for identity in (INITIATOR, OWNER, RECIPIENT):
                db.add(User(
                    username=identity["username"], display_name=identity["display_name"],
                    department=identity["department"], role=identity["role"], password_hash="x", is_active=True,
                ))
            await db.commit()
        self.identity = dict(INITIATOR)
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://rows12-16.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def create_task(self, status: str, suffix: str) -> int:
        async with self.sessions() as db:
            task = BusinessRecord(
                module="task", serial_no=f"903{suffix}", title=f"9.2-{suffix}", customer="",
                status=status, owner=OWNER["username"], department="事务部",
                data={"initiator": INITIATOR["username"], "source": "日常任务", "rejected_reason": "缺少材料"},
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            return task.id

    async def persisted_task(self, task_id: int) -> BusinessRecord:
        async with self.sessions() as db:
            return await db.get(BusinessRecord, task_id)

    async def test_initiator_can_restart_or_confirm_rejected_and_completed_tasks(self) -> None:
        rejected_restart = await self.create_task("已拒绝", "1201")
        response = await self.client.post(f"{API}/tasks/{rejected_restart}/restart", json={"comment": "补齐材料后重启"})
        self.assertEqual(response.status_code, 200, response.text)
        restarted = await self.persisted_task(rejected_restart)
        self.assertEqual(restarted.status, "处理中")
        self.assertEqual((restarted.data or {}).get("rejected_reason"), "")

        rejected_confirm = await self.create_task("已拒绝", "1301")
        response = await self.client.post(f"{API}/tasks/{rejected_confirm}/confirm", json={"comment": "不再继续，确认完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(rejected_confirm)).status, "已验收")

        completed_restart = await self.create_task("已完成", "1202")
        response = await self.client.post(f"{API}/tasks/{completed_restart}/restart", json={"comment": "验收不通过"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(completed_restart)).status, "处理中")

        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id.in_([rejected_restart, rejected_confirm, completed_restart])
            ))).all())
        self.assertEqual({event.action for event in events}, {"重新开始任务", "验收任务"})

    async def test_recipient_can_complete_or_handoff_pending_and_processing_tasks(self) -> None:
        self.identity = dict(OWNER)
        pending_complete = await self.create_task("待处理", "1501")
        response = await self.client.post(f"{API}/tasks/{pending_complete}/complete", json={"comment": "直接完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(pending_complete)).status, "已完成")

        pending_handoff = await self.create_task("待接收", "1502")
        response = await self.client.post(f"{API}/tasks/{pending_handoff}/handoff", json={
            "recipient": RECIPIENT["username"], "comment": "转交处理",
        })
        self.assertEqual(response.status_code, 200, response.text)
        handed = await self.persisted_task(pending_handoff)
        self.assertEqual((handed.owner, handed.status), (RECIPIENT["username"], "待接收"))

        processing_complete = await self.create_task("进行中", "1601")
        response = await self.client.post(f"{API}/tasks/{processing_complete}/complete", json={"comment": "处理完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(processing_complete)).status, "已完成")

    async def test_ended_tasks_reject_recipient_actions(self) -> None:
        self.identity = dict(OWNER)
        stopped = await self.create_task("已停止", "1602")
        accepted = await self.client.post(f"{API}/tasks/{stopped}/accept", json={"comment": "不应接收"})
        completed = await self.client.post(f"{API}/tasks/{stopped}/complete", json={"comment": "不应完成"})
        handed = await self.client.post(f"{API}/tasks/{stopped}/handoff", json={
            "recipient": RECIPIENT["username"], "comment": "不应转交",
        })
        self.assertEqual((accepted.status_code, completed.status_code, handed.status_code), (409, 409, 409))
        self.assertEqual((await self.persisted_task(stopped)).status, "已停止")

    async def test_batch_complete_and_confirm_match_single_task_state_machine(self) -> None:
        self.identity = dict(OWNER)
        pending = await self.create_task("待处理", "1503")
        response = await self.client.post(f"{API}/tasks/batch-lifecycle", json={
            "task_ids": [pending], "action": "complete", "comment": "批量完成",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(pending)).status, "已完成")

        rejected = await self.create_task("已拒绝", "1302")
        self.identity = dict(INITIATOR)
        response = await self.client.post(f"{API}/tasks/batch-lifecycle", json={
            "task_ids": [rejected], "action": "confirm", "comment": "批量确认",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(rejected)).status, "已验收")

    async def test_automatic_fixed_tasks_also_use_legacy_compact_numbers(self) -> None:
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CASE-903", title="测试案件", customer="测试客户", status="文书准备",
                owner=OWNER["username"], department="事务部", data={},
            )
            db.add(case)
            await db.flush()
            with patch("app.main.secrets.randbelow", side_effect=[12345, 67890]):
                tasks = await _ensure_case_fixed_tasks(case, db, operator=INITIATOR["username"])
            await db.commit()
            self.assertEqual(len(tasks), 2)
            self.assertTrue(all(len(task.serial_no) == 11 and task.serial_no.isdigit() for task in tasks))


if __name__ == "__main__":
    unittest.main()

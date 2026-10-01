from __future__ import annotations

from datetime import date
import unittest

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.tasks import _add_calendar_months, _ensure_execution_application_reminder_task
from app.database import Base
from app.models import BusinessRecord, Notification, User, WorkflowEvent


class CaseExecutionApplicationAutoTaskTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_first_pending_execution_creates_one_assistant_owned_two_month_task(self) -> None:
        async with self.sessions() as db:
            db.add_all([
                User(username="lawyer", display_name="经办律师甲", department="诉讼部", role="user", password_hash="x", is_active=True),
                User(username="assistant", display_name="律师助理乙", department="律师助理部", role="user", password_hash="x", is_active=True),
            ])
            case = BusinessRecord(
                module="case", serial_no="CASE-AUTO-001", title="自动任务案件", customer="测试客户",
                status="一审待执行", owner="manager", department="诉讼部",
                data={
                    "handling_lawyers": ["经办律师甲"],
                    "handling_lawyer_usernames": ["lawyer"],
                    "assistants": ["律师助理乙"],
                    "assistant_usernames": ["assistant"],
                    "assistant": "律师助理乙",
                    "assistant_username": "assistant",
                },
            )
            db.add(case)
            await db.flush()

            task = await _ensure_execution_application_reminder_task(
                case, db, previous_status="一审判决结案", operator="phase-editor", today=date(2026, 5, 8),
            )
            await db.commit()

            self.assertIsNotNone(task)
            self.assertEqual(task.title, "执行申请-提醒任务")
            self.assertEqual(task.owner, "assistant")
            self.assertEqual(task.status, "待接收")
            self.assertEqual(task.department, "律师助理部")
            self.assertEqual(task.description, "本案CASE-AUTO-001判决书或调解书已生效,请尽快提交申请执行材料,并上传")
            self.assertEqual(task.data["deadline"], "2026-07-08")
            self.assertEqual(task.data["initiator"], "lawyer")
            self.assertEqual(task.data["collaborators"], [])
            self.assertEqual(task.data["auto_task_type"], "execution_application_reminder")
            self.assertEqual(case.data["execution_application_reminder_task_id"], task.id)

            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
            self.assertIn("经办律师甲新建任务给负责人(律师助理乙)", event.comment)
            self.assertIn("协作人(无)", event.comment)
            self.assertIn(task.description, event.comment)
            notice = await db.scalar(select(Notification).where(Notification.source_id == task.id))
            self.assertEqual(notice.recipient, "assistant")

            duplicate = await _ensure_execution_application_reminder_task(
                case, db, previous_status="一审判决结案", operator="phase-editor", today=date(2026, 5, 8),
            )
            await db.commit()
            self.assertEqual(duplicate.id, task.id)
            count = await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == "task",
                BusinessRecord.data["auto_task_type"].as_string() == "execution_application_reminder",
            ))
            self.assertEqual(count, 1)

    async def test_missing_active_assistant_blocks_orphan_task(self) -> None:
        async with self.sessions() as db:
            db.add(User(username="lawyer", display_name="经办律师甲", department="诉讼部", role="user", password_hash="x", is_active=True))
            case = BusinessRecord(
                module="case", serial_no="CASE-AUTO-002", title="缺少助理", customer="测试客户",
                status="一审待执行", owner="manager", department="诉讼部",
                data={"handling_lawyer_usernames": ["lawyer"]},
            )
            db.add(case)
            await db.flush()
            with self.assertRaisesRegex(Exception, "案件未设置有效律师助理"):
                await _ensure_execution_application_reminder_task(
                    case, db, previous_status="一审判决结案", operator="phase-editor",
                )

    def test_calendar_month_deadline_clamps_month_end(self) -> None:
        self.assertEqual(_add_calendar_months(date(2026, 12, 31), 2), date(2027, 2, 28))


if __name__ == "__main__":
    unittest.main()

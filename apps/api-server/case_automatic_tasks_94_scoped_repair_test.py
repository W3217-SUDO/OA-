"""9.4 scoped production repair must be exact, atomic, and idempotent."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, User, WorkflowEvent
from scripts import apply_94_automatic_task_rework as repair


class AutomaticTasks94ScopedRepairTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="lawyer", display_name="经办律师", department="诉讼部", role="user", password_hash="x", is_active=True),
                User(username="assistant", display_name="律师助理", department="诉讼部", role="user", password_hash="x", is_active=True),
            ])
            for index in range(3):
                case = BusinessRecord(
                    module="case", serial_no=f"R94-DOC-{index}", title="案件", customer="客户",
                    status="一审和解结案" if index else "文书准备", owner="lawyer", department="诉讼部",
                    data={"handling_lawyer_usernames": ["lawyer"], "assistant_usernames": ["assistant"]},
                )
                db.add(case); await db.flush()
                db.add(WorkflowEvent(
                    record_id=case.id, action="修改普通案件基本信息", from_status="等待公证书",
                    to_status="文书准备", operator="admin",
                    created_at=datetime(2026, 9, 8, 6, 10 + index, tzinfo=timezone.utc),
                ))
            archive_cases = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.serial_no.in_(["R94-DOC-1", "R94-DOC-2"])
            ))).all())
            for index, case in enumerate(archive_cases):
                db.add(WorkflowEvent(
                    record_id=case.id, action="修改案件阶段", from_status="文书准备",
                    to_status="一审和解结案", operator="admin",
                    created_at=datetime(2026, 9, 8, 7, 10 + index, tzinfo=timezone.utc),
                ))
            await db.commit()
            self.document_event_ids = list((await db.scalars(select(WorkflowEvent.id).where(
                WorkflowEvent.to_status == "文书准备"
            ).order_by(WorkflowEvent.id))).all())
            self.archive_event_ids = list((await db.scalars(select(WorkflowEvent.id).where(
                WorkflowEvent.to_status == "一审和解结案"
            ).order_by(WorkflowEvent.id))).all())
        repair.SessionLocal = self.sessions

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    def args(self, apply: bool) -> SimpleNamespace:
        return SimpleNamespace(
            apply=apply,
            owner_username="liangchenyu",
            owner_display_name="梁晨宇",
            owner_department="诉讼四部",
            dingtalk_user_id="row94-dingtalk-user",
            document_event_id=self.document_event_ids,
            archive_event_id=self.archive_event_ids,
        )

    async def test_dry_run_is_read_only_and_apply_is_exact_and_idempotent(self) -> None:
        preview = await repair.run(self.args(False))
        self.assertEqual((preview["owner_action"], len(preview["document_events"]), len(preview["archive_events"])), ("create", 3, 2))
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(User).where(User.username == "liangchenyu")))
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "task")), 0)

        applied = await repair.run(self.args(True))
        repeated = await repair.run(self.args(True))
        self.assertEqual(len(applied["task_ids"]), 5)
        self.assertEqual(repeated["task_ids"], applied["task_ids"])
        async with self.sessions() as db:
            owner = await db.scalar(select(User).where(User.username == "liangchenyu"))
            tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all())
        self.assertEqual((owner.display_name, owner.department, owner.role), ("梁晨宇", "诉讼四部", "user"))
        self.assertEqual(sum(task.title == "文书准备阶段" for task in tasks), 3)
        self.assertEqual(sum(task.title == "结算归档一审和解结案" for task in tasks), 2)


if __name__ == "__main__":
    unittest.main()

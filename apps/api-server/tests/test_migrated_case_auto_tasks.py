"""陶国南 11-01：迁移案件不再由后台扫描生成自动任务；此前给迁移案件批量生成的自动任务不计超期绩效。"""
import unittest
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.case_automation import is_migrated_case
from app.core.tasks import _apply_task_overdue_performance
from app.database import Base
from app.models import BusinessRecord


class MigratedCaseAutoTaskTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        overdue = (date.today() - timedelta(days=5)).isoformat()
        old = datetime(2026, 10, 12, tzinfo=timezone.utc)
        async with self.sessions() as db:
            db.add(BusinessRecord(id=1, module="case", serial_no="AJ1", title="迁移案件", status="文书准备", owner="a", data={"legacy_case_id": 9}))
            db.add(BusinessRecord(id=2, module="case", serial_no="AJ2", title="新案件", status="文书准备", owner="a", data={}))
            auto = {"source": "案件任务", "creation_mode": "自动", "system_created_by": "system", "deadline": overdue}
            db.add(BusinessRecord(id=11, module="task", serial_no="RW11", title="文书过期提醒", status="待接收", owner="a", created_at=old, data={**auto, "case_id": 1}))
            db.add(BusinessRecord(id=12, module="task", serial_no="RW12", title="文书过期提醒", status="待接收", owner="a", created_at=old, data={**auto, "case_id": 2}))
            db.add(BusinessRecord(id=13, module="task", serial_no="RW13", title="人工任务", status="待接收", owner="a", created_at=old,
                                  data={"source": "案件任务", "deadline": overdue, "case_id": 1}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_migrated_marker(self):
        async with self.sessions() as db:
            self.assertTrue(is_migrated_case(await db.get(BusinessRecord, 1)))
            self.assertFalse(is_migrated_case(await db.get(BusinessRecord, 2)))

    async def test_batch_auto_tasks_on_migrated_cases_get_no_penalty(self):
        async with self.sessions() as db:
            await _apply_task_overdue_performance(db)
        async with self.sessions() as db:
            impacts = {task.id: (task.data or {}).get("performance_impact") for task in
                       (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()}
        self.assertFalse(impacts[11])
        self.assertTrue(impacts[12]["overdue"])
        self.assertTrue(impacts[13]["overdue"])


if __name__ == "__main__":
    unittest.main()

"""9.2 row 6: urgent queue and phase-duration projection."""

import unittest
from datetime import date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    CounselCaseSearchInput,
    _case_phase_changed_days,
    _contract_customer_record_dict,
    _query_counsel_cases,
    dashboard,
)
from app.models import BusinessRecord, User


IDENTITY = {"username": "codex-92-r6-admin", "role": "admin"}


class DashboardUrgentPhaseDuration92Row6Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="Dashboard Admin", department="测试部", role="admin", password_hash="test", is_active=True))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def case(serial_no: str, days: int, *, data=None):
        changed = date.today() - timedelta(days=days)
        return BusinessRecord(
            module="case", serial_no=serial_no, title=serial_no, customer="测试客户",
            status="新案待分配", owner=IDENTITY["username"], department="测试部",
            created_at=datetime.combine(changed, time.min), updated_at=datetime.now(),
            data={"case_type": "民事案件", "phase_changed_at": changed.isoformat(), **(data or {})},
        )

    async def test_urgent_card_and_drilldown_share_owned_task_deadline_scope(self):
        overdue = self.case("CODEX-92-R6-OVER", 366)
        boundary = self.case("CODEX-92-R6-BOUNDARY", 365)
        flagged_recent = self.case("CODEX-92-R6-FLAGGED", 20, data={"priority": "紧急", "urgent": True})
        legacy = self.case(
            "CODEX-92-R6-LEGACY", 1,
            data={"phase_changed_at": "", "legacy_record": {"ChangeTime": str(date.today() - timedelta(days=500))}},
        )
        urgent_counsel = self.case(
            "CODEX-92-R6-COUNSEL", 400,
            data={"case_type": "法律顾问"},
        )
        async with self.sessions() as db:
            db.add_all([
                overdue, boundary, flagged_recent, legacy, urgent_counsel,
                BusinessRecord(
                    module="task", serial_no="CODEX-92-R6-OTHER-TASK", title="他人的到期任务",
                    customer="测试客户", status="待处理", owner="other", department="测试部",
                    data={"source": "案件任务", "case_no": overdue.serial_no, "deadline": str(date.today())},
                ),
                BusinessRecord(
                    module="task", serial_no="CODEX-92-R6-BOUNDARY-TASK", title="十五天内任务",
                    customer="测试客户", status="待处理", owner=IDENTITY["username"], department="测试部",
                    data={"source": "案件任务", "case_no": boundary.serial_no, "deadline": str(date.today() + timedelta(days=15))},
                ),
                BusinessRecord(
                    module="task", serial_no="CODEX-92-R6-LEGACY-TASK", title="十六天后任务",
                    customer="测试客户", status="待处理", owner=IDENTITY["username"], department="测试部",
                    data={"source": "案件任务", "case_no": legacy.serial_no, "deadline": str(date.today() + timedelta(days=16))},
                ),
                BusinessRecord(
                    module="task", serial_no="CODEX-92-R6-COUNSEL-TASK", title="逾期法律顾问任务",
                    customer="测试客户", status="待处理", owner=IDENTITY["username"], department="测试部",
                    data={"source": "案件任务", "case_no": urgent_counsel.serial_no, "deadline": str(date.today() - timedelta(days=1))},
                ),
            ])
            await db.commit()
            result = await dashboard(IDENTITY, db, section="metrics")
            drilldown = await _query_counsel_cases(
                CounselCaseSearchInput(dashboard_queue="urgent-cases"),
                IDENTITY,
                db,
                counsel_only=False,
            )

        self.assertEqual(
            {item.serial_no for item in drilldown},
            {"CODEX-92-R6-BOUNDARY", "CODEX-92-R6-COUNSEL"},
        )
        metric = {item["key"]: item for item in result["metrics"]}["urgent-cases"]
        self.assertEqual(metric["value"], f"{len(drilldown)}件")
        self.assertEqual(metric["route"], "dashboard-queue-urgent-cases")

    async def test_projection_uses_persisted_or_legacy_start_and_ignores_updated_at(self):
        record = self.case("CODEX-92-R6-DISPLAY", 100)
        record.updated_at = datetime.now()
        async with self.sessions() as db:
            db.add(record)
            await db.commit()
            projected = await _contract_customer_record_dict(record, None, db, identity=IDENTITY)

        self.assertEqual(_case_phase_changed_days(record), 100)
        self.assertEqual(projected["data"]["phase_changed_at"], str(date.today() - timedelta(days=100)))
        self.assertEqual(projected["data"]["phase_changed_days"], 100)
        self.assertEqual(projected["data"]["phase_duration"], "100天")


if __name__ == "__main__":
    unittest.main()

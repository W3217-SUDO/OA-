"""BUG 500801：报表大屏经营总数据——新增案件、调查线索（提交/审核通过）、开庭、任务（发出/完成）。"""
import unittest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401  注册全部模型
from app.core.large_screen_overview import case_month_counts, clue_rankings, hearing_month_counts, task_month_counts
from app.core.person_names import refresh_person_names
from app.database import Base
from app.models import BusinessRecord, User


def at(day: str) -> datetime:
    return datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=timezone.utc)


class LargeScreenOverviewTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def test_cases_and_hearings_by_month(self):
        cases = [
            BusinessRecord(module="case", serial_no="C1", customer="客户甲", status="一审立案受理", created_at=at("2026-03-05"),
                           data={"first_court_hearing_date": "2026-03-20", "second_court_hearing_date": "2026-11-02", "execution_court_hearing_date": "2025-12-01"}),
            BusinessRecord(module="case", serial_no="C2", customer="测试11.13", status="一审立案受理", created_at=at("2026-03-06"),
                           data={"first_court_hearing_date": "2026-03-21"}),
            BusinessRecord(module="case", serial_no="C3", customer="客户乙", status="一审立案受理", created_at=at("2025-12-30"), data={}),
        ]
        self.assertEqual(case_month_counts(cases, 2026)[2], {"month": 3, "value": 2})
        hearings = {item["month"]: item["value"] for item in hearing_month_counts(cases, 2026)}
        self.assertEqual((hearings[3], hearings[11], sum(hearings.values())), (1, 1, 2))  # 测试客户、往年日期不算

    async def test_clues_and_tasks(self):
        async with self.sessions() as db:
            db.add(User(username="sugl", display_name="苏贵龙", password_hash="x", role="staff"))
            customer = BusinessRecord(module="customer", serial_no="KH1", title="无限极（中国）有限公司", customer="无限极（中国）有限公司", status="正常", owner="admin", data={"customer_short_name": "无限极"})
            db.add(customer)
            await db.flush()
            def clue(no, status, created, owner="sugl"):
                return BusinessRecord(module="clue", serial_no=no, title=no, customer="无限极（中国）有限公司", status=status, owner=owner,
                                      created_at=at(created), data={"customer_record_id": customer.id})
            def task(no, status, created, data=None):
                return BusinessRecord(module="task", serial_no=no, title=no, status=status, owner="admin", created_at=at(created), data=data or {})
            db.add_all([
                clue("M1", "已取证", "2026-02-01"), clue("M2", "待审批", "2026-02-02"), clue("M3", "已驳回", "2026-02-03"),
                clue("M4", "草稿", "2026-02-04"), clue("M5", "待取证", "2025-12-31"),
                task("T1", "处理中", "2026-10-30", {"legacy_record": {"CreateTime": "2026-06-10T09:00:00"}}),
                task("T2", "已取消", "2026-10-30"),
                task("T3", "已完成", "2026-10-30", {"auto_completed_at": "2026-10-31T10:00:00"}),
                task("T4", "已验收", "2026-09-01", {"finished_at": "2026-09-15T10:00:00"}),
            ])
            await db.commit()
            await refresh_person_names(db, force=True)
            clues = await clue_rankings(db, [], 2026)
            tasks = {item["month"]: item for item in await task_month_counts(db, [], 2026)}
        self.assertEqual(clues["by_investigator"], [{"name": "苏贵龙", "submitted": 3, "approved": 1}])
        self.assertEqual(clues["by_brand"], [{"name": "无限极", "submitted": 3, "approved": 1}])
        self.assertEqual((clues["submitted"], clues["approved"]), (3, 1))
        self.assertEqual((tasks[6]["issued"], tasks[9]["issued"], tasks[10]["issued"]), (1, 1, 1))
        self.assertEqual((tasks[9]["done"], tasks[10]["done"]), (1, 1))


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import CounselCaseSearchInput, dashboard, search_ordinary_cases
from app.models import BusinessRecord


IDENTITY = {"username": "admin", "role": "admin"}


class DashboardAppealScopeRow5Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
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

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def case(serial_no: str, status: str, owner: str, data=None):
        return BusinessRecord(
            module="case",
            serial_no=serial_no,
            title=serial_no,
            customer="CODEX-827-R5-客户",
            status=status,
            owner=owner,
            department="测试部",
            data=data or {},
        )

    async def test_card_and_drilldown_exclude_other_users_and_non_exact_signals(self):
        async with self.sessions() as db:
            db.add_all([
                self.case("CODEX-827-R5-OTHER", "一审等待上诉", "other"),
                self.case(
                    "CODEX-827-R5-FALSE-SIGNAL",
                    "一审上诉准备",
                    "admin",
                    {"required_action": "待上诉"},
                ),
                self.case(
                    "CODEX-827-R5-STALE-PROJECTION",
                    "二审立案受理",
                    "admin",
                    {"case_phase": "待上诉"},
                ),
            ])
            await db.commit()
            dashboard_result = await dashboard(IDENTITY, db)
            list_result = await search_ordinary_cases(
                CounselCaseSearchInput(
                    scope="mine",
                    case_statuses=["一审等待上诉", "待上诉"],
                    page=1,
                    page_size=15,
                ),
                IDENTITY,
                db,
            )

        metric = next(item for item in dashboard_result["metrics"] if item["key"] == "appeal-pending")
        self.assertEqual(metric["value"], "0件")
        self.assertEqual(metric["route"], "case-mine-appeal")
        self.assertEqual(list_result["total"], 0)

    async def test_card_and_drilldown_match_personal_owner_and_legacy_participant(self):
        async with self.sessions() as db:
            db.add_all([
                self.case("CODEX-827-R5-OWN", "一审等待上诉", "admin"),
                self.case(
                    "CODEX-827-R5-PARTICIPANT",
                    "待上诉",
                    "other",
                    {"legacy_participants": [{"staff_name": "admin"}]},
                ),
                self.case("CODEX-827-R5-OTHER", "一审等待上诉", "other"),
                self.case("CODEX-827-R5-WRONG-PHASE", "二审立案受理", "admin"),
            ])
            await db.commit()
            dashboard_result = await dashboard(IDENTITY, db)
            list_result = await search_ordinary_cases(
                CounselCaseSearchInput(
                    scope="mine",
                    case_statuses=["一审等待上诉", "待上诉"],
                    page=1,
                    page_size=15,
                ),
                IDENTITY,
                db,
            )

        metric = next(item for item in dashboard_result["metrics"] if item["key"] == "appeal-pending")
        self.assertEqual(metric["value"], "2件")
        self.assertEqual(list_result["total"], 2)
        self.assertEqual(
            {item["serial_no"] for item in list_result["items"]},
            {"CODEX-827-R5-OWN", "CODEX-827-R5-PARTICIPANT"},
        )


if __name__ == "__main__":
    unittest.main()

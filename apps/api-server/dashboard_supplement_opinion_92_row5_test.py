"""9.2 row 5: supplement-opinion dashboard count and drilldown parity."""

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import CounselCaseSearchInput, _query_counsel_cases, dashboard
from app.models import BusinessRecord


IDENTITY = {"username": "codex-92-r5-admin", "role": "admin"}


class DashboardSupplementOpinion92Row5Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def case(serial_no: str, status: str, *, case_type: str = "民事案件", data=None):
        return BusinessRecord(
            module="case", serial_no=serial_no, title=serial_no, customer="测试客户",
            status=status, owner=IDENTITY["username"], department="测试部",
            data={"case_type": case_type, **(data or {})},
        )

    async def test_card_and_drilldown_share_exact_legacy_phase_queue(self):
        records = [
            self.case("CODEX-92-R5-FIRST", "一审补充代理意见"),
            self.case("CODEX-92-R5-SECOND", "二审补充代理意见"),
            self.case("CODEX-92-R5-PROJECTED", "历史数据", data={"case_phase_name": "一审补充代理意见"}),
            self.case("CODEX-92-R5-TEXT", "一审准备开庭", data={"required_action": "补充意见"}),
            self.case("CODEX-92-R5-EVIDENCE", "一审补充证据"),
            self.case("CODEX-92-R5-CRIMINAL", "一审补充代理意见", case_type="刑事案件"),
        ]
        async with self.sessions() as db:
            db.add_all(records)
            await db.commit()
            result = await dashboard(IDENTITY, db)
            drilldown = await _query_counsel_cases(
                CounselCaseSearchInput(scope="company", case_queue="supplement_opinion"),
                IDENTITY,
                db,
                counsel_only=False,
            )

        case_nos = {item.serial_no for item in drilldown}
        self.assertEqual(case_nos, {
            "CODEX-92-R5-FIRST", "CODEX-92-R5-SECOND", "CODEX-92-R5-PROJECTED",
        })
        metric = {item["key"]: item for item in result["metrics"]}["opinion-supplement"]
        self.assertEqual(metric["value"], f"{len(drilldown)}件")
        self.assertEqual(metric["route"], "case-company-supplement-opinion")


if __name__ == "__main__":
    unittest.main()

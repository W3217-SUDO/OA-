import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import CounselCaseSearchInput, _query_counsel_cases, dashboard
from app.models import BusinessRecord


IDENTITY = {"username": "admin", "role": "admin"}


class DashboardSupplementEvidenceQueueRow4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_queue_only_returns_civil_cases_in_exact_legacy_supplement_phases(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R4-IN", title="真实补证阶段",
                    customer="客户", status="二审补充证据", owner="admin", department="上海",
                    data={"case_type": "民事案件", "investigator": "调查员甲"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R4-TEXT", title="仅备注补证",
                    customer="客户", status="二审准备开庭", owner="admin", department="上海",
                    data={"case_type": "民事案件", "required_action": "补充证据"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R4-CRIMINAL", title="刑事补证阶段",
                    customer="客户", status="二审补充证据", owner="admin", department="上海",
                    data={"case_type": "刑事案件"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R4-ORDINARY", title="普通案件",
                    customer="客户", status="二审准备开庭", owner="admin", department="上海",
                    data={"case_type": "民事案件"},
                ),
            ])
            await db.commit()
            dashboard_result = await dashboard(IDENTITY, db)
            records = await _query_counsel_cases(
                CounselCaseSearchInput(scope="company", case_queue="supplement_evidence"),
                IDENTITY,
                db,
                counsel_only=False,
            )

        self.assertEqual([item.serial_no for item in records], ["CODEX-827-R4-IN"])
        metrics = {item["key"]: item for item in dashboard_result["metrics"]}
        self.assertEqual(metrics["evidence-supplement"]["value"], f"{len(records)}件")
        self.assertEqual(
            metrics["evidence-supplement"]["route"],
            "case-company-supplement-evidence",
        )

    async def test_unknown_queue_is_rejected(self):
        async with self.sessions() as db:
            with self.assertRaisesRegex(Exception, "案件工作队列无效"):
                await _query_counsel_cases(
                    CounselCaseSearchInput(scope="company", case_queue="all_cases"),
                    IDENTITY,
                    db,
                    counsel_only=False,
                )


if __name__ == "__main__":
    unittest.main()

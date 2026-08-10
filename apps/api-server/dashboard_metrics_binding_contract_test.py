import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard
from app.models import BusinessRecord


IDENTITY = {"username": "admin", "role": "admin"}


class DashboardMetricsBindingContractTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_dashboard_metrics_follow_real_business_fields_and_routes(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="finance", serial_no="FY-DASH-OFFICIAL", title="官费",
                    customer="客户", status="草稿", owner="admin", department="上海",
                    data={"fee_type": "官方费用", "amount": 100, "paid_amount": 20},
                ),
                BusinessRecord(
                    module="finance", serial_no="FY-DASH-REFUND", title="退费",
                    customer="客户", status="待审批", owner="admin", department="上海",
                    data={"fee_type": "代理费", "refund_requested_amount": 50, "refunded_amount": 10},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-URGENT", title="紧急案件",
                    customer="客户", status="新案待分配", owner="admin", department="上海",
                    data={"priority": "紧急"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-EXECUTION", title="待执行案件",
                    customer="客户", status="一审准备开庭", owner="admin", department="上海",
                    data={"execution_status": "一审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-APPEAL", title="待上诉案件",
                    customer="客户", status="待上诉", owner="admin", department="上海", data={},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-SUPPLEMENT", title="补充材料案件",
                    customer="客户", status="文书准备", owner="admin", department="上海",
                    data={"required_action": "补充证据", "supplement_type": "补充意见"},
                ),
            ])
            await db.commit()
            result = await dashboard(IDENTITY, db)

        metrics = {item["key"]: item for item in result["metrics"]}
        self.assertEqual(metrics["official-fee-unpaid"]["value"], "1件")
        self.assertEqual(metrics["official-fee-unreceived"]["value"], "80.00元")
        self.assertEqual(metrics["refund-pending"]["value"], "1件")
        self.assertEqual(metrics["evidence-supplement"]["value"], "1件")
        self.assertEqual(metrics["opinion-supplement"]["value"], "1件")
        self.assertEqual(metrics["appeal-pending"]["value"], "1件")
        self.assertEqual(metrics["execution-pending"]["value"], "1件")
        self.assertEqual(metrics["urgent-cases"]["value"], "1件")
        self.assertEqual(metrics["execution-pending"]["route"], "case-company-execution")
        self.assertEqual(result["source"], "realtime")


if __name__ == "__main__":
    unittest.main()

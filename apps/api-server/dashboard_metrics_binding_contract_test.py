import unittest
from datetime import date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard, list_pending_execution_cases
from app.models import BusinessRecord, ContractObject, HearingSchedule, User


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
            contract = BusinessRecord(
                module="contract", serial_no="HT-DASH-OFFICIAL", title="官费应收合同",
                customer="客户", status="审批通过", owner="admin", department="上海", data={},
            )
            db.add(contract)
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="AJ-DASH-OFFICIAL", title="官费应收案件",
                customer="客户", status="一审", owner="admin", department="上海",
                data={"contract_id": contract.id, "contract_no": contract.serial_no},
            )
            db.add(case)
            await db.flush()
            db.add(ContractObject(
                contract_record_id=contract.id, case_record_id=case.id,
                fee_type="官费", amount=100, created_by="admin", updated_by="admin",
            ))
            db.add_all([
                BusinessRecord(
                    module="finance", serial_no="FY-DASH-OFFICIAL", title="官费",
                    customer="客户", status="草稿", owner="admin", department="上海",
                    data={
                        "fee_type": "官方费用", "amount": 100, "paid_amount": 70,
                        "received_amount": 20, "contract_id": contract.id,
                        "case_id": case.id, "case_no": case.serial_no,
                    },
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
                    customer="客户", status="一审待执行", owner="admin", department="上海",
                    data={"case_phase": "一审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-APPEAL", title="待上诉案件",
                    customer="客户", status="待上诉", owner="admin", department="上海", data={},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-SUPPLEMENT", title="补充材料案件",
                    customer="客户", status="一审补充证据", owner="admin", department="上海",
                    data={"case_type": "民事争议", "supplement_type": "补充意见"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-FALSE-SUPPLEMENT", title="仅文字提到补证",
                    customer="客户", status="文书准备", owner="admin", department="上海",
                    data={"case_type": "民事争议", "required_action": "补充证据"},
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
        self.assertEqual(metrics["evidence-supplement"]["route"], "case-company-supplement-evidence")
        self.assertEqual(metrics["execution-pending"]["route"], "case-company-execution")
        self.assertEqual(result["source"], "realtime")

    async def test_pending_execution_list_uses_dashboard_phases_and_role_scope(self):
        async with self.sessions() as db:
            db.add(User(
                username="limited", display_name="受限用户", department="测试部",
                password_hash="unused", role="user", is_active=True,
            ))
            db.add_all([
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-FIRST", title="一审待执行",
                    customer="客户", status="一审待执行", owner="limited", department="测试部",
                    data={"case_phase": "一审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-SECOND", title="二审待执行",
                    customer="客户", status="二审待执行", owner="other", department="其他部",
                    data={"case_phase": "二审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-RETRIAL", title="再审待执行",
                    customer="客户", status="再审待执行", owner="other", department="其他部",
                    data={"case_phase": "再审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-ACTIVE", title="已经执行",
                    customer="客户", status="执行受理", owner="limited", department="测试部",
                    data={"case_phase": "执行受理", "execution_status": "执行受理"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-STALE-SIGNAL", title="历史执行字段残留",
                    customer="客户", status="一审准备开庭", owner="limited", department="测试部",
                    data={"case_phase": "一审准备开庭", "execution_status": "一审待执行"},
                ),
            ])
            await db.commit()

            admin_dashboard = await dashboard(IDENTITY, db)
            admin_list = await list_pending_execution_cases(1, 20, IDENTITY, db)
            admin_page_one = await list_pending_execution_cases(1, 2, IDENTITY, db)
            admin_page_two = await list_pending_execution_cases(2, 2, IDENTITY, db)
            limited_list = await list_pending_execution_cases(
                1, 20, {"username": "limited", "role": "user"}, db,
            )

        admin_metric = next(item for item in admin_dashboard["metrics"] if item["key"] == "execution-pending")
        self.assertEqual(admin_metric["value"], "3件")
        self.assertEqual(admin_list["total"], 3)
        self.assertEqual(
            {item["serial_no"] for item in admin_list["items"]},
            {"CODEX-827-R6-FIRST", "CODEX-827-R6-SECOND", "CODEX-827-R6-RETRIAL"},
        )
        self.assertEqual(admin_page_one["total"], 3)
        self.assertEqual(admin_page_two["total"], 3)
        self.assertEqual(
            {item["serial_no"] for item in admin_page_one["items"] + admin_page_two["items"]},
            {"CODEX-827-R6-FIRST", "CODEX-827-R6-SECOND", "CODEX-827-R6-RETRIAL"},
        )
        self.assertEqual(limited_list["total"], 1)
        self.assertEqual(limited_list["items"][0]["serial_no"], "CODEX-827-R6-FIRST")

    async def test_dashboard_hearings_follow_case_court_fields_with_legacy_priority(self):
        first_hearing = datetime.combine(date.today() + timedelta(days=5), time(9, 30))
        retrial_hearing = datetime.combine(date.today() + timedelta(days=7), time(14, 15))
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-826-R2-CASE", title="开庭排期关联案件",
                customer="CODEX-826-R2-客户", status="再审", owner="admin", department="上海",
                data={
                    "first_court_name": "一审法院",
                    "first_court_hearing_date": str(first_hearing),
                    "retrial_court_name": "CODEX-826-R2-再审法院",
                    "retrial_court_courtroom": "第二法庭",
                    "retrial_court_hearing_date": str(retrial_hearing),
                    "hearing_lawyer": "开庭律师",
                    "handling_lawyers": ["经办律师"],
                    "assistant": "律师助理",
                },
            )
            db.add(case)
            await db.flush()
            db.add(HearingSchedule(
                case_record_id=case.id, hearing_date=first_hearing.date(), hearing_time="09:30",
                court="旧的独立排期", courtroom="第一法庭", hearing_type="一审开庭",
                hearing_lawyer="开庭律师", status="已排期",
            ))
            await db.commit()
            result = await dashboard(IDENTITY, db)

        matching = [item for item in result["hearings"] if item["case_no"] == "CODEX-826-R2-CASE"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["date"], str(retrial_hearing.date()))
        self.assertEqual(matching[0]["time"], "14:15")
        self.assertEqual(matching[0]["court"], "CODEX-826-R2-再审法院")
        self.assertEqual(matching[0]["lawyer"], "开庭律师")
        self.assertEqual(matching[0]["agent"], "经办律师")
        self.assertEqual(matching[0]["assistant"], "律师助理")


if __name__ == "__main__":
    unittest.main()

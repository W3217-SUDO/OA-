import unittest
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard
from app.models import BusinessRecord, User


ADMIN = {"username": "admin", "role": "admin"}


class DashboardLatestCasePeopleRow8Test(unittest.IsolatedAsyncioTestCase):
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

    async def test_latest_cases_project_legacy_equivalent_fields_and_people(self):
        async with self.sessions() as db:
            db.add_all([
                User(
                    username="manager01", display_name="客户经理甲", password_hash="unused",
                    role="user", department="客户部", is_active=True, profile={},
                ),
                User(
                    username="court01", display_name="开庭律师乙", password_hash="unused",
                    role="user", department="诉讼部", is_active=True, profile={},
                ),
                User(
                    username="handler01", display_name="经办律师丙", password_hash="unused",
                    role="user", department="诉讼部", is_active=True, profile={},
                ),
                User(
                    username="assistant01", display_name="律师助理丁", password_hash="unused",
                    role="user", department="诉讼部", is_active=True, profile={},
                ),
            ])
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-827-R8-CUSTOMER", title="第八行客户",
                customer="第八行客户", status="有效", owner="manager01", department="客户部",
                data={
                    "customer_managers": ["manager01"],
                    "customer_manager_display_names": ["过期客户管理人"],
                },
            )
            db.add(customer)
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="CODEX-827-R8-CASE", title="第八行最新案件",
                customer="第八行客户", status="内部状态不应展示", owner="handler01", department="诉讼部",
                created_at=datetime.now() - timedelta(days=10),
                data={
                    "customer_record_id": customer.id,
                    "customer_no": customer.serial_no,
                    "case_register_date": "2026-08-27 09:30:00",
                    "case_phase_name": "一审准备开庭",
                    "plaintiffs": ["原告甲", "原告乙"],
                    "defendants": ["被告甲", "被告乙"],
                    "customer_manager_display_name": "过期客户管理人",
                    "hearing_lawyer_display_name": "过期开庭律师",
                    "hearing_lawyer_username": "court01",
                    "handling_lawyer_display_names": ["过期经办律师"],
                    "handling_lawyer_usernames": ["handler01"],
                    "assistant_display_name": "过期律师助理",
                    "assistant_username": "assistant01",
                    "legacy_record": {
                        "CourtLawyerName": "旧开庭律师不应覆盖稳定账号",
                        "CaseLawyerName": "旧经办律师不应覆盖稳定账号",
                        "CaseAssistantName": "旧助理不应覆盖稳定账号",
                    },
                },
            )
            older_but_recently_created = BusinessRecord(
                module="case", serial_no="CODEX-827-R8-OLDER", title="创建时间较新但案源日期较旧",
                customer="另一客户", status="待分配", owner="admin", department="诉讼部",
                created_at=datetime.now(), data={"case_register_date": "2026-08-20"},
            )
            db.add_all([case, older_but_recently_created])
            await db.commit()

            result = await dashboard(ADMIN, db)

        self.assertEqual(result["latest_cases"][0], {
            "case_no": "CODEX-827-R8-CASE",
            "stage": "一审准备开庭",
            "plaintiff": "原告甲、原告乙",
            "defendant": "被告甲、被告乙",
            "date": "2026-08-27",
            "manager": "客户经理甲",
            "lawyer": "开庭律师乙",
            "agent": "经办律师丙",
            "assistant": "律师助理丁",
        })
        self.assertEqual(result["latest_cases"][1]["case_no"], "CODEX-827-R8-OLDER")

    async def test_latest_cases_use_legacy_names_and_keep_legacy_page_size(self):
        async with self.sessions() as db:
            for index in range(14):
                db.add(BusinessRecord(
                    module="case", serial_no=f"CODEX-827-R8-{index:02d}", title=f"案件{index}",
                    customer="历史客户", status="历史阶段", owner="admin", department="诉讼部",
                    data={
                        "case_register_date": f"2026-08-{index + 1:02d}",
                        "legacy_record": {
                            "AppellantNames": "历史原告", "AppelleeNames": "历史被告",
                            "CoordinatorName": "历史客户管理人", "CourtLawyerName": "历史开庭律师",
                            "CaseLawyerName": "历史经办律师", "CaseAssistantName": "历史律师助理",
                        },
                    },
                ))
            await db.commit()

            result = await dashboard(ADMIN, db)

        self.assertEqual(len(result["latest_cases"]), 13)
        self.assertEqual(result["latest_cases"][0]["case_no"], "CODEX-827-R8-13")
        self.assertEqual(result["latest_cases"][0]["manager"], "历史客户管理人")
        self.assertEqual(result["latest_cases"][0]["lawyer"], "历史开庭律师")
        self.assertEqual(result["latest_cases"][0]["agent"], "历史经办律师")
        self.assertEqual(result["latest_cases"][0]["assistant"], "历史律师助理")

    async def test_latest_cases_do_not_project_system_or_ambiguous_customer_owner_as_people(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="customer", serial_no="CODEX-827-R8-DUPLICATE-A", title="同名客户",
                    customer="同名客户", status="有效", owner="manager-a", department="客户部", data={},
                ),
                BusinessRecord(
                    module="customer", serial_no="CODEX-827-R8-DUPLICATE-B", title="同名客户",
                    customer="同名客户", status="有效", owner="manager-b", department="客户部", data={},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R8-AMBIGUOUS", title="同名客户案件",
                    customer="同名客户", status="待分配", owner="admin", department="诉讼部",
                    data={
                        "case_register_date": "2026-08-27",
                        "handling_lawyer_usernames": ["System"],
                        "hearing_lawyer_username": "missing-account",
                        "assistant_username": "missing-assistant",
                    },
                ),
            ])
            await db.commit()

            result = await dashboard(ADMIN, db)

        row = result["latest_cases"][0]
        self.assertEqual(row["case_no"], "CODEX-827-R8-AMBIGUOUS")
        self.assertEqual(row["manager"], "")
        self.assertEqual(row["lawyer"], "")
        self.assertEqual(row["agent"], "")
        self.assertEqual(row["assistant"], "")


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _fee_query_rows, dashboard
from app.models import BusinessRecord, FinanceTransaction


IDENTITY = {"username": "admin", "role": "admin"}


class DashboardUnpaidOfficialFeeRow3Test(unittest.IsolatedAsyncioTestCase):
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
    def record(
        serial_no, owner, status, fee_type, amount, case_no, *, paid_amount=0,
    ):
        return BusinessRecord(
            module="finance", serial_no=serial_no, title=fee_type,
            customer="CODEX-827-R3-客户", status=status, owner=owner,
            department="测试部", data={
                "fee_type": fee_type, "amount": amount, "case_no": case_no,
                "paid_amount": paid_amount,
            },
        )

    async def test_dashboard_count_and_clicked_query_share_personal_unpaid_scope(self):
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-827-R3-CASE", title="待缴官费案件",
                customer="CODEX-827-R3-客户", status="一审", owner="admin",
                department="测试部", data={"hearing_lawyer": "范文玲"},
            )
            own_unpaid = self.record(
                "CODEX-827-R3-FEE-OWN", "admin", "已审批", "官方费用", 300,
                "CODEX-827-R3-CASE",
            )
            other_unpaid = self.record(
                "CODEX-827-R3-FEE-OTHER", "other", "已审批", "官方费用", 400,
                "CODEX-827-R3-CASE",
            )
            own_paid = self.record(
                "CODEX-827-R3-FEE-PAID", "admin", "已付款", "官方费用", 200,
                "CODEX-827-R3-CASE",
            )
            own_non_official = self.record(
                "CODEX-827-R3-FEE-AGENCY", "admin", "已审批", "代理费", 500,
                "CODEX-827-R3-CASE",
            )
            own_historical_paid = self.record(
                "CODEX-827-R3-FEE-HISTORICAL-PAID", "admin", "已审批",
                "官方费用", 250, "CODEX-827-R3-CASE", paid_amount=250,
            )
            own_partially_paid = self.record(
                "CODEX-827-R3-FEE-PARTIAL", "admin", "部分付款",
                "官方费用", 300, "CODEX-827-R3-CASE", paid_amount=100,
            )
            db.add_all([
                case, own_unpaid, other_unpaid, own_paid, own_non_official,
                own_historical_paid, own_partially_paid,
            ])
            await db.flush()
            db.add(FinanceTransaction(
                finance_record_id=own_paid.id, transaction_type="付款", amount=200,
                transaction_date=date(2026, 8, 27), voucher_no="CODEX-827-R3-PAY",
                counterparty="法院", operator="admin", remark="测试已付官费",
            ))
            await db.commit()

            clicked_rows = await _fee_query_rows(
                IDENTITY, db, scope="mine", unpaid_official=True,
            )
            result = await dashboard(IDENTITY, db)

        metric = next(item for item in result["metrics"] if item["key"] == "official-fee-unpaid")
        self.assertEqual(metric["value"], "2件")
        self.assertEqual(metric["query"], {"scope": "mine", "unpaid_official": True})
        self.assertEqual(
            {item["serial_no"] for item in clicked_rows},
            {"CODEX-827-R3-FEE-OWN", "CODEX-827-R3-FEE-PARTIAL"},
        )
        self.assertTrue(
            all(item["data"]["hearing_lawyer"] == "范文玲" for item in clicked_rows),
        )


if __name__ == "__main__":
    unittest.main()

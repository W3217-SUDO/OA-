import unittest
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import _fee_query_rows, app, dashboard
from app.models import BusinessRecord, FinanceTransaction, User
from app.security import current_identity


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
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="Dashboard Admin", department="测试部", role="admin", password_hash="test", is_active=True))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://dashboard-official-fee.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

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

    async def test_dashboard_counts_visible_cases_and_clicked_query_lists_unpaid_fee_rows(self):
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
            result = await dashboard(IDENTITY, db, section="metrics")
        clicked_response = await self.client.get(
            f"{settings.api_prefix}/finance/fees/query",
            params={"dashboard_queue": "official-fee-unpaid", "scope": "mine"},
        )

        metric = next(item for item in result["metrics"] if item["key"] == "official-fee-unpaid")
        self.assertEqual(metric["value"], "1件")
        self.assertEqual(metric["route"], "dashboard-queue-official-fee-unpaid")
        self.assertEqual(clicked_response.status_code, 200, clicked_response.text)
        self.assertEqual(clicked_response.json()["total"], 3)
        self.assertEqual(
            [item["serial_no"] for item in clicked_response.json()["cases"]],
            [case.serial_no],
        )
        self.assertEqual(
            {item["serial_no"] for item in clicked_rows},
            {"CODEX-827-R3-FEE-OWN", "CODEX-827-R3-FEE-PARTIAL"},
        )
        self.assertEqual(
            {item["serial_no"] for item in clicked_response.json()["items"]},
            {"CODEX-827-R3-FEE-OWN", "CODEX-827-R3-FEE-OTHER", "CODEX-827-R3-FEE-PARTIAL"},
        )
        self.assertTrue(
            all(item["data"]["hearing_lawyer"] == "范文玲" for item in clicked_rows),
        )


if __name__ == "__main__":
    unittest.main()

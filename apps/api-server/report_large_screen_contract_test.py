import unittest
from datetime import date, datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import _large_screen_case_is_closed, _large_screen_month_keys, app, report_large_screen
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, RolePermission, User
from app.security import current_identity


ADMIN = {"username": "admin", "role": "admin"}


class ReportLargeScreenContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def case(serial_no, status, data=None):
        return BusinessRecord(
            module="case", serial_no=serial_no, title=serial_no, customer="CODEX-LARGE-CUSTOMER",
            status=status, owner="admin", department="测试部", data=data or {},
            created_at=datetime.now(timezone.utc),
        )

    async def test_snapshot_uses_actual_cash_and_excludes_non_operational_cases(self):
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理员", password_hash="unused", role="admin"))
            db.add_all([
                self.case("CODEX-LARGE-ACTIVE", "一审", {"case_type": "民事案件"}),
                self.case("CODEX-LARGE-CLOSED", "一审", {"case_type": "民事案件", "case_closed_at": "2026-01-01T00:00:00+00:00"}),
                self.case("CODEX-LARGE-PHASE-CLOSED", "一审判决结案", {"case_type": "刑事案件"}),
                self.case("CODEX-LARGE-DRAFT", "草稿", {"case_type": "民事案件"}),
                self.case("CODEX-LARGE-CANCELLED", "已撤销", {"case_type": "民事案件"}),
                BusinessRecord(module="customer", serial_no="CODEX-LARGE-CUSTOMER", title="CODEX-LARGE-CUSTOMER", customer="", status="正常", owner="admin", department="测试部", data={}),
            ])
            await db.flush()
            db.add_all([
                IncomingPayment(receipt_no="CODEX-LARGE-IN", received_date=date.today(), amount=120.5, payer_name="测试付款方", operator="admin"),
                FinanceTransaction(finance_record_id=None, transaction_type="付款", amount=45.25, transaction_date=date.today(), operator="admin"),
                FinanceTransaction(finance_record_id=None, transaction_type="开票", amount=999, transaction_date=date.today(), operator="admin"),
            ])
            await db.commit()

            result = await report_large_screen(ADMIN, db)

        self.assertEqual(result["case_summary"], {"total": 3, "in_progress": 1, "closed": 2})
        self.assertEqual(result["customer_summary"]["total"], 1)
        self.assertTrue(result["finance"]["amount_visible"])
        self.assertEqual(result["finance"]["income"], 120.5)
        self.assertEqual(result["finance"]["expense"], 45.25)
        self.assertEqual(result["case_type_distribution"], [{"name": "民事案件", "value": 2}, {"name": "刑事案件", "value": 1}])
        self.assertEqual(result["employee_ranking"], [{"username": "admin", "name": "管理员", "value": 3}])
        self.assertEqual(len(result["monthly_trend"]), 12)
        current_month = date.today().strftime("%Y-%m")
        current = next(item for item in result["monthly_trend"] if item["month"] == current_month)
        self.assertEqual(current, {"month": current_month, "cases": 3, "income": 120.5, "expense": 45.25})

    async def test_empty_snapshot_has_zero_counts_and_twelve_continuous_months(self):
        async with self.sessions() as db:
            result = await report_large_screen(ADMIN, db)

        self.assertEqual(result["case_summary"], {"total": 0, "in_progress": 0, "closed": 0})
        self.assertEqual(result["customer_summary"], {"total": 0})
        self.assertEqual(result["employee_ranking"], [])
        self.assertEqual(result["case_type_distribution"], [])
        self.assertEqual(len(result["monthly_trend"]), 12)
        self.assertTrue(all(item["cases"] == 0 and item["income"] == 0 and item["expense"] == 0 for item in result["monthly_trend"]))

    def test_month_keys_are_continuous_across_year_boundary(self):
        self.assertEqual(
            _large_screen_month_keys(date(2026, 1, 31)),
            [
                "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07",
                "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01",
            ],
        )

    def test_closed_classification_rejects_pending_close_and_honors_archived_record_status(self):
        pending_close = self.case("CODEX-LARGE-PENDING-CLOSE", "待结案", {"case_phase": "待结案"})
        archived_with_stale_phase = self.case("CODEX-LARGE-ARCHIVED", "已归档", {"case_phase": "一审"})

        self.assertFalse(_large_screen_case_is_closed(pending_close))
        self.assertTrue(_large_screen_case_is_closed(archived_with_stale_phase))

    async def test_without_large_screen_permission_the_endpoint_is_denied(self):
        async with self.sessions() as db:
            db.add(User(username="limited", display_name="受限用户", password_hash="unused", role="user"))
            await db.commit()
            with self.assertRaises(HTTPException) as denied:
                await report_large_screen({"username": "limited", "role": "user"}, db)
        self.assertEqual(denied.exception.status_code, 403)

    async def test_authorized_user_without_amount_field_gets_scoped_counts_but_no_amounts(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="limited", display_name="受限用户", password_hash="unused", role="user"),
                RolePermission(
                    role="user", display_name="普通用户", data_scope="本人及共享数据",
                    menu_keys=["reports-large-screen"], field_keys=[],
                ),
                BusinessRecord(module="case", serial_no="CODEX-LARGE-OWN", title="own", customer="CODEX-LARGE-OWN-CUSTOMER", status="一审", owner="limited", department="测试部", data={}),
                BusinessRecord(module="case", serial_no="CODEX-LARGE-OTHER", title="other", customer="other", status="一审", owner="other", department="其他部", data={}),
            ])
            await db.commit()
            result = await report_large_screen({"username": "limited", "role": "user"}, db)

        self.assertEqual(result["case_summary"], {"total": 1, "in_progress": 1, "closed": 0})
        self.assertFalse(result["finance"]["amount_visible"])
        self.assertIsNone(result["finance"]["income"])
        self.assertIsNone(result["finance"]["expense"])
        self.assertTrue(all(row["income"] is None and row["expense"] is None for row in result["monthly_trend"]))

    async def test_personal_finance_scope_excludes_other_users_cash(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="limited", display_name="受限用户", password_hash="unused", role="user"),
                RolePermission(
                    role="user", display_name="普通用户", data_scope="本人及共享数据",
                    menu_keys=["reports-large-screen"], field_keys=["finance.amount"],
                ),
                BusinessRecord(module="customer", serial_no="CODEX-LARGE-LIMITED-CUSTOMER", title="受限客户", customer="", status="正常", owner="limited", department="测试部", data={}),
                BusinessRecord(module="finance", serial_no="CODEX-LARGE-LIMITED-FEE", title="limited", customer="受限客户", status="已付款", owner="limited", department="测试部", data={}),
                BusinessRecord(module="finance", serial_no="CODEX-LARGE-OTHER-FEE", title="other", customer="其他客户", status="已付款", owner="other", department="其他部", data={}),
            ])
            await db.flush()
            fees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all())
            limited_fee = next(item for item in fees if item.owner == "limited")
            other_fee = next(item for item in fees if item.owner == "other")
            db.add_all([
                IncomingPayment(receipt_no="CODEX-LARGE-LIMITED-IN", received_date=date.today(), amount=20, payer_name="受限付款方", operator="limited", claimed_customer="受限客户"),
                IncomingPayment(receipt_no="CODEX-LARGE-OTHER-IN", received_date=date.today(), amount=50, payer_name="其他付款方", operator="other", claimed_customer="其他客户"),
                FinanceTransaction(finance_record_id=limited_fee.id, transaction_type="付款", amount=10, transaction_date=date.today(), operator="limited"),
                FinanceTransaction(finance_record_id=other_fee.id, transaction_type="付款", amount=30, transaction_date=date.today(), operator="other"),
            ])
            await db.commit()
            result = await report_large_screen({"username": "limited", "role": "user"}, db)

        self.assertTrue(result["finance"]["amount_visible"])
        self.assertEqual(result["finance"]["income"], 20)
        self.assertEqual(result["finance"]["expense"], 10)

    async def test_asgi_route_applies_dependency_based_authentication(self):
        async with self.sessions() as db:
            async def overridden_db():
                yield db

            async def denied_identity():
                return {"username": "limited", "role": "user"}

            previous = dict(app.dependency_overrides)
            app.dependency_overrides[get_db] = overridden_db
            app.dependency_overrides[current_identity] = denied_identity
            try:
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(f"{settings.api_prefix}/reports/large-screen")
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides.update(previous)

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()

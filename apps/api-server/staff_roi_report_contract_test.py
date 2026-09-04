import asyncio
import csv
import io
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import _staff_roi_report, app, current_identity
from app.models import Base, BusinessRecord, Department, FinanceTransaction, IncomingPayment, User


class StaffRoiReportContractTest(unittest.TestCase):
    def test_settled_income_is_split_by_commission_and_cost_uses_paid_ledger_only(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                department = Department(code="CODEX-ROI", name="ROI测试部", is_active=True)
                other_department = Department(code="CODEX-ROI-OTHER", name="ROI另一部", is_active=True)
                alice = User(username="roi-alice", display_name="Alice", department="ROI测试部", password_hash="x", role="user")
                bob = User(username="roi-bob", display_name="Bob", department="ROI另一部", password_hash="x", role="user")
                charlie = User(username="roi-charlie", display_name="Charlie", department="ROI另一部", password_hash="x", role="user")
                source_fee = BusinessRecord(module="finance", serial_no="CODEX-ROI-SOURCE", title="代理费", status="已审批", data={"amount": 1000, "expense_scope": "律所"})
                session.add_all([department, other_department, alice, bob, charlie, source_fee])
                await session.flush()
                alice_commission = BusinessRecord(module="finance", serial_no="CODEX-ROI-A", title="Alice提成", owner="roi-alice", status="已付款", data={"expense_scope": "内部", "source_fee_id": source_fee.id, "payee": "roi-alice", "amount": 100})
                bob_commission = BusinessRecord(module="finance", serial_no="CODEX-ROI-B", title="Bob提成", owner="roi-bob", status="已付款", data={"expense_scope": "内部", "source_fee_id": source_fee.id, "payee": "roi-bob", "amount": 300})
                charlie_commission = BusinessRecord(module="finance", serial_no="CODEX-ROI-C", title="Charlie提成", owner="roi-charlie", status="待付款", data={"expense_scope": "内部", "source_fee_id": source_fee.id, "payee": "roi-charlie", "amount": 400})
                session.add_all([alice_commission, bob_commission, charlie_commission])
                await session.flush()
                session.add(IncomingPayment(receipt_no="CODEX-ROI-RECEIPT", received_date=date(2026, 9, 2), amount=800, allocated_amount=800, payer_name="测试付款方", status="已分配", operator="admin", allocations=[{"fee_record_id": source_fee.id, "amount": 800}]))
                session.add_all([
                    FinanceTransaction(finance_record_id=alice_commission.id, transaction_type="付款", amount=50, transaction_date=date(2026, 9, 3), operator="admin"),
                    FinanceTransaction(finance_record_id=bob_commission.id, transaction_type="付款", amount=150, transaction_date=date(2026, 9, 3), operator="admin"),
                ])
                await session.commit()

                report = await _staff_roi_report({"username": "admin", "role": "admin", "role_ids": ["admin"]}, session, date(2026, 9, 1), date(2026, 9, 30))
                self.assertEqual(report["total"], 3)
                rows = {item["employee_username"]: item for item in report["items"]}
                self.assertEqual(rows["roi-alice"]["performance"], 100.0)
                self.assertEqual(rows["roi-bob"]["performance"], 300.0)
                self.assertEqual(rows["roi-charlie"]["performance"], 400.0)
                self.assertEqual(rows["roi-alice"]["cost"], 50.0)
                self.assertEqual(rows["roi-bob"]["cost"], 150.0)
                self.assertEqual(rows["roi-charlie"]["cost"], 0.0)
                self.assertEqual(rows["roi-alice"]["roi"], 200.0)
                self.assertEqual(rows["roi-bob"]["roi"], 200.0)
                self.assertIsNone(rows["roi-charlie"]["roi"])
                self.assertEqual(sum(item["performance"] for item in report["items"]), 800.0)
                self.assertEqual(report["definition"]["roi"], "业绩÷成本×100%；成本为零时不计算")

                department_report = await _staff_roi_report({"username": "admin", "role": "admin", "role_ids": ["admin"]}, session, date(2026, 9, 1), date(2026, 9, 30), department.id)
                self.assertEqual(department_report["total"], 1)
                self.assertEqual(department_report["items"][0]["employee_username"], "roi-alice")
                self.assertEqual(department_report["items"][0]["performance"], 100.0)

                # A restricted caller sees only the source fee and Alice's
                # commission record.  Hidden colleagues remain in the split
                # denominator, while their identities and rows never return.
                restricted_scope = [BusinessRecord.id.in_([source_fee.id, alice_commission.id])]
                with patch("app.main._require_record_module_menu", new=AsyncMock()), patch("app.main._allowed_field_keys", new=AsyncMock(return_value={"finance.amount"})), patch("app.main._record_scope_conditions", new=AsyncMock(return_value=restricted_scope)):
                    restricted_report = await _staff_roi_report({"username": "roi-alice", "role": "user"}, session, date(2026, 9, 1), date(2026, 9, 30))
                self.assertEqual(restricted_report["items"], [{
                    "employee": "Alice", "employee_username": "roi-alice", "department": "ROI测试部",
                    "performance": 100.0, "cost": 50.0, "roi": 200.0,
                }])

                async def override_db():
                    yield session
                app.dependency_overrides[get_db] = override_db
                app.dependency_overrides[current_identity] = lambda: {"username": "admin", "role": "admin", "role_ids": ["admin"]}
                try:
                    transport = httpx.ASGITransport(app=app)
                    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                        query = {"start_date": "2026-09-02", "end_date": "2026-09-03", "department_id": department.id}
                        response = await client.get(f"{settings.api_prefix}/reports/staff-roi", params=query)
                        self.assertEqual(response.status_code, 200, response.text)
                        payload = response.json()
                        self.assertEqual(payload["items"], department_report["items"])
                        export = await client.get(f"{settings.api_prefix}/reports/staff-roi/export", params=query)
                        self.assertEqual(export.status_code, 200, export.text)
                        csv_rows = list(csv.DictReader(io.StringIO(export.content.decode("utf-8-sig"))))
                        self.assertEqual(csv_rows, [{"员工": "Alice", "账号": "roi-alice", "部门": "ROI测试部", "业绩": "100.0", "成本": "50.0", "ROI(%)": "200.0"}])
                finally:
                    app.dependency_overrides.clear()

                with self.assertRaises(HTTPException) as failure:
                    await _staff_roi_report({"username": "admin", "role": "admin", "role_ids": ["admin"]}, session, date(2026, 10, 1), date(2026, 9, 1))
                self.assertEqual(failure.exception.status_code, 422)
                with self.assertRaises(HTTPException) as missing_department:
                    await _staff_roi_report({"username": "admin", "role": "admin", "role_ids": ["admin"]}, session, department_id=999)
                self.assertEqual(missing_department.exception.status_code, 422)

                with patch("app.main._require_record_module_menu", new=AsyncMock()), patch("app.main._allowed_field_keys", new=AsyncMock(return_value=set())):
                    with self.assertRaises(HTTPException) as amount_denied:
                        await _staff_roi_report({"username": "roi-alice", "role": "user"}, session)
                self.assertEqual(amount_denied.exception.status_code, 403)
                with patch("app.main._require_record_module_menu", new=AsyncMock(side_effect=HTTPException(status_code=403, detail="报表菜单未授权"))):
                    with self.assertRaises(HTTPException) as report_denied:
                        await _staff_roi_report({"username": "roi-alice", "role": "user"}, session)
                self.assertEqual(report_denied.exception.status_code, 403)
            await engine.dispose()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()

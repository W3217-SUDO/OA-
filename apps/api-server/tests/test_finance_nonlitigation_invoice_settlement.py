"""501099：开票、结算、内部费用按业务类型分诉讼/非诉；只有非诉页面的账号按“给页面＝功能全有”只办非诉单。"""

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance import invoice_operations, settlements
from app.core.finance import (
    nonlitigation_fee_fields, nonlitigation_write_identity, with_invoice_fee_items, with_nonlitigation_fee_fields,
)
from app.database import Base
from app.models import BusinessRecord, User, WorkflowEvent
from app.models_shared import FinanceReviewInput

PERMISSIONS = "app.core.permissions._permission_payload_for_identity"
FINANCE = {"username": "fin", "role": "auditor", "role_ids": ["auditor"], "_finance_scope": "firm", "_business_type": None}
LAWYER = {"username": "lawyer", "role": "user", "role_ids": ["user"], "_finance_scope": "firm", "_business_type": "诉讼"}
IPR_ONLY = {"username": "ipr", "role": "user", "role_ids": ["user"], "_finance_scope": "firm", "_business_type": "非诉",
            "display_name": "知产", "department": "知识产权部"}
IPR_MENUS = {"menu_keys": ["ipr-finance", "ipr-finance-invoice-pending", "ipr-finance-settlement-audit",
                           "ipr-finance-internal-audit"]}


class NonlitigationFinanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            self.fee_ipr = BusinessRecord(module="finance", serial_no="FY-IPR", title="年费", status="已付款", data={
                "business_type": "非诉", "amount": 900, "fee_type": "官费", "fee_type_path": "官费/年费",
                "legacy_record": {"AnnualYear": 3, "AnnualFrom": 3, "AnnualEnd": 5, "IsFirstYear": "F"}})
            self.fee_lit = BusinessRecord(module="finance", serial_no="FY-LIT", title="代理费", status="已付款",
                                          data={"amount": 100, "fee_type": "律师代理费"})
            db.add_all([self.fee_ipr, self.fee_lit,
                        User(username="ipr", display_name="知产", password_hash="x", role="user", department="知识产权部")])
            await db.flush()
            self.invoice_ipr = BusinessRecord(module="invoice", serial_no="FP-IPR", title="非诉发票", status="待审批", owner="x",
                                              data={"business_type": "非诉", "amount": 900, "case_fee_ids": [self.fee_ipr.id]})
            self.invoice_lit = BusinessRecord(module="invoice", serial_no="FP-LIT", title="诉讼发票", status="待审批", owner="x",
                                              data={"amount": 100, "case_fee_ids": [self.fee_lit.id]})
            db.add_all([self.invoice_ipr, self.invoice_lit])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_write_identity_by_account_type(self):
        async with self.sessions() as db:
            # 财务（不带业务类型）两种都能办，身份不变。
            self.assertIs(await nonlitigation_write_identity([self.invoice_ipr, self.invoice_lit], FINANCE, db), FINANCE)
            # 诉讼律师不能办非诉单。
            await nonlitigation_write_identity([self.invoice_lit], LAWYER, db)
            with self.assertRaises(HTTPException) as caught:
                await nonlitigation_write_identity([self.invoice_ipr], LAWYER, db)
            self.assertEqual(caught.exception.status_code, 409)
            with patch(PERMISSIONS, return_value=IPR_MENUS):
                granted = await nonlitigation_write_identity([self.invoice_ipr], IPR_ONLY, db, "ipr-finance-invoice-pending")
                self.assertEqual((granted["role"], granted["action_keys"]), ("admin", ["*"]))
                # 没有对应页面不放行；诉讼单一律拒绝。
                self.assertIs(await nonlitigation_write_identity([self.invoice_ipr], IPR_ONLY, db, "ipr-finance-invoice-company"), IPR_ONLY)
                with self.assertRaises(HTTPException):
                    await nonlitigation_write_identity([self.invoice_lit], IPR_ONLY, db, "ipr-finance-invoice-pending")

    async def test_nonlitigation_only_account_reviews_nonlitigation_invoice_only(self):
        with patch(PERMISSIONS, return_value=IPR_MENUS):
            async with self.sessions() as db:
                result = await invoice_operations.review_invoice_application(
                    self.invoice_ipr.id, FinanceReviewInput(approved=True, comment="ok"), IPR_ONLY, db)
                self.assertEqual(result["status"], "待开票")
                with self.assertRaises(HTTPException) as caught:
                    await invoice_operations.review_invoice_application(
                        self.invoice_lit.id, FinanceReviewInput(approved=True, comment="ok"), IPR_ONLY, db)
                self.assertEqual(caught.exception.status_code, 409)
                events = (await db.execute(WorkflowEvent.__table__.select())).all()
                self.assertEqual(len(events), 1)

    async def test_settlement_gate_opens_only_for_nonlitigation_page(self):
        with patch(PERMISSIONS, return_value=IPR_MENUS):
            async with self.sessions() as db:
                self.assertEqual((await settlements._settlement_role_identity(IPR_ONLY, db, *settlements.SETTLEMENT_AUDIT_PAGES))["role"], "admin")
                self.assertEqual((await settlements._settlement_role_identity(IPR_ONLY, db, *settlements.SETTLEMENT_PAYMENT_PAGES))["role"], "user")
                self.assertEqual((await settlements._settlement_role_identity(LAWYER, db, *settlements.SETTLEMENT_AUDIT_PAGES))["role"], "user")
                self.assertIs(await settlements._settlement_role_identity(FINANCE, db, *settlements.SETTLEMENT_AUDIT_PAGES), FINANCE)
        self.assertEqual(settlements._nonlitigation_tag({"application_id": 7}, {7: "非诉"}), {"business_type": "非诉"})
        self.assertEqual(settlements._nonlitigation_tag({"application_id": 8}, {8: "诉讼"}), {})

    async def test_invoice_lists_by_account_type(self):
        from app.areas.finance.router import list_invoice_applications
        async with self.sessions() as db:
            db.add_all([User(username="admin", display_name="管理员", password_hash="x", role="admin", department="财务部"),
                        User(username="lawyer", display_name="律师", password_hash="x", role="user", department="诉讼部")])
            await db.commit()

        async def numbers(identity, scope="company"):
            async with self.sessions() as db:
                result = await list_invoice_applications(scope=scope, customer="", application_no="", invoice_type="", invoice_title="",
                                                         invoice_no="", invoice_status="", invoiced_from=None, invoiced_to=None,
                                                         case_no="", applicant="", page=1, page_size=50, identity=identity, db=db)
            return sorted(row["serial_no"] for row in result["items"]), result

        admin = {"username": "admin", "role": "admin", "role_ids": ["admin"], "_finance_scope": "firm"}
        self.assertEqual((await numbers({**admin, "_business_type": None}))[0], ["FP-IPR", "FP-LIT"])
        self.assertEqual((await numbers({**admin, "_business_type": "诉讼"}))[0], ["FP-LIT"])
        rows, result = await numbers({**admin, "_business_type": "非诉"})
        self.assertEqual(rows, ["FP-IPR"])
        self.assertEqual(result["items"][0]["fee_items"][0]["annual_year"], 3)
        # 不带财务中心（原入口）结果和原来一样。
        self.assertEqual((await numbers({"username": "admin", "role": "admin", "role_ids": ["admin"]}))[0], ["FP-IPR", "FP-LIT"])
        with patch(PERMISSIONS, return_value=IPR_MENUS):
            self.assertEqual((await numbers({**IPR_ONLY, "role": "admin"}, scope="pending"))[0], ["FP-IPR"])


    async def test_nonlitigation_fee_fields(self):
        fields = nonlitigation_fee_fields(self.fee_ipr.data)
        self.assertEqual(fields, {"expense_subtype": "官费/年费", "annual_year": 3, "annual_from": 3, "annual_end": 5, "is_first_year": "F"})
        # 新系统已有的同义字段优先；恒达演练已写好的键原样返回。
        self.assertEqual(nonlitigation_fee_fields({"expense_subtype": "发明专利年费", "annual_year": 1, "is_first_year": "T",
                                                   "legacy_record": {"AnnualYear": 9}}),
                         {"expense_subtype": "发明专利年费", "annual_year": 1, "annual_from": None, "annual_end": None, "is_first_year": "T"})
        self.assertEqual(nonlitigation_fee_fields({}), {"expense_subtype": "", "annual_year": None, "annual_from": None,
                                                        "annual_end": None, "is_first_year": None})
        rows = with_nonlitigation_fee_fields([{"id": 1, "data": dict(self.fee_ipr.data)}, {"id": 2, "data": dict(self.fee_lit.data)}])
        self.assertEqual(rows[0]["data"]["annual_year"], 3)
        self.assertEqual(rows[1]["data"], self.fee_lit.data)  # 诉讼行原样不动
        async with self.sessions() as db:
            invoices = await with_invoice_fee_items([{"id": 1, "data": dict(self.invoice_ipr.data)},
                                                     {"id": 2, "data": dict(self.invoice_lit.data)}], db)
        self.assertEqual(invoices[0]["fee_items"][0]["annual_end"], 5)
        self.assertEqual((invoices[0]["data"]["expense_subtype"], invoices[0]["data"]["annual_year"]), ("官费/年费", 3))
        self.assertNotIn("fee_items", invoices[1])


if __name__ == "__main__":
    unittest.main()

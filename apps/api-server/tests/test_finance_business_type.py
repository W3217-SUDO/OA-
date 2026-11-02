"""501099：财务数据按业务类型分诉讼/非诉，非诉财务中心固定只看非诉，财务中心可看全部。"""

import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance.incoming_payments import _incoming_owner_conditions
from app.core.finance import _visible_incoming_payment_statement
from app.core.finance_action_permissions import page_granted_finance_actions
from app.core.finance_centers import (
    finance_center_identity, record_business_conditions, require_incoming_center, require_record_center,
)
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, User


def _request(method="GET"):
    return SimpleNamespace(method=method)


class FinanceBusinessTypeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([
                IncomingPayment(receipt_no="R-LIT", received_date=date(2026, 11, 1), amount=10, payer_name="甲",
                                status="待认领", operator="lawyer", finance_scope="firm"),
                IncomingPayment(receipt_no="R-IPR", received_date=date(2026, 11, 1), amount=20, payer_name="乙",
                                status="待认领", operator="ipr", finance_scope="firm", business_type="非诉"),
                IncomingPayment(receipt_no="R-IPR-PLATFORM", received_date=date(2026, 11, 1), amount=40, payer_name="丙",
                                status="待认领", operator="ipr2", finance_scope="platform", business_type="非诉"),
                User(username="ipr", display_name="知产", password_hash="x", role="user", department="知识产权部"),
                User(username="ipr2", display_name="知产二", password_hash="x", role="user", department="知识产权部"),
                User(username="lawyer", display_name="律师", password_hash="x", role="user", department="诉讼部"),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _receipts(self, identity, *extra):
        async with self.sessions() as db:
            statement = await _visible_incoming_payment_statement(identity, db, include_amounts=False)
            return sorted(item.receipt_no for item in (await db.scalars(statement.where(*extra))).all())

    async def test_business_type_filters_receipts_inside_center(self):
        admin = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
        self.assertEqual(await self._receipts({**admin, "_business_type": None}), ["R-IPR", "R-LIT"])
        self.assertEqual(await self._receipts({**admin, "_business_type": "诉讼"}), ["R-LIT"])
        self.assertEqual(await self._receipts({**admin, "_business_type": "非诉"}), ["R-IPR"])

    async def test_owner_scope_mine_and_department(self):
        admin = {"username": "admin", "role": "admin", "_finance_scope": "platform", "_business_type": "非诉"}
        async with self.sessions() as db:
            mine = await _incoming_owner_conditions("mine", {**admin, "username": "ipr", "department": "知识产权部"}, db)
            dept = await _incoming_owner_conditions("dept", {**admin, "username": "ipr", "department": "知识产权部"}, db)
        self.assertEqual(await self._receipts(admin, *mine), [])
        self.assertEqual(await self._receipts(admin, *dept), ["R-IPR-PLATFORM"])

    async def test_actions_refuse_other_business_type(self):
        async with self.sessions() as db:
            litigation = await db.scalar(select(IncomingPayment).where(IncomingPayment.receipt_no == "R-LIT"))
            nonlitigation = await db.scalar(select(IncomingPayment).where(IncomingPayment.receipt_no == "R-IPR"))
        identity = {"username": "ipr", "role": "user", "_finance_scope": "firm", "_business_type": "非诉"}
        require_incoming_center(nonlitigation, identity)
        with self.assertRaises(HTTPException) as caught:
            require_incoming_center(litigation, identity)
        self.assertEqual(caught.exception.status_code, 409)
        require_incoming_center(litigation, {**identity, "_business_type": None})
        fee = BusinessRecord(module="finance", serial_no="FY1", title="", data={"finance_scope": "firm"})
        await require_record_center(fee, {**identity, "_business_type": "诉讼"})
        with self.assertRaises(HTTPException):
            await require_record_center(fee, identity)
        contract = BusinessRecord(module="contract", serial_no="HT1", title="", data={})
        await require_record_center(contract, identity)

    async def test_record_conditions_keep_unmarked_rows_as_litigation(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(module="finance", serial_no="FY-LIT", title="", data={}),
                BusinessRecord(module="finance", serial_no="FY-IPR", title="", data={"business_type": "非诉"}),
                BusinessRecord(module="contract", serial_no="HT-SHARED", title="", data={}),
            ])
            await db.commit()
            for business, expected in (("诉讼", ["FY-LIT", "HT-SHARED"]), ("非诉", ["FY-IPR", "HT-SHARED"]), (None, ["FY-IPR", "FY-LIT", "HT-SHARED"])):
                rows = (await db.scalars(select(BusinessRecord.serial_no).where(
                    *record_business_conditions({"_business_type": business})))).all()
                self.assertEqual(sorted(rows), expected)

    async def test_center_identity_by_menu(self):
        async def resolve(menus, finance_scope, business_type, role="user", actual_role=None):
            identity = {"username": "u", "role": role, "_actual_role": actual_role or role, "_actual_role_ids": [actual_role or role]}
            with patch("app.core.permissions._permission_payload_for_identity", return_value={"menu_keys": menus}):
                return await finance_center_identity(_request(), finance_scope, business_type, identity, None)

        ipr_only = ["ipr", "ipr-finance", "ipr-finance-receipts", "ipr-finance-receipts-mine"]
        self.assertEqual((await resolve(ipr_only, "firm", "非诉"))["_business_type"], "非诉")
        for scope, business in (("firm", None), ("firm", "全部"), ("firm", "诉讼"), ("platform", "非诉")):
            with self.assertRaises(HTTPException) as caught:
                await resolve(ipr_only, scope, business)
            self.assertEqual(caught.exception.status_code, 403)
        # 页面访问临时当管理员时仍按真实菜单：只有非诉菜单的账号不能借此看诉讼。
        for business in (None, "诉讼", "全部"):
            with self.assertRaises(HTTPException):
                await resolve(ipr_only, "firm", business, role="admin", actual_role="user")
        self.assertEqual((await resolve(ipr_only, "firm", "非诉", role="admin", actual_role="user"))["_business_type"], "非诉")
        # 诉讼律师（没有回款管理页、没有非诉菜单）不看非诉：切“非诉”“全部”也只给诉讼。
        lawyer = ["finance", "finance-receipts", "finance-receipts-claim", "finance-receipts-pending"]
        for business in (None, "全部", "非诉"):
            self.assertEqual((await resolve(lawyer, "firm", business, role="admin", actual_role="user"))["_business_type"], "诉讼")
        # 财务、管理员在财务中心不少看：可切诉讼、非诉、全部。
        finance = ["finance", "finance-receipts", "finance-receipts-manage"]
        self.assertIsNone((await resolve(finance, "firm", "全部"))["_business_type"])
        self.assertIsNone((await resolve(finance, "firm", None))["_business_type"])
        self.assertEqual((await resolve(finance, "firm", "非诉"))["_business_type"], "非诉")
        self.assertEqual((await resolve([], "platform", "诉讼", role="admin"))["_business_type"], "诉讼")

    def test_department_receipt_page_carries_receipt_management_switches(self):
        self.assertEqual(
            page_granted_finance_actions(["ipr-finance-receipts-dept"]),
            page_granted_finance_actions(["finance-receipts-manage"]),
        )
        self.assertEqual(page_granted_finance_actions(["ipr-finance-receipts-mine"]), [])
        for page in ("payment-package-manage", "payment-audit", "invoice-pending", "internal-fee-audit"):
            self.assertEqual(page_granted_finance_actions([f"ipr-finance-{page}"]), page_granted_finance_actions([f"finance-{page}"]))


if __name__ == "__main__":
    unittest.main()

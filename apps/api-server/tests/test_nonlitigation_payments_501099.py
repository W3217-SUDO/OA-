"""501099 付款管理 6 个页面：财务看全部、诉讼律师只看诉讼、只有非诉菜单的账号只能办非诉。"""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance import internal_payments
from app.areas.finance.payment_business import (
    filter_payment_business, payment_actor, require_payment_business, tag_nonlitigation,
)
from app.core.finance_centers import record_business_conditions
from app.database import Base
from app.models import BusinessRecord

# 三种账号进付款页面后的身份（finance_center_identity 已算好 _business_type）。
FINANCE = {"username": "cw", "role": "manager", "role_ids": ["manager"], "_actual_role_ids": ["manager"],
           "_finance_scope": "firm", "_business_type": None}
LAWYER = {"username": "lawyer", "role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"],
          "_finance_scope": "firm", "_business_type": "诉讼"}
IPR_ONLY = {"username": "ipr", "role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"],
            "_finance_scope": "firm", "_business_type": "非诉"}
MENUS = {"cw": ["finance-payment-audit"], "lawyer": ["finance-payment-mine"],
         "ipr": ["ipr-finance-payment-mine", "ipr-finance-payment-audit", "ipr-finance-payment-package-manage"]}


def _payload(identity, db):
    return {"menu_keys": MENUS[identity["username"]]}


def record(module, serial, business=None, **data):
    return BusinessRecord(module=module, serial_no=serial, title=serial, customer="客户", status="待核销",
                          owner="admin", department="上海",
                          data={**data, **({"business_type": business} if business else {})})


class NonlitigationPaymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            self.lit_payment = record("contract_payment", "CP-LIT")
            self.ipr_payment = record("contract_payment", "CP-IPR", "非诉")
            self.lit_package = record("finance_package", "PK-LIT", fee_type="普通付款包")
            self.ipr_package = record("finance_package", "PK-IPR", "非诉", fee_type="普通付款包")
            db.add_all([self.lit_payment, self.ipr_payment, self.lit_package, self.ipr_package])
            await db.commit()
        self.permission = patch("app.core.permissions._permission_payload_for_identity", AsyncMock(side_effect=_payload))
        self.permission.start()

    async def asyncTearDown(self):
        self.permission.stop()
        await self.engine.dispose()

    async def test_only_nonlitigation_page_account_is_elevated(self):
        async with self.sessions() as db:
            self.assertIs(await payment_actor(FINANCE, db, "audit"), FINANCE)
            self.assertIs(await payment_actor(LAWYER, db, "audit"), LAWYER)
            actor = await payment_actor(IPR_ONLY, db, "audit")
            self.assertEqual(actor["role"], "admin")
            self.assertTrue(actor["_nonlitigation_payment_actor"])
            # 没给这个页面就不放行。
            self.assertIs(await payment_actor(IPR_ONLY, db, "writeoff"), IPR_ONLY)

    async def test_write_requires_matching_business_type(self):
        async with self.sessions() as db:
            actor = await payment_actor(IPR_ONLY, db, "audit")
        require_payment_business(self.ipr_payment, actor)
        with self.assertRaises(HTTPException) as error:
            require_payment_business(self.lit_payment, actor)
        self.assertEqual(error.exception.status_code, 409)
        require_payment_business(self.lit_payment, LAWYER)
        with self.assertRaises(HTTPException):
            require_payment_business(self.ipr_payment, LAWYER)
        # 财务不带业务类型：两种都能办，和原来一样。
        require_payment_business(self.lit_payment, FINANCE)
        require_payment_business(self.ipr_payment, FINANCE)

    async def test_lists_filter_by_business_type(self):
        rows = [self.lit_payment, self.ipr_payment, self.lit_package, self.ipr_package]
        async with self.sessions() as db:
            self.assertEqual(len(await filter_payment_business(rows, FINANCE, db)), 4)
            self.assertEqual({row.serial_no for row in await filter_payment_business(rows, LAWYER, db)}, {"CP-LIT", "PK-LIT"})
            self.assertEqual({row.serial_no for row in await filter_payment_business(rows, IPR_ONLY, db)}, {"CP-IPR", "PK-IPR"})
            # 请款单查询、付款包列表用的 SQL 条件：分页总数按类型算。
            for identity, expected in ((FINANCE, 2), (LAWYER, 1), (IPR_ONLY, 1)):
                found = (await db.scalars(select(BusinessRecord.serial_no).where(
                    BusinessRecord.module == "contract_payment",
                    *record_business_conditions(identity, allow_shared_contract=False),
                ))).all()
                self.assertEqual(len(found), expected, identity["username"])

    async def test_payment_package_list_endpoint(self):
        async def dicts(rows, identity, db):
            return [{"id": row.id, "serial_no": row.serial_no, "data": dict(row.data or {})} for row in rows]

        async def displays(items, db):
            return items

        with patch("app.core.permissions._record_scope_conditions", AsyncMock(return_value=[])), \
                patch("app.core.permissions._record_dicts_for_identity", AsyncMock(side_effect=dicts)), \
                patch.object(internal_payments, "apply_finance_person_displays", AsyncMock(side_effect=displays)):
            async with self.sessions() as db:
                for identity, expected in ((FINANCE, {"PK-LIT", "PK-IPR"}), (LAWYER, {"PK-LIT"}), (IPR_ONLY, {"PK-IPR"})):
                    result = await internal_payments.list_internal_payment_packages(
                        page=1, page_size=None, status_filter="", page_id="", package_scope="ordinary", package_no="",
                        payee="", payment_date_from=None, payment_date_to=None, identity=identity, db=db)
                    self.assertEqual({item["serial_no"] for item in result["items"]}, expected, identity["username"])
                    self.assertEqual(result["total"], len(expected))

    def test_new_records_inherit_nonlitigation_only_when_all_sources_are(self):
        self.assertEqual(tag_nonlitigation({"a": 1}, self.ipr_payment)["business_type"], "非诉")
        self.assertNotIn("business_type", tag_nonlitigation({"a": 1}, self.ipr_payment, self.lit_payment))
        self.assertNotIn("business_type", tag_nonlitigation({"a": 1}))


if __name__ == "__main__":
    unittest.main()

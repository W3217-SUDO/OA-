"""陶威 2026-10-31 新旧系统对齐：付款包列表按旧系统补列、内部付款包按收款人筛选、银行原始流水只读页。"""
import unittest
from datetime import datetime

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance import bank_flows, internal_payments
from app.core import soft_delete
from app.core.constants import DEFAULT_HIDDEN_MENU_KEYS, DEFAULT_SYSTEM_MENUS, ROLE_TREE_HIDDEN_MENU_KEYS
from app.core.dependencies import current_identity, get_db
from app.database import Base
from app.legacy_schema import LEGACY_METADATA
from app.models import BusinessRecord, SystemParameter, User

ADMIN = {"username": "fadmin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "管理员", "department": "财务部", "action_keys": ["*"]}


class LegacyBankFlowAndPackagesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(lambda sync: LEGACY_METADATA.tables["FAM_AR_Payment_GDICBC"].create(sync, checkfirst=True))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add(User(username="fadmin", display_name="管理员", password_hash="x", department="财务部", role="admin"))
            db.add(User(username="gongyq", display_name="龚永强", password_hash="x", department="调查取证部", role="staff"))
            db.add(SystemParameter(category="payment_type", code="LEGACY-PAYMENT-3", name="公证机构",
                                   extra={"nature": "官费", "legacy_payment_type_name": "公证费", "payee": "公证机构"}))
            fee = BusinessRecord(module="finance", serial_no="LIP-L-1", title="内部费用", owner="fanyuxing", department="调查取证部",
                                 status="已付款", data={"fee_type": "内部费用", "payee": "gongyq", "amount": 100})
            db.add(fee)
            await db.flush()
            db.add(BusinessRecord(module="finance_package", serial_no="P1", title="付款包 P1", owner="shenhe", department="诉讼四部",
                                  status="已付款", data={"legacy_kind": "ap_packing", "fee_type": "普通付款包", "fee_ids": [11, 12],
                                                         "amount": 300, "total_amount": 300, "payee": "公证机构",
                                                         "legacy_record": {"PaymentTypeId": 3, "Remark": "老备注"}}))
            db.add(BusinessRecord(module="finance_package", serial_no="P2", title="内部付款包 P2", owner="shenhe", department="调查取证部",
                                  status="已付款", data={"legacy_kind": "internal_packing", "fee_type": "内部费用付款包",
                                                         "fee_ids": [fee.id], "amount": 100, "total_amount": 100, "legacy_record": {}}))
            db.add(BusinessRecord(module="finance_package", serial_no="P3", title="内部付款包 P3", owner="shenhe", department="调查取证部",
                                  status="待核销", data={"legacy_kind": "internal_packing", "fee_type": "内部费用付款包",
                                                         "fee_ids": [], "amount": 50, "total_amount": 50, "legacy_record": {}}))
            await db.commit()
            table = LEGACY_METADATA.tables["FAM_AR_Payment_GDICBC"]
            base = {"CompanyId": 1, "ICBC_BankNo": "1001", "PaymentModeName": "贷", "Payer_BankNo": "4080", "Payer_BankName": "309",
                    "KeyWords": "案款", "Usage": "", "Remark": "附言", "Operator": "shenhe", "OperatorTime": datetime(2026, 10, 20),
                    "FileName": "a.xlsx", "CreateUser": "shenhe", "CreateTime": datetime(2026, 10, 20), "ChangeTime": datetime(2026, 10, 20),
                    "ChangeUser": "shenhe", "GroupId": 10}
            await db.execute(table.insert(), [
                {**base, "PaymentId": 1, "SequenceNo": "1", "CashedDate": datetime(2026, 10, 20), "CashedAmount": 25500,
                 "Payer_Name": "味思原徐州食品有限公司", "IsActived": "T", "Status": 2},
                {**base, "PaymentId": 2, "SequenceNo": "2", "CashedDate": datetime(2026, 9, 1), "CashedAmount": 100,
                 "Payer_Name": "某公司", "IsActived": "F", "Status": 1},
            ])
            await db.commit()
        app = FastAPI()
        app.include_router(internal_payments.router)
        app.include_router(bank_flows.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ADMIN)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    def test_menus_follow_legacy_layout(self):
        menus = {key: (parent, label) for key, parent, label, *_ in DEFAULT_SYSTEM_MENUS}
        self.assertNotIn("finance-payment-package-manage", DEFAULT_HIDDEN_MENU_KEYS)
        self.assertNotIn("finance-payment-package-manage", ROLE_TREE_HIDDEN_MENU_KEYS)
        self.assertEqual(menus["finance-receipts-gdicbc"], ("finance-receipts", "回款(国定工行)"))
        self.assertEqual(menus["finance-receipts-bank-flow"], ("finance-receipts", "银行原始流水"))
        self.assertEqual(menus["platform-finance-overview-gdicbc"][1], "回款(国定工行)")

    async def test_ordinary_package_list_has_legacy_columns(self):
        response = await self.client.get("/api/v1/finance/payment-packages", params={"package_scope": "ordinary", "page_size": 20})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["items"][0]["data"]
        self.assertEqual((data["fee_count"], data["payment_nature"], data["payment_type_name"], data["remark"]), (2, "官费", "公证费", "老备注"))

    async def test_imported_internal_package_shows_and_filters_by_line_payee(self):
        response = await self.client.get("/api/v1/finance/payment-packages", params={"package_scope": "internal", "status": "已付款", "page_size": 20})
        items = response.json()["items"]
        self.assertEqual([item["serial_no"] for item in items], ["P2"])
        self.assertEqual(items[0]["data"]["payee"], "gongyq")
        by_name = await self.client.get("/api/v1/finance/payment-packages", params={"package_scope": "internal", "payee": "龚永强", "page_size": 20})
        self.assertEqual([item["serial_no"] for item in by_name.json()["items"]], ["P2"])
        self.assertEqual(by_name.json()["total"], 1)

    async def test_bank_flows_read_only_like_legacy_list(self):
        response = await self.client.get("/api/v1/finance/bank-flows", params={"bank": "gdicbc"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["total"], 1)
        row = body["items"][0]
        self.assertEqual((row["Payer_Name"], row["CashedAmount"], row["status"], row["group"]), ("味思原徐州食品有限公司", 25500.0, "已导入", "律所"))
        self.assertEqual([column["label"] for column in body["columns"]][:4], ["本方账号", "交易时间", "交易类型", "贷方发生额"])
        everything = await self.client.get("/api/v1/finance/bank-flows", params={"bank": "gdicbc", "include_deleted": True, "date_to": "2026-09-30"})
        self.assertEqual([item["status"] for item in everything.json()["items"]], ["已删除"])
        missing = await self.client.get("/api/v1/finance/bank-flows", params={"bank": "icbc"})
        self.assertEqual(missing.status_code, 404)

    async def test_bank_flow_table_outside_manifest_is_reflected(self):
        # 招行流水表不在镜像表清单里（迁移时另建），按库里的表结构读。
        async with self.engine.begin() as connection:
            await connection.exec_driver_sql(
                'CREATE TABLE "FAM_AR_Payment_CMB" ("PaymentId" INTEGER PRIMARY KEY, "TransactionType" TEXT, "TransactionDate" DATETIME, '
                '"Payer_Account_No" TEXT, "Payer_Name" TEXT, "TradeAmount" NUMERIC, "TransactionNo" TEXT, "Reference" TEXT, "Purpose" TEXT, '
                '"Remark" TEXT, "Remarks" TEXT, "IsActived" TEXT, "Status" INTEGER, "FileName" TEXT, "Operator" TEXT, "CreateTime" DATETIME, "GroupId" INTEGER)')
            await connection.exec_driver_sql(
                """INSERT INTO "FAM_AR_Payment_CMB" VALUES (1, 'IBPS对公提回贷记', '2026-09-02 10:29:29', '1111', '南通瑞圣拓纺织服饰有限公司', 15000, 'C06', '', '', '', '', 'T', 2, 'a.xlsx', 'cw', '2026-09-03 11:09:06', 10)""")
        response = await self.client.get("/api/v1/finance/bank-flows", params={"bank": "cmb"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["items"][0]["Payer_Name"], "南通瑞圣拓纺织服饰有限公司")

    async def test_deleted_packages_hidden_unless_asked(self):
        async with self.sessions() as db:
            db.add(BusinessRecord(module="finance_package", serial_no="LAP-PKG-1", title="付款包", owner="shenhe", department="诉讼四部",
                                  status="已删除", data={"legacy_kind": "ap_packing", "fee_type": "普通付款包", "fee_ids": []}))
            await db.commit()
        listed = await self.client.get("/api/v1/finance/payment-packages", params={"package_scope": "ordinary", "page_size": 20})
        self.assertEqual([item["serial_no"] for item in listed.json()["items"]], ["P1"])
        deleted = await self.client.get("/api/v1/finance/payment-packages", params={"package_scope": "ordinary", "status": "已删除", "page_size": 20})
        self.assertEqual([item["serial_no"] for item in deleted.json()["items"]], ["LAP-PKG-1"])


if __name__ == "__main__":
    unittest.main()

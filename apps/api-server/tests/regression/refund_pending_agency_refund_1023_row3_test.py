"""10.23 第3行：控制台“待退费”与案件“退费”列按有效律师代理费（退费）计算。

数据仿生产 GDMS2400918：一审诉讼费 100 先后两次法院退费各 50，其中第二次生成的律师代理费（退费）
已删除但退费单仍是草稿；官费 500 退费 200；二审诉讼费 500 的律师代理费（退费）150 已撤回。
用户确认：退费金额 = 有效律师代理费（退费）合计；案件“退费”列同口径显示；已撤回不显示；
删除/撤回律师代理费（退费）时作废对应草稿退费单；旧案费用自带退费金额照旧。
"""

import unittest

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1023-3-"
ADMIN = {"username": f"{PREFIX}admin", "role": "admin", "display_name": "管理者", "department": "测试部"}


class RefundPendingAgencyRefundRow3Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department="测试部", role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no=f"{PREFIX}CASE", title="第3行案件", customer="测试客户", status="一审立案受理",
                                  owner=ADMIN["username"], department="测试部",
                                  data={"case_type": "民事争议", "case_team_usernames": [ADMIN["username"]], "plaintiff": "原告", "opponent": "被告"})
            legacy_case = BusinessRecord(module="case", serial_no=f"{PREFIX}OLD", title="旧案", customer="旧客户", status="一审立案受理",
                                         owner=ADMIN["username"], department="测试部", data={"case_type": "民事争议", "case_team_usernames": [ADMIN["username"]]})
            db.add_all([case, legacy_case])
            await db.flush()
            self.case_id = case.id

            def fee(code, fee_type, subtype, amount, status_value="草稿", **extra):
                return BusinessRecord(module="finance", serial_no=f"{PREFIX}{code}", title=subtype, customer="测试客户", status=status_value,
                                      owner=ADMIN["username"], department="测试部",
                                      data={"case_id": case.id, "case_record_id": case.id, "case_no": case.serial_no, "expense_scope": "律所",
                                            "fee_type": fee_type, "expense_subtype": subtype, "amount": amount, **extra})

            self.first = fee("FIRST", "官方费用", "一审诉讼费", 100)
            self.official = fee("OFFICIAL", "官方费用", "官费", 500)
            self.second = fee("SECOND", "官方费用", "二审诉讼费", 500)
            db.add_all([self.first, self.official, self.second])
            await db.flush()

            def refund(code, source, amount):
                return BusinessRecord(module="refund", serial_no=f"{PREFIX}TF-{code}", title="法院退费", customer="测试客户", status="草稿",
                                      owner=ADMIN["username"], department="测试部",
                                      data={"fee_record_id": source.id, "case_no": case.serial_no, "amount": amount})

            self.refund_a = refund("A", self.first, 50)
            self.refund_b = refund("B", self.first, 50)
            self.refund_c = refund("C", self.official, 200)
            self.refund_d = refund("D", self.second, 150)
            db.add_all([self.refund_a, self.refund_b, self.refund_c, self.refund_d])
            await db.flush()

            def agency(code, source, refund_row, amount, status_value="草稿"):
                return fee(code, "代理费", "律师代理费(退费)", amount, status_value, refund_fee=True,
                           source_fee_id=source.id, refund_record_id=refund_row.id)

            self.agency_a = agency("AG-A", self.first, self.refund_a, 50)
            self.agency_b = agency("AG-B", self.first, self.refund_b, 50, "已删除")
            self.agency_c = agency("AG-C", self.official, self.refund_c, 200)
            self.agency_d = agency("AG-D", self.second, self.refund_d, 150, "已撤回")
            self.legacy_fee = BusinessRecord(module="finance", serial_no=f"{PREFIX}LEGACY", title="旧案诉讼费", customer="旧客户", status="已付款",
                                             owner=ADMIN["username"], department="测试部",
                                             data={"case_id": legacy_case.id, "case_no": legacy_case.serial_no, "fee_type": "官方费用",
                                                   "expense_subtype": "一审诉讼费", "amount": 800, "refund_requested_amount": 300, "refunded_amount": 0,
                                                   "legacy_case_fee_id": 1023301})
            db.add_all([self.agency_a, self.agency_b, self.agency_c, self.agency_d, self.legacy_fee])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row3-1023.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _pending(self):
        response = await self.client.get(f"{API}/finance/case-fees/refunds", params={"page_size": 200})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        return {row["id"]: row["data"]["refund_requested_amount"] for row in response.json()["items"]}

    async def _case_refund_column(self):
        response = await self.client.get(f"{API}/cases/{self.case_id}/relations", params={"include": "fees"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        return {row["id"]: row["data"] for row in response.json()["fees"]}

    async def test_pending_refund_counts_only_active_agency_refunds(self):
        pending = await self._pending()
        self.assertEqual(pending.get(self.first.id), 50, "已删除的律师代理费（退费）对应退费单不计入")
        self.assertEqual(pending.get(self.official.id), 200)
        self.assertNotIn(self.second.id, pending, "律师代理费（退费）已撤回的不出现在待退费")
        self.assertEqual(pending.get(self.legacy_fee.id), 300, "旧案费用自带退费金额照旧")

    async def test_case_refund_column_matches_pending_refund(self):
        fees = await self._case_refund_column()
        self.assertEqual(fees[self.first.id].get("refund_amount"), 50)
        self.assertEqual(fees[self.official.id].get("refund_amount"), 200)
        self.assertFalse(fees[self.first.id].get("refund_display_suppressed"))
        self.assertFalse(fees[self.second.id].get("refund_amount"))

    async def test_deleting_agency_refund_voids_its_draft_refund(self):
        response = await self.client.delete(f"{API}/finance/fees/{self.agency_c.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.text)
        async with self.sessions() as db:
            refund = await db.get(BusinessRecord, self.refund_c.id)
            self.assertEqual(refund.status, "已作废")
            self.assertEqual(refund.data["voided_with_fee_id"], self.agency_c.id)
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.refund_c.id))).all()
            self.assertTrue(any(event.action == "退费单随律师代理费（退费）作废" for event in events))
        self.assertNotIn(self.official.id, await self._pending())


if __name__ == "__main__":
    unittest.main()

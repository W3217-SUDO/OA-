"""控制台数字口径（2026-10-23 用户确认）：首页卡片数字 = 点进去那个列表的总数。

覆盖：待审核归档（状态“归档审核”、未指定审核人，管理员看全部）、待审核预损费用（= 归档“亏损内审”标签）、
待审批官方费用（= 请款单审批：合同付款“待审批”）、待审批内部费用、待审批结算费用、待归档费用；
未到官费金额排除已删除/已撤回费用，从控制台进入的应收明细只列官费未到账>0 并给出合计。
"""

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app, dashboard
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1023-DASH-"
IDENTITY = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "测试部"}


class DashboardCountsMatchListsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理者", department="测试部", password_hash="x", role="admin", is_active=True))

            def record(module, code, status, owner="other", **data):
                return BusinessRecord(module=module, serial_no=f"{PREFIX}{code}", title=code, customer=f"{PREFIX}客户",
                                      status=status, owner=owner, department="测试部", data=data)

            db.add_all([
                record("case", "ARCH-1", "归档审核", archive_submitter="other"),
                record("case", "ARCH-2", "归档审核", archive_submitter="other"),
                record("case", "ARCH-OLD", "待归档审核", archive_submitter="other"),
                record("case", "LOSS-1", "亏损内审", archive_submitter="other"),
                record("case", "LOSS-2", "亏损审核", archive_submitter="other"),
                record("contract_payment", "CP-1", "待审批"),
                record("contract_payment", "CP-2", "待审批"),
                record("contract_payment", "CP-3", "已审批"),
                record("finance_settlement", "ST-1", "待审批", finance_scope="firm"),
            ])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://dash-1023.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _todos(self):
        async with self.sessions() as db:
            result = await dashboard(IDENTITY, db, section="todos")
        cards = {}
        for row in result["todos"]:
            cards[row[0]] = row[1]
            cards[row[3]] = row[4]
        return cards

    async def _total(self, method, path, **kwargs):
        response = await self.client.request(method, f"{API}{path}", **kwargs)
        self.assertEqual(response.status_code, 200, (path, response.text))
        return response.json()["total"]

    async def test_cards_equal_click_through_list_totals(self):
        cards = await self._todos()
        self.assertNotIn("待审批归档费用", cards, "卡片已改名为“待归档费用”")
        pending = await self._total("POST", "/cases/archive/search", json={"view": "pending", "page": 1, "page_size": 15})
        loss_internal = await self._total("POST", "/cases/archive/search", json={"view": "loss_internal", "page": 1, "page_size": 15})
        self.assertEqual(cards["待审核归档"], pending)
        self.assertEqual(cards["待审核归档"], 3, "“归档审核”与“待归档审核”都计入；亏损内审/亏损审核不计入")
        self.assertEqual(cards["待审核预损费用"], loss_internal)
        self.assertEqual(cards["待审核预损费用"], 1)
        payment = (await self._total("GET", "/records", params={"module": "finance", "finance_view": "external", "record_status": "待审批", "page_size": 1})
                   + await self._total("GET", "/records", params={"module": "contract_payment", "record_status": "待审批", "page_size": 1}))
        self.assertEqual(cards["待审批官方费用"], payment)
        self.assertEqual(cards["待审批官方费用"], 2)
        self.assertEqual(cards["待审批内部费用"], await self._total(
            "GET", "/finance/internal-review-requests", params={"kind": "other", "page": 1, "page_size": 15}))
        self.assertEqual(cards["待审批结算费用"], await self._total(
            "GET", "/finance/general-settlements/applications", params={"status": "待审批", "finance_scope": "firm", "page": 1, "page_size": 10}))
        self.assertEqual(cards["待归档费用"], await self._total(
            "GET", "/finance/archive-settlements/pending", params={"finance_scope": "firm", "page": 1, "page_size": 10}))


if __name__ == "__main__":
    unittest.main()

"""501617（陶国南 11-06“按照老系统的一样”）：专利年费左侧“年费清单”单独授权，默认谁都看不到；年费监控不受影响。"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import IPR_ANNUAL_FEE_LIST_ACTION, PAGE_GRANTED_ACTION_CODES, SYSTEM_ACTION_BY_CODE
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "上海分所"}
# 有“专利年费”页面被提升成 admin 的普通员工
ELEVATED = {"username": "clerk", "role": "admin", "role_ids": ["admin"], "_actual_role": "user", "_actual_role_ids": ["user"],
            "display_name": "流程", "department": "上海分所"}


class AnnualFeeListPermissionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理者", department="上海分所", password_hash="x", role="admin", is_active=True))
            db.add(User(username="clerk", display_name="流程", department="上海分所", password_hash="x", role="user", is_active=True))
            await db.commit()
        app.dependency_overrides[get_db] = self._db
        self.identity = ADMIN
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fee.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()

    def test_code_is_separately_granted_under_annual_fee_page(self):
        self.assertEqual(SYSTEM_ACTION_BY_CODE[IPR_ANNUAL_FEE_LIST_ACTION]["menu_key"], "ipr-patent-annual-fee")
        self.assertNotIn(IPR_ANNUAL_FEE_LIST_ACTION, PAGE_GRANTED_ACTION_CODES, "给了页面不自动带上")

    async def test_list_group_hidden_without_grant(self):
        groups = {item["group"] for item in (await self.client.get(f"{API}/ipr/annual-fee-monitor/summary")).json()["items"]}
        self.assertEqual(groups, {"年费清单", "年费监控"}, "系统管理员都能看到")

        self.identity = ELEVATED
        response = await self.client.get(f"{API}/ipr/annual-fee-monitor/summary")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({item["group"] for item in response.json()["items"]}, {"年费监控"}, "页面提升的 admin 不算，没单独授权只看年费监控")
        year_view = next(item["key"] for item in (await self._admin_summary()) if item["group"] == "年费清单")
        blocked = await self.client.get(f"{API}/ipr/annual-fee-monitor/items", params={"view": year_view})
        self.assertEqual(blocked.status_code, 403, blocked.text)
        self.assertEqual((await self.client.get(f"{API}/ipr/annual-fee-monitor/items", params={"view": "within-6"})).status_code, 200)

    async def _admin_summary(self):
        saved, self.identity = self.identity, ADMIN
        try:
            return (await self.client.get(f"{API}/ipr/annual-fee-monitor/summary")).json()["items"]
        finally:
            self.identity = saved


if __name__ == "__main__":
    unittest.main()

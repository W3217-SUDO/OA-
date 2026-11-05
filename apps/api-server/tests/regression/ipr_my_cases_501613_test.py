"""501613（范文玲 11-05）：知识产权中心“我的案件”——按我在案件里的角色分组、失效单列、筛选和各组数量。

案件管理人 business_owner 迁移时存账号，要按账号也认（原“我是案件管理人”按姓名匹配，查不到）。
"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity

API = settings.api_prefix
ME = {"username": "fwl613", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"], "display_name": "范文玲", "department": "知产部"}


def case(no, status, **data):
    return BusinessRecord(module="ipr_case", serial_no=no, title=f"案件{no}", customer=data.pop("customer", "客户甲"), status=status,
                          owner=data.pop("owner", "someone"), department="知产部",
                          data={"case_kind": "商标", "case_category": "non_litigation", **data})


class IprMyCases501613Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="fwl613", display_name="范文玲", department="知产部", role="admin", password_hash="x", is_active=True))
            db.add_all([
                case("M1", "年费监控", business_owner="fwl613", applicant="上海甲公司", trademark_ids="35", deadline="2027-01-01T00:00:00"),
                case("M2", "受理", case_origin_people_name="范文玲", agent="范文玲"),
                case("M3", "受理", writer="范文玲", customer="客户乙"),
                case("M4", "失效", business_owner="fwl613"),
                case("M5", "受理", owner="fwl613"),
                case("M6", "受理", case_officer="fwl613"),
                case("X1", "受理", business_owner="other", agent="别人"),
                case("X2", "失效", business_owner="other"),
            ])
            await db.commit()
        self.previous = dict(app.dependency_overrides)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ME)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr613.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def serials(self, **params):
        response = await self.client.get(f"{API}/ipr/cases", params={"page_size": 100, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return sorted(item["serial_no"] for item in response.json()["items"])

    async def test_groups_match_by_account_or_name_and_exclude_invalid(self):
        self.assertEqual(await self.serials(role_view="my:business_owner"), ["M1"], "案件管理人按账号认，失效的 M4 不在这组")
        self.assertEqual(await self.serials(role_view="my:source_person"), ["M2"])
        self.assertEqual(await self.serials(role_view="my:procurator"), ["M2"])
        self.assertEqual(await self.serials(role_view="my:copywriter"), ["M3"])
        self.assertEqual(await self.serials(role_view="my:mine"), ["M1", "M2", "M3", "M5", "M6"], "任一角色、处理人或我新建的，不含失效")
        self.assertEqual(await self.serials(role_view="invalid"), ["M4", "X2"], "失效案件：能看的案件里阶段为失效的")
        self.assertEqual(await self.serials(role_view="business_owner"), ["M1", "M4"], "原“我是案件管理人”菜单修好，仍含失效")

    async def test_extra_filters_and_counts(self):
        self.assertEqual(await self.serials(role_view="my:mine", applicant="甲公司"), ["M1"])
        self.assertEqual(await self.serials(role_view="my:mine", trademark_class="35"), ["M1"])
        self.assertEqual(await self.serials(role_view="my:mine", customer="客户乙"), ["M3"])
        self.assertEqual(await self.serials(role_view="my:mine", case_no="M5"), ["M5"])
        counts = (await self.client.get(f"{API}/ipr/cases/my-counts")).json()
        self.assertEqual(counts, {"business_owner": 1, "source_person": 1, "procurator": 1, "copywriter": 1, "mine": 5, "invalid": 2})


if __name__ == "__main__":
    unittest.main()

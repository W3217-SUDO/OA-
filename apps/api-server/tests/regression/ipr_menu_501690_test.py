"""501690（思法汇成 11-07）：知产非诉分成 我的案件、全部案件、流程事务；只持有“我的案件”的账号只看自己相关的非诉案件。"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import DEFAULT_HIDDEN_MENU_KEYS, DEFAULT_SYSTEM_MENUS, ROLE_TREE_HIDDEN_MENU_KEYS
from app.core.data_scope_gate import GATE_CONFIG_KEY, is_personal_page, reset_gate_cache
from app.core.permissions import _expand_menu_permission_keys
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemConfig, User
from app.security import current_identity

API = settings.api_prefix
MY_PAGES = ("ipr-source-person", "ipr-business-owner", "ipr-procurator", "ipr-copywriter", "ipr-my-mine", "ipr-my-invalid")
# 财务人员角色现在存的知产非诉授权（生产 11-07）：不能因为这次改菜单多出“全部案件”。
FINANCE_STORED = ["ipr", "ipr-patent", "ipr-trademark", "ipr-review", "ipr-office-files", "ipr-custom-file-import", "ipr-source-person",
                  "ipr-procurator", "ipr-copywriter", "ipr-officer", "ipr-business-owner", "ipr-case-reboot", "ipr-case-files",
                  "ipr-patent-annual-fee", "ipr-my-cases"]


def who(*menu_keys, actual="user", external=False):
    return {"username": "me690", "display_name": "我", "department": "知产部", "role": "admin", "role_ids": ["admin", actual],
            "_actual_role": actual, "_actual_role_ids": [actual], "_page_menu_capability": True, "_page_scope_actual": False,
            "_external_account": external, "menu_keys": list(menu_keys), "action_keys": ["*"]}


def case(no, status="受理", **data):
    return BusinessRecord(module="ipr_case", serial_no=no, title=no, customer="客户", status=status, owner=data.pop("owner", "someone"),
                          department="知产部", data={"case_kind": "专利", "case_category": "non_litigation", **data})


class MenuTest(unittest.TestCase):
    def test_tree(self):
        parents = {key: (parent, label) for key, parent, label, _icon, _order in DEFAULT_SYSTEM_MENUS}
        self.assertEqual({key for key in parents if parents[key][0] == "ipr-my-cases"}, set(MY_PAGES))
        self.assertEqual(parents["ipr-business-owner"][1], "我是管理人")
        self.assertEqual({key for key in parents if parents[key][0] == "ipr-all-cases"}, {"ipr-all-patent", "ipr-all-trademark"})
        self.assertEqual({key for key in parents if parents[key][0] == "ipr-process"},
                         {"ipr-patent-transfer", "ipr-trademark-transfer", "ipr-patent-annual-fee", "ipr-case-reboot", "ipr-case-files", "ipr-office-files"})
        self.assertEqual(parents["ipr-finance"][0], "ipr", "非诉财务中心单独留一块")
        for key in ("ipr-review", "ipr-officer", "ipr-patent", "ipr-trademark"):
            self.assertIn(key, DEFAULT_HIDDEN_MENU_KEYS)
            self.assertIn(key, ROLE_TREE_HIDDEN_MENU_KEYS)
        for key in (*MY_PAGES, "ipr-all-cases", "ipr-all-patent", "ipr-all-trademark", "ipr-process"):
            self.assertNotIn(key, DEFAULT_HIDDEN_MENU_KEYS)
            self.assertNotIn(key, ROLE_TREE_HIDDEN_MENU_KEYS)

    def test_grants(self):
        finance = set(_expand_menu_permission_keys(FINANCE_STORED))
        self.assertFalse({"ipr-all-cases", "ipr-all-patent", "ipr-all-trademark"} & finance, "全部案件只单独配")
        self.assertLessEqual({"ipr-process", "ipr-case-reboot", "ipr-office-files", *MY_PAGES}, finance, "现有页面不丢")
        self.assertLessEqual(set(MY_PAGES), set(_expand_menu_permission_keys(["ipr-my-cases"])))
        self.assertLessEqual({"ipr-all-patent", "ipr-all-trademark"}, set(_expand_menu_permission_keys(["ipr-all-cases"])))

    def test_page_classes(self):
        for key in (*MY_PAGES, "ipr-my-cases", "ipr-officer"):
            self.assertTrue(is_personal_page(key), key)
        for key in ("ipr-all-patent", "ipr-all-trademark", "ipr-patent-annual-fee", "ipr-patent"):
            self.assertFalse(is_personal_page(key), key)


class ScopeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="me690", display_name="我", department="知产部", role="user", password_hash="x", is_active=True))
            db.add_all([case("M1", agent="me690"), case("M2", "失效", business_owner="me690"), case("M3", owner="me690"),
                        case("X1", agent="别人"), case("X2", "失效", business_owner="别人")])
            await db.commit()
            self.other = (await db.execute(BusinessRecord.__table__.select().where(BusinessRecord.serial_no == "X1"))).first().id
        self.previous = dict(app.dependency_overrides)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        self.identity = who()
        app.dependency_overrides[current_identity] = lambda: dict(self.identity)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr690.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()
        reset_gate_cache()

    async def serials(self, **params):
        response = await self.client.get(f"{API}/ipr/cases", params={"page_size": 100, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return sorted(item["serial_no"] for item in response.json()["items"])

    async def test_my_pages_only_see_own_cases(self):
        self.identity = who("ipr-my-cases", *MY_PAGES)
        self.assertEqual(await self.serials(), ["M1", "M2", "M3"], "不带视图也看不到全所")
        self.assertEqual(await self.serials(role_view="invalid"), ["M2"], "失效案件只看自己相关的")
        self.assertEqual((await self.client.get(f"{API}/ipr/cases/{self.other}")).status_code, 404)

    async def test_work_pages_see_whole_firm(self):
        everything = ["M1", "M2", "M3", "X1", "X2"]
        for keys in (("ipr-all-patent",), ("ipr-all-cases", "ipr-all-patent"), ("ipr-my-cases", "ipr-my-mine", "ipr-case-reboot"), ("ipr-finance-receipts",)):
            self.identity = who(*keys)
            self.assertEqual(await self.serials(), everything, keys)
        self.identity = who(actual="admin")
        self.assertEqual(await self.serials(), everything, "真实管理员")

    async def test_gate_off_returns_old_behaviour(self):
        async with self.sessions() as db:
            db.add(SystemConfig(key=GATE_CONFIG_KEY, label="t", group="t", description="", value="off"))
            await db.commit()
        reset_gate_cache()
        self.identity = who("ipr-my-mine")
        self.assertEqual(await self.serials(), ["M1", "M2", "M3", "X1", "X2"])


if __name__ == "__main__":
    unittest.main()

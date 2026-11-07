"""案件保存后案号、当事人、中文都能搜到：JSON 列保留中文；案号不分空格和全半角括号；范围不放宽。"""
import unittest

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, dumps_json, engine as app_engine, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity

API = settings.api_prefix


def identity(username):
    return {"username": username, "display_name": username, "department": "诉讼部", "role": "user", "role_ids": ["user"],
            "_actual_role": "user", "_actual_role_ids": ["user"], "_page_menu_capability": False, "_page_scope_actual": False,
            "menu_keys": ["case", "case-mine", "case-mine-civil"], "action_keys": []}


class SerializerTest(unittest.TestCase):
    def test_keeps_chinese_and_never_fails(self):
        self.assertEqual(dumps_json({"案号": "（2026）皖1226民初8944号"}), '{"案号": "（2026）皖1226民初8944号"}')
        self.assertEqual(dumps_json({"a": "\ud83d"}), '{"a": "\\ud83d"}', "孤立代理字符不能让保存失败")
        self.assertIs(app_engine.dialect._json_serializer, dumps_json, "系统引擎要用这个写法")


class SearchAfterSaveTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False},
                                          poolclass=StaticPool, json_serializer=dumps_json)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([User(username=name, display_name=name, department="诉讼部", role="user", password_hash="x", is_active=True) for name in ("me", "other")])
            db.add_all([
                self.case("AJ1", "me", court_case_no="（2026）皖1226民初8944号", plaintiff="张三丰"),
                self.case("AJ2", "me", court_case_no="（2025）沪 0151 民初 3310 号"),
                self.case("AJ3", "me", court_case_no="(2024)苏0505民初77号"),
                self.case("AJ4", "other", court_case_no="（2026）皖1226民初8944号", plaintiff="张三丰"),
            ])
            await db.commit()
            # 经系统保存：整个 data 重新写一次
            for item in (await db.scalars(select(BusinessRecord))).all():
                item.data = {**item.data, "remark": "保存过"}
            await db.commit()
        self.previous = dict(app.dependency_overrides)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: identity("me")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://cases.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    @staticmethod
    def case(no, owner, **data):
        return BusinessRecord(module="case", serial_no=no, title=f"案件{no}", customer="某公司", status="立案", owner=owner, department="诉讼部",
                              data={"case_type": "民事", "case_no": no, "owner_username": owner, **data})

    async def search(self, keyword, scope="mine"):
        response = await self.client.post(f"{API}/cases/search", json={"scope": scope, "keyword": keyword, "page_size": 50})
        self.assertEqual(response.status_code, 200, response.text)
        return sorted(item["serial_no"] for item in response.json()["items"])

    async def test_stored_text_keeps_chinese(self):
        async with self.sessions() as db:
            raw = await db.scalar(text("select data from business_records where serial_no='AJ1'"))
        self.assertIn("（2026）皖1226民初8944号", raw)
        self.assertNotIn("\\u", raw)

    async def test_found_after_save_and_scope_not_widened(self):
        self.assertEqual(await self.search("（2026）皖1226民初8944号"), ["AJ1"], "别人的同案号案件不能带出来")
        self.assertEqual(await self.search("张三丰"), ["AJ1"], "当事人")
        self.assertEqual(await self.search("皖1226民初"), ["AJ1"], "部分案号")

    async def test_case_number_ignores_spaces_and_bracket_width(self):
        self.assertEqual(await self.search("（2025）沪0151民初3310号"), ["AJ2"], "库里带空格，搜不带")
        self.assertEqual(await self.search("(2025)沪0151民初3310号"), ["AJ2"], "半角搜全角")
        self.assertEqual(await self.search("（2024）苏 0505 民初 77 号"), ["AJ3"], "全角加空格搜半角")
        self.assertEqual(await self.search("沪 0151 民初 3310 号"), ["AJ2"], "没有年份括号")

    async def test_employee_reference_found_in_old_escaped_rows(self):
        from app.core.system import _collect_hr_employee_deletion_blockers
        async with self.sessions() as db:
            await db.execute(text("""update business_records set data = '{"handler": "\\u674e\\u56db\\u5149"}' where serial_no='AJ3'"""))
            employee = BusinessRecord(module="hr", serial_no="YG1", title="李四光", customer="", status="在职", owner="me", department="诉讼部", data={})
            db.add(employee)
            await db.commit()
            blockers, _ = await _collect_hr_employee_deletion_blockers(employee, {"username": "me", "role": "admin", "role_ids": ["admin"]}, db)
        self.assertTrue(any(item["kind"] == "业务引用" or "AJ3" in str(item) for item in blockers), blockers)

    async def test_global_scope_same(self):
        self.assertIn("AJ2", await self.search("（2025）沪0151民初3310号", "global"))
        self.assertIn("AJ3", await self.search("（2024）苏 0505 民初 77 号", "global"))


if __name__ == "__main__":
    unittest.main()

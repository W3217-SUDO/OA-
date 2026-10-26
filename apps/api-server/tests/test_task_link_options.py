"""新建任务选关联案件、客户（问题处理中心 BUG20261026002）：按关键词搜当前账号能看到的案件和客户。"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.tp.router import router
from app.core.dependencies import current_identity, get_db
from app.database import Base
from app.models import BusinessRecord, User

ADMIN = {"username": "CODEXTLADMIN", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "任务管理员", "department": "CODEXTL", "menu_keys": ["*"], "action_keys": ["*"]}
STAFF = {"username": "CODEXTLSTAFF", "role": "staff", "role_ids": ["staff"], "_actual_role_ids": ["staff"],
         "display_name": "任务员工", "department": "CODEXTL-OTHER", "menu_keys": [], "action_keys": []}


def record(module, serial_no, title, *, customer="", owner="CODEXTLADMIN", data=None):
    return BusinessRecord(module=module, serial_no=serial_no, title=title, customer=customer, status="进行中",
                          owner=owner, department="CODEXTL", description="CODEXTL", data=data or {})


class TaskLinkOptionsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name="任务管理员", password_hash="isolated-only",
                     department="CODEXTL", role="admin"),
                User(username=STAFF["username"], display_name="任务员工", password_hash="isolated-only",
                     department="CODEXTL-OTHER", role="staff"),
                record("case", "CODEXTL2600001", "浙江甲公司诉乙公司", customer="浙江甲公司",
                       data={"court_case_no": "（2026）浙0102民初1号"}),
                record("case", "CODEXTL2600002", "上海丙公司合同纠纷", customer="上海丙公司"),
                record("case", "CODEXTL26000021", "上海丙公司另案", customer="上海丙公司"),
                record("case", "CODEXTL2600009", "员工自己的案件", customer="员工客户", owner=STAFF["username"]),
                record("customer", "CODEXTLKH001", "浙江甲公司"),
                record("customer", "CODEXTLKH002", "上海丙公司"),
                record("customer", "CODEXTLKH003", ""),
                record("contract", "CODEXTLHT001", "浙江甲公司合同", customer="浙江甲公司"),
            ])
            await db.commit()
        self.identity = dict(ADMIN)
        app = FastAPI()
        app.include_router(router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _cases(self, keyword="", **params):
        response = await self.client.get("/api/v1/tasks/case-options", params={"keyword": keyword, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return [item["serial_no"] for item in response.json()["items"]]

    async def test_case_options_search_number_name_customer_and_court_number(self):
        self.assertEqual(set(await self._cases("浙江")), {"CODEXTL2600001"})
        self.assertEqual(set(await self._cases("浙0102民初")), {"CODEXTL2600001"})
        self.assertEqual(set(await self._cases("合同纠纷")), {"CODEXTL2600002"})
        # 直接输入完整案号：完全一致的排第一，前缀相同的其他案号排后面。
        self.assertEqual((await self._cases("CODEXTL2600002"))[0], "CODEXTL2600002")
        self.assertEqual(len(await self._cases("", limit=2)), 2)
        response = await self.client.get("/api/v1/tasks/case-options", params={"keyword": "浙江"})
        item = response.json()["items"][0]
        self.assertEqual((item["title"], item["customer"], item["court_case_no"]),
                         ("浙江甲公司诉乙公司", "浙江甲公司", "（2026）浙0102民初1号"))

    async def test_customer_options_search_and_skip_blank_names(self):
        response = await self.client.get("/api/v1/tasks/customer-options", params={"keyword": ""})
        self.assertEqual(response.status_code, 200, response.text)
        names = [item["name"] for item in response.json()["items"]]
        self.assertEqual(set(names), {"浙江甲公司", "上海丙公司"})
        response = await self.client.get("/api/v1/tasks/customer-options", params={"keyword": "KH002"})
        self.assertEqual([item["name"] for item in response.json()["items"]], ["上海丙公司"])

    async def test_non_admin_only_sees_visible_cases(self):
        self.identity = dict(STAFF)
        self.assertEqual(await self._cases(""), ["CODEXTL2600009"])
        self.assertEqual(await self._cases("浙江"), [])

    async def test_limit_is_capped(self):
        response = await self.client.get("/api/v1/tasks/case-options", params={"limit": 500})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

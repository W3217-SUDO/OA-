"""客户列表类型筛选：选“全部”时客户、申请人等类型都能按名称查到。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_customers
from app.database import Base
from app.models import BusinessRecord, SystemParameter, User

ADMIN = {"username": "admin", "role": "admin", "_page_menu_capability": True}


class CustomerListAllTypesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理者", role="admin", role_ids=["admin"], password_hash="x"))
            db.add_all([SystemParameter(category="customer_type", code=code, name=name, is_active=True)
                        for code, name in (("CUSTOMER", "客户"), ("2", "申请人"), ("0", "未设置"))])
            for serial, title, kind in (("CODEX-CT-1", "甲客户公司", "客户"), ("CODEX-CT-2", "上海交通大学", "申请人"), ("CODEX-CT-3", "丙", "未设置")):
                db.add(BusinessRecord(module="customer", serial_no=serial, title=title, customer="", status="正常", owner="admin",
                                      data={"customer_type": kind, "customer_managers": ["admin"]}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _titles(self, **params):
        async with self.sessions() as db:
            args = dict(scope="company", customer_name="", customer_type="客户", manager="", page=1, page_size=15, identity=ADMIN, db=db)
            args.update(params)
            return sorted(item["title"] for item in (await list_customers(**args))["items"])

    async def test_default_type_still_only_lists_clients(self):
        self.assertEqual(await self._titles(), ["甲客户公司"])
        self.assertEqual(await self._titles(customer_name="上海交通大学"), [])

    async def test_all_types_finds_applicants_and_unset_records_by_name(self):
        self.assertEqual(await self._titles(customer_type="全部", customer_name="上海交通大学"), ["上海交通大学"])
        self.assertEqual(await self._titles(customer_type="全部"), ["上海交通大学", "丙", "甲客户公司"])

    async def test_specific_type_filter_is_unchanged(self):
        self.assertEqual(await self._titles(customer_type="申请人"), ["上海交通大学"])


if __name__ == "__main__":
    unittest.main()

"""501666（shenhe 11-06）：内部费用 待核销/已核销列表按费用类型筛选——包里任一笔费用属于所选类型（选上级含下级）就列出。"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance import internal_payments
from app.core import soft_delete
from app.core.dependencies import current_identity, get_db
from app.database import Base
from app.models import BusinessRecord, SystemParameter, User

ADMIN = {"username": "fadmin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "管理员", "department": "财务部", "action_keys": ["*"]}


class PackageFeeTypeFilterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add(User(username="fadmin", display_name="管理员", password_hash="x", department="财务部", role="admin"))
            internal = SystemParameter(category="fee_type", code="INTERNAL", name="内部费用", extra={})
            archive = SystemParameter(category="fee_type", code="1104030", name="调档费", extra={"parent_code": "INTERNAL"})
            survey = SystemParameter(category="fee_type", code="1104040", name="调查提成", extra={"parent_code": "INTERNAL"})
            db.add_all([internal, archive, survey])
            await db.flush()
            fee_archive = BusinessRecord(module="finance", serial_no="F1", title="调档费", owner="a", department="d", status="待核销",
                                         data={"fee_type": "内部费用", "fee_type_id": archive.id, "fee_type_code": "1104030", "expense_subtype": "调档费"})
            # 导入的旧明细没有类型代码，只有名称快照
            fee_survey = BusinessRecord(module="finance", serial_no="F2", title="调查提成", owner="a", department="d", status="待核销",
                                        data={"fee_type": "内部费用", "fee_type_name": "调查提成", "commission_type": "调查提成",
                                              "legacy_kind": "internal_payment_line"})
            db.add_all([fee_archive, fee_survey])
            await db.flush()
            for no, ids in (("PA", [fee_archive.id]), ("PB", [fee_survey.id]), ("PC", [fee_archive.id, fee_survey.id])):
                db.add(BusinessRecord(module="finance_package", serial_no=no, title=no, owner="shenhe", department="d", status="待核销",
                                      data={"fee_type": "内部费用付款包", "fee_ids": ids, "amount": 1, "total_amount": 1}))
            await db.commit()
        app = FastAPI()
        app.include_router(internal_payments.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ADMIN)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def listed(self, **params):
        response = await self.client.get("/api/v1/finance/payment-packages",
                                         params={"package_scope": "internal", "status": "待核销", "page_size": 1, **params})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        return body["total"], body["items"]

    async def test_leaf_code_filters_packages_and_total(self):
        total, items = await self.listed(fee_types="1104030")
        self.assertEqual(total, 2)
        self.assertEqual(len(items), 1)
        total, _ = await self.listed(fee_types="1104040", page_size=20)
        self.assertEqual(total, 2)

    async def test_parent_code_includes_children_and_no_filter_lists_all(self):
        self.assertEqual((await self.listed(fee_types="INTERNAL", page_size=20))[0], 3)
        self.assertEqual((await self.listed(page_size=20))[0], 3)
        self.assertEqual((await self.listed(fee_types="请选择", page_size=20))[0], 3)

    async def test_payee_and_fee_type_together(self):
        self.assertEqual((await self.listed(fee_types="1104030", payee="nobody", page_size=20))[0], 0)


if __name__ == "__main__":
    unittest.main()

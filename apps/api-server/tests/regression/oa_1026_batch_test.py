"""10.26 批次：第4行合同付款不因已删除的标的案件 404；第5行客户类型同名去重；第10行费用类型同名去重。

只用一次性内存 SQLite，测试数据前缀 CODEX-1026-。
"""
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import unittest
from datetime import datetime

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.areas.contract import router as contract_routes
from app.areas.crm import router as crm_routes
from app.core.dependencies import current_identity
from app.core.finance import _fee_type_catalog, _fee_type_catalog_aliases
from app.data_models.contracts import ContractObject
from app.database import Base, get_db
from app.models import BusinessRecord, SystemParameter, User

ADMIN = {"username": "admin", "role": "admin", "department": "CODEX-1026"}


def parameter(category, code, name, sort_order=0, **extra):
    return SystemParameter(category=category, code=code, name=name, extra=extra, sort_order=sort_order,
                           is_active=True, created_by="admin", updated_by="admin")


class Oa1026BatchTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.db.add(User(username="admin", password_hash="isolated-not-a-login", department="CODEX-1026"))
        await self.db.commit()
        app = FastAPI()
        app.include_router(contract_routes.router)
        app.include_router(crm_routes.router)
        app.dependency_overrides[current_identity] = lambda: ADMIN

        async def isolated_db():
            try:
                yield self.db
            except Exception:
                await self.db.rollback()
                raise
        app.dependency_overrides[get_db] = isolated_db
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.close()
        await self.engine.dispose()

    def record(self, module, suffix, status="草稿", data=None):
        record = BusinessRecord(module=module, serial_no=f"CODEX-1026-{suffix}", title=f"CODEX-1026-{suffix}",
            customer="CODEX-1026-CUSTOMER", status=status, owner="admin", department="CODEX-1026", data=data or {})
        self.db.add(record)
        return record

    async def test_row4_payment_candidates_skip_deleted_object_case(self):
        contract = self.record("contract", "CONTRACT", data={"contract_body": "律所"})
        live_case = self.record("case", "LIVE", status="在办")
        deleted_case = self.record("case", "DELETED", status="新案待分配")
        await self.db.flush()
        deleted_case.deleted_at = datetime.now()
        deleted_case.deleted_by = "admin"
        source = {"case_id": live_case.id, "case_no": live_case.serial_no,
                  "contract_id": contract.id, "contract_no": contract.serial_no}
        fee = self.record("finance", "FEE", data={**source, "fee_type": "官方费用", "expense_subtype": "一审诉讼费", "amount": 100})
        for case in (live_case, deleted_case):
            self.db.add(ContractObject(contract_record_id=contract.id, case_record_id=case.id, fee_type="官方费用",
                                       amount=100, created_by="admin", updated_by="admin"))
        await self.db.commit()
        response = await self.client.get(f"/api/v1/contracts/{contract.id}/payment-candidates")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(fee.id, {row["case_fee_id"] for row in response.json()["items"]})
        objects = await self.client.get(f"/api/v1/contracts/{contract.id}/objects")
        self.assertEqual(objects.status_code, 200, objects.text)
        self.assertEqual([row["case_record_id"] for row in objects.json()["items"]], [live_case.id])

    async def test_row5_customer_types_deduplicated_by_name(self):
        self.db.add_all([parameter("customer_type", "1", "客户", 0), parameter("customer_type", "APPLICANT", "申请人", 1),
                         parameter("customer_type", "CUSTOMER", "客户", 130)])
        await self.db.commit()
        response = await self.client.get("/api/v1/customers/reference-options")
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()["customer_types"]
        self.assertEqual([row["label"] for row in rows], ["客户", "申请人"])
        self.assertEqual(rows[0]["code"], "1")

    def test_row10_preset_leaf_merged_into_legacy_leaf_under_same_root(self):
        items = [parameter("fee_type", "OFFICIAL", "官方费用", parent_code=""),
                 parameter("fee_type", "1101010", "一审诉讼费", parent_code="OFFICIAL"),
                 parameter("fee_type", "11010020", "一审诉讼费", parent_code="OFFICIAL",
                           legacy_source="hz_crm_20260930", legacy_id=11010020, legacy_group_id=1),
                 parameter("fee_type", "11010030", "二审诉讼费", parent_code="OFFICIAL",
                           legacy_source="hz_crm_20260930", legacy_id=11010030, legacy_group_id=1)]
        for index, item in enumerate(items, start=1):
            item.id = index
        names = [row["name"] for row in _fee_type_catalog(items) if row["selectable"]]
        self.assertEqual(names, ["一审诉讼费", "二审诉讼费"])
        self.assertEqual(_fee_type_catalog_aliases(items), {2: 3})


if __name__ == "__main__":
    unittest.main()

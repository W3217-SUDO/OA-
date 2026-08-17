"""Runtime coverage for automatic relation resolution in generic CSV imports."""

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "import-admin", "role": "admin", "display_name": "导入管理员", "department": "测试部"}


class RecordImportRelationResolutionContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", role_ids=["admin"], password_hash="x", is_active=True))
            customer = BusinessRecord(module="customer", serial_no="KH-IMPORT-001", title="自动关联客户", customer="自动关联客户", status="正常", owner=IDENTITY["username"], department=IDENTITY["department"], data={})
            db.add(customer)
            await db.flush()
            contract = BusinessRecord(module="contract", serial_no="HT-IMPORT-001", title="自动关联合同", customer=customer.title, status="审批通过", owner=IDENTITY["username"], department=IDENTITY["department"], data={"customer_id": customer.id, "customer_record_id": customer.id, "customer_no": customer.serial_no})
            db.add(contract)
            await db.flush()
            case = BusinessRecord(module="case", serial_no="AJ-IMPORT-001", title="自动关联案件", customer=customer.title, status="新案待分配", owner=IDENTITY["username"], department=IDENTITY["department"], data={"customer_id": customer.id, "customer_record_id": customer.id, "customer_no": customer.serial_no, "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no})
            db.add(case)
            await db.commit()
            self.customer_id = customer.id
            self.contract_id = contract.id
            self.case_id = case.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://record-import.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def import_csv(self, module: str, content: str):
        return await self.client.post(
            f"{API}/records/import",
            params={"module": module},
            files={"file": (f"{module}.csv", content.encode("utf-8"), "text/csv")},
        )

    async def test_contract_customer_name_resolves_to_customer_id(self):
        response = await self.import_csv(
            "contract",
            "业务编号,合同名称,客户/主体,合同类型,合同金额,签订日期,负责人\n"
            "HT-IMPORTED-002,导入合同,自动关联客户,专项服务,100,2026-08-14,import-admin\n",
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["failed"], 0, response.text)
        async with self.sessions() as db:
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "HT-IMPORTED-002"))
        self.assertEqual(record.data["customer_id"], self.customer_id)
        self.assertEqual(record.data["customer_record_id"], self.customer_id)
        self.assertEqual(record.data["customer_no"], "KH-IMPORT-001")

    async def test_case_number_carries_full_customer_and_contract_chain(self):
        response = await self.import_csv(
            "document",
            "业务编号,文件名称,收发类型,文件日期,关联案号,负责人\n"
            "SW-IMPORTED-002,导入法院文书,收文,2026-08-14,AJ-IMPORT-001,import-admin\n",
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["failed"], 0, response.text)
        async with self.sessions() as db:
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "SW-IMPORTED-002"))
        self.assertEqual(record.data["case_id"], self.case_id)
        self.assertEqual(record.data["case_record_id"], self.case_id)
        self.assertEqual(record.data["contract_id"], self.contract_id)
        self.assertEqual(record.data["customer_id"], self.customer_id)
        self.assertEqual(record.customer, "自动关联客户")

    async def test_unknown_parent_fails_without_creating_record(self):
        response = await self.import_csv(
            "finance",
            "业务编号,费用名称,费用类型,金额,关联案号,经办人\n"
            "FY-IMPORTED-BAD,错误费用,官方费用,100,AJ-NOT-FOUND,import-admin\n",
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["failed"], 1, response.text)
        async with self.sessions() as db:
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "FY-IMPORTED-BAD"))
        self.assertIsNone(record)


if __name__ == "__main__":
    unittest.main()

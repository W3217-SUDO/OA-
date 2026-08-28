import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractApprovalStep, FileAttachment, RolePermission, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "row24-admin", "role": "admin", "display_name": "第24行管理员", "department": "第24行部门"}


class CustomerCountNavigationRow24Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [
            User.__table__, RolePermission.__table__, SystemParameter.__table__, BusinessRecord.__table__,
            ContractApprovalStep.__table__, FileAttachment.__table__, WorkflowEvent.__table__,
        ]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables))
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            db.add(SystemParameter(category="customer_type", code="customer", name="客户", is_active=True, sort_order=1))
            customer = BusinessRecord(module="customer", serial_no="KH-R24-001", title="测试客户1", customer="测试客户1", status="正常", owner=IDENTITY["username"], department=IDENTITY["department"], data={"customer_type": "客户"})
            similar = BusinessRecord(module="customer", serial_no="KH-R24-002", title="测试客户1分公司", customer="测试客户1分公司", status="正常", owner=IDENTITY["username"], department=IDENTITY["department"], data={"customer_type": "客户"})
            db.add_all([customer, similar])
            await db.flush()
            self.customer_id = customer.id
            db.add_all([
                BusinessRecord(module="contract", serial_no="HT-R24-ID", title="ID关联合同", customer=customer.title, status="审批通过", owner="other", department="其他部门", data={"customer_id": customer.id, "customer_no": customer.serial_no}),
                BusinessRecord(module="contract", serial_no="HT-R24-NAME", title="迁移名称合同", customer=customer.title, status="审批通过", owner="other", department="其他部门", data={}),
                BusinessRecord(module="contract", serial_no="HT-R24-ARCHIVED", title="已归档合同", customer=customer.title, status="已归档", owner=IDENTITY["username"], department=IDENTITY["department"], data={}),
                BusinessRecord(module="contract", serial_no="HT-R24-SIMILAR", title="相似客户合同", customer=similar.title, status="审批通过", owner=IDENTITY["username"], department=IDENTITY["department"], data={"customer_id": similar.id, "customer_no": similar.serial_no}),
                BusinessRecord(module="case", serial_no="CASE-R24-ID", title="ID关联民事案件", customer=customer.title, status="文书准备", owner="other", department="其他部门", data={"case_type": "民事案件", "customer_id": customer.id, "customer_no": customer.serial_no}),
                BusinessRecord(module="case", serial_no="CASE-R24-NAME", title="迁移名称民事案件", customer=customer.title, status="文书准备", owner="other", department="其他部门", data={"case_type": "民事争议"}),
                BusinessRecord(module="case", serial_no="CASE-R24-NON-CIVIL", title="非民事案件", customer=customer.title, status="办理中", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "刑事案件"}),
                BusinessRecord(module="case", serial_no="CASE-R24-SIMILAR", title="相似客户案件", customer=similar.title, status="文书准备", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "民事案件", "customer_id": similar.id, "customer_no": similar.serial_no}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row24.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_customer_counts_equal_the_click_through_lists(self):
        customers = await self.client.get(f"{API}/customers", params={"scope": "mine", "customer_name": "测试客户1", "customer_type": "客户", "page": 1, "page_size": 15})
        self.assertEqual(customers.status_code, 200, customers.text)
        customer_row = next(item for item in customers.json()["items"] if item["id"] == self.customer_id)
        self.assertEqual(customer_row["data"]["contract_count"], 2)
        self.assertEqual(customer_row["data"]["civil_case_count"], 2)

        contracts = await self.client.get(f"{API}/records", params={"module": "contract", "scope": "mine", "customer_id": self.customer_id, "customer": "测试客户1", "exclude_archived": "true", "page": 1, "page_size": 100})
        self.assertEqual(contracts.status_code, 200, contracts.text)
        self.assertEqual(contracts.json()["total"], customer_row["data"]["contract_count"])
        self.assertEqual({item["serial_no"] for item in contracts.json()["items"]}, {"HT-R24-ID", "HT-R24-NAME"})

        cases = await self.client.post(f"{API}/cases/search", json={"scope": "mine", "case_types": ["民事案件", "民事争议"], "customer_id": self.customer_id, "customer": "测试客户1", "page": 1, "page_size": 100})
        self.assertEqual(cases.status_code, 200, cases.text)
        self.assertEqual(cases.json()["total"], customer_row["data"]["civil_case_count"])
        self.assertEqual({item["serial_no"] for item in cases.json()["items"]}, {"CASE-R24-ID", "CASE-R24-NAME"})


if __name__ == "__main__":
    unittest.main()

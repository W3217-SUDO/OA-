import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "customer-count-admin", "role": "admin", "display_name": "客户管理员", "department": "上海分所"}


class CustomerCountScopedNavigationContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[
                User.__table__,
                RolePermission.__table__,
                BusinessRecord.__table__,
                FileAttachment.__table__,
                WorkflowEvent.__table__,
            ]))
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role=ADMIN["role"], password_hash="test", is_active=True))
            customer_a = BusinessRecord(module="customer", serial_no="KH-A", title="客户A", customer="客户A", status="正常", owner=ADMIN["username"], department=ADMIN["department"], data={})
            customer_a_child = BusinessRecord(module="customer", serial_no="KH-A-CHILD", title="客户A子公司", customer="客户A子公司", status="正常", owner=ADMIN["username"], department=ADMIN["department"], data={})
            db.add_all([customer_a, customer_a_child])
            await db.flush()
            self.customer_a_id = customer_a.id
            db.add_all([
                BusinessRecord(module="contract", serial_no="HT-CNT-001", title="客户A合同一", customer="客户A", status="草稿", owner="other-owner", department="其他分所", data={"customer_id": customer_a.id, "customer_no": "KH-A"}),
                BusinessRecord(module="contract", serial_no="HT-CNT-002", title="客户A合同二", customer="客户A", status="履行中", owner=ADMIN["username"], department=ADMIN["department"], data={"customer_id": customer_a.id, "customer_no": "KH-A"}),
                BusinessRecord(module="contract", serial_no="HT-CNT-003", title="客户A归档合同", customer="客户A", status="已归档", owner=ADMIN["username"], department=ADMIN["department"], data={"customer_id": customer_a.id, "customer_no": "KH-A"}),
                BusinessRecord(module="contract", serial_no="HT-CNT-004", title="子公司合同", customer="客户A子公司", status="草稿", owner=ADMIN["username"], department=ADMIN["department"], data={"customer_id": customer_a_child.id, "customer_no": "KH-A-CHILD"}),
                BusinessRecord(module="case", serial_no="CA-CNT-001", title="客户A民事案件", customer="客户A", status="办理中", owner="other-owner", department="其他分所", data={"case_type": "民事案件", "customer_id": customer_a.id, "customer_no": "KH-A"}),
                BusinessRecord(module="case", serial_no="CA-CNT-002", title="子公司民事案件", customer="客户A子公司", status="办理中", owner=ADMIN["username"], department=ADMIN["department"], data={"case_type": "民事案件", "customer_id": customer_a_child.id, "customer_no": "KH-A-CHILD"}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://customer-count.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_contract_records_are_filtered_by_exact_customer_identity_before_paging(self):
        response = await self.client.get(f"{API}/records", params={
            "module": "contract",
            "scope": "mine",
            "customer_id": self.customer_a_id,
            "customer": "客户A",
            "exclude_archived": "true",
            "page": 1,
            "page_size": 100,
        })

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual({item["serial_no"] for item in payload["items"]}, {"HT-CNT-001", "HT-CNT-002"})
        self.assertEqual({item["customer"] for item in payload["items"]}, {"客户A"})

    async def test_case_search_uses_exact_customer_identity_and_returns_all_linked_owners(self):
        response = await self.client.post(f"{API}/cases/search", json={
            "scope": "mine",
            "case_types": ["民事案件"],
            "customer_id": self.customer_a_id,
            "customer": "客户A",
            "page": 1,
            "page_size": 100,
        })

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["serial_no"], "CA-CNT-001")

    async def test_contract_creation_allocates_distinct_server_numbers_and_ignores_client_number(self):
        payload = {
            "serial_no": "CLIENT-MUST-BE-IGNORED",
            "title": "CODEX-并发合同",
            "customer": "客户A",
            "owner": ADMIN["username"],
            "department": ADMIN["department"],
            "data": {"amount": 0},
        }
        first = await self.client.post(f"{API}/contracts", json=payload)
        second = await self.client.post(f"{API}/contracts", json=payload)

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(second.status_code, 201, second.text)
        serials = {first.json()["serial_no"], second.json()["serial_no"]}
        self.assertEqual(len(serials), 2)
        self.assertTrue(all(serial.startswith("SHHT") for serial in serials))


if __name__ == "__main__":
    unittest.main()

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractApprovalStep, RolePermission, User
from app.security import current_identity


IDENTITY = {"username": "archive-list-admin", "role": "admin", "display_name": "归档列表管理员", "department": "合同部"}


class ContractArchiveListTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [User.__table__, RolePermission.__table__, BusinessRecord.__table__, ContractApprovalStep.__table__]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables))
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            db.add_all([
                BusinessRecord(module="contract", serial_no="ARCH-001", title="已归档合同", customer="甲客户", status="已归档", owner=IDENTITY["username"], department=IDENTITY["department"], data={"archived_at": "2026-09-01T10:00:00"}),
                BusinessRecord(module="contract", serial_no="ARCH-002", title="归档中合同", customer="乙客户", status="审批通过", owner=IDENTITY["username"], department=IDENTITY["department"], data={}),
                BusinessRecord(module="contract", serial_no="ARCH-003", title="已取消完结合同", customer="丙客户", status="审批通过", owner=IDENTITY["username"], department=IDENTITY["department"], data={"archive_closure_updated_at": "2026-09-03T10:00:00"}),
                BusinessRecord(module="finance", serial_no="FEE-002", title="归档中的费用", customer="乙客户", status="已付款", owner=IDENTITY["username"], department=IDENTITY["department"], data={"contract_id": 2, "fee_archived": True, "fee_archived_at": "2026-09-02T10:00:00"}),
                BusinessRecord(module="finance", serial_no="FEE-003", title="取消归档的费用", customer="丙客户", status="已付款", owner=IDENTITY["username"], department=IDENTITY["department"], data={"contract_id": 3, "fee_archived": False}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://archive-list.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_archive_list_filters_paginates_and_excludes_cancelled_closure(self):
        response = await self.client.get(f"{settings.api_prefix}/contracts/archive-list", params={"page": 1, "page_size": 1})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(len(payload["items"]), 1)
        self.assertNotIn("ARCH-003", [item["serial_no"] for item in payload["items"]])
        filtered = await self.client.get(f"{settings.api_prefix}/contracts/archive-list", params={"archive_status": "归档中", "customer": "乙", "page": 1, "page_size": 15})
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual([(item["serial_no"], item["archive_status"]) for item in filtered.json()["items"]], [("ARCH-002", "归档中")])
        date_filtered = await self.client.get(f"{settings.api_prefix}/contracts/archive-list", params={"archive_date_from": "2026-09-02", "archive_date_to": "2026-09-02", "page": 1, "page_size": 15})
        self.assertEqual(date_filtered.status_code, 200, date_filtered.text)
        self.assertEqual([item["serial_no"] for item in date_filtered.json()["items"]], ["ARCH-002"])
        invalid_dates = await self.client.get(f"{settings.api_prefix}/contracts/archive-list", params={"archive_date_from": "2026-09-03", "archive_date_to": "2026-09-02"})
        self.assertEqual(invalid_dates.status_code, 422, invalid_dates.text)
        exported = await self.client.get(f"{settings.api_prefix}/contracts/archive-list/export-excel", params={"page": 1, "page_size": 1})
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertIn("ARCH-001".encode(), exported.content)
        self.assertIn("ARCH-002".encode(), exported.content)


if __name__ == "__main__":
    unittest.main()

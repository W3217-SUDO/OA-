"""Isolated contracts for stable-GUID contract event history parity."""

import unittest
from xml.etree import ElementTree

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractEvent, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
GUID = "22222222-2222-4222-8222-222222222222"
FOREIGN_GUID = "44444444-4444-4444-8444-444444444444"
ADMIN = {"username": "contract-d9-admin", "role": "admin", "display_name": "合同管理员", "department": "上海分所"}
USER = {"username": "contract-d9-user", "role": "user", "display_name": "合同员工", "department": "上海分所"}


class ContractEventBackendD9Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="test", is_active=True),
                User(username=USER["username"], display_name=USER["display_name"], department=USER["department"], role="user", password_hash="test", is_active=True),
                RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=["user-center"], field_keys=[]),
                BusinessRecord(module="customer", serial_no="CUS-D9-001", title="D9 客户", customer="D9 客户", status="正常", owner=ADMIN["username"], department=ADMIN["department"], data={}),
            ])
            contract = BusinessRecord(
                module="contract", serial_no="CON-D9-001", title="D9 合同", customer="D9 客户",
                status="草稿", owner=USER["username"], department=USER["department"],
                data={"contract_guid": GUID},
            )
            archived = BusinessRecord(
                module="contract", serial_no="CON-D9-002", title="D9 已归档合同", customer="D9 客户",
                status="已归档", owner=USER["username"], department=USER["department"],
                data={"contract_guid": "33333333-3333-4333-8333-333333333333"},
            )
            foreign = BusinessRecord(
                module="contract", serial_no="CON-D9-003", title="D9 他人合同", customer="D9 客户", status="草稿", owner=ADMIN["username"], department=USER["department"],
                data={"contract_guid": FOREIGN_GUID},
            )
            db.add_all([contract, archived, foreign])
            await db.flush()
            db.add_all([
                ContractEvent(contract_record_id=contract.id, content="历史事项一", operator=USER["username"]),
                ContractEvent(contract_record_id=contract.id, content="历史事项二", operator=ADMIN["username"]),
            ])
            await db.commit()
            self.contract_id = contract.id
            self.archived_id = archived.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://contract-d9.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_guid_event_list_supports_paging_keyword_and_legacy_shape(self):
        legacy = await self.client.get(f"{API}/contracts/guid/{GUID}/events")
        self.assertEqual(legacy.status_code, status.HTTP_200_OK)
        self.assertEqual(legacy.json()["total"], 2)
        self.assertNotIn("page", legacy.json())
        paged = await self.client.get(f"{API}/contracts/guid/{GUID}/events", params={"page": 1, "page_size": 1, "keyword": "历史事项二"})
        self.assertEqual(paged.status_code, status.HTTP_200_OK)
        self.assertEqual((paged.json()["total"], paged.json()["page"], paged.json()["page_size"], paged.json()["pages"]), (1, 1, 1, 1))
        self.assertEqual(paged.json()["items"][0]["content"], "历史事项二")

    async def test_guid_event_create_audits_and_rejects_empty_or_archived(self):
        created = await self.client.post(f"{API}/contracts/guid/{GUID}/events", json={"content": "Guid 新事项"})
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.json()["contract_guid"], GUID)
        async with self.sessions() as db:
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.contract_id, WorkflowEvent.action == "新增合同事项"))
        self.assertIsNotNone(event)
        empty = await self.client.post(f"{API}/contracts/guid/{GUID}/events", json={"content": "   "})
        self.assertEqual(empty.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        archived = await self.client.post(f"{API}/contracts/guid/33333333-3333-4333-8333-333333333333/events", json={"content": "不应写入"})
        self.assertEqual(archived.status_code, status.HTTP_409_CONFLICT)

    async def test_guid_event_permission_and_not_found_boundaries(self):
        app.dependency_overrides[current_identity] = lambda: USER
        forbidden = await self.client.post(f"{API}/contracts/guid/{GUID}/events", json={"content": "本人可写"})
        self.assertEqual(forbidden.status_code, status.HTTP_201_CREATED)
        missing = await self.client.get(f"{API}/contracts/guid/99999999-9999-4999-8999-999999999999/events")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)
        forbidden = await self.client.get(f"{API}/contracts/guid/{FOREIGN_GUID}/events")
        self.assertEqual(forbidden.status_code, status.HTTP_404_NOT_FOUND)

    async def test_contract_create_and_update_preserve_stable_guid(self):
        created = await self.client.post(f"{API}/contracts", json={
            "serial_no": "CON-D9-NEW", "title": "D9 新合同", "customer": "D9 客户",
            "owner": ADMIN["username"], "department": ADMIN["department"], "data": {"contract_guid": FOREIGN_GUID},
        })
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        guid = created.json()["data"]["contract_guid"]
        self.assertTrue(guid)
        self.assertNotEqual(guid, FOREIGN_GUID)
        updated = await self.client.patch(f"{API}/contracts/{created.json()['id']}", json={
            "serial_no": "CON-D9-NEW", "title": "D9 新合同已更新", "customer": "D9 客户",
            "owner": ADMIN["username"], "department": ADMIN["department"], "data": {"contract_guid": GUID},
        })
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)
        self.assertEqual(updated.json()["data"]["contract_guid"], guid)


if __name__ == "__main__":
    unittest.main()

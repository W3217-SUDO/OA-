"""Runtime contracts for customer-center backend alignment, isolated from legal_platform.db."""

import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, RolePermission, SystemParameter, User, WorkflowEvent
from app.security import current_identity


ADMIN = {"username": "customer-admin", "role": "admin", "display_name": "客户管理员", "department": "上海分所"}
AUDITOR = {"username": "customer-auditor", "role": "auditor", "display_name": "客户审计员", "department": "上海分所"}
API = settings.api_prefix
CUSTOMER_GUID = "11111111-1111-4111-8111-111111111111"


class CustomerBackendAlignmentD6Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [
            User.__table__, RolePermission.__table__, BusinessRecord.__table__,
            WorkflowEvent.__table__, FileAttachment.__table__, SystemParameter.__table__,
        ]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

        self.upload_root = Path(tempfile.mkdtemp(prefix="codex-customer-d6-"))
        from app import main as main_module
        self.main_module = main_module
        self.original_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root
        file_path = self.upload_root / "customer-contract.pdf"
        file_path.write_bytes(b"customer-file-d6")

        async with self.sessions() as db:
            db.add(User(username="customer-auditor", display_name="客户审计员", department="上海分所", role="auditor", password_hash="test", is_active=True))
            db.add(User(username="customer-admin", display_name="客户管理员", department="上海分所", role="admin", password_hash="test", is_active=True))
            db.add(SystemParameter(category="customer_type", code="customer", name="客户", is_active=True))
            customer = BusinessRecord(
                module="customer", serial_no="KH-D6-001", title="D6 客户", customer="D6 客户",
                status="正常", owner="customer-auditor", department="上海分所",
                data={
                    "customer_guid": CUSTOMER_GUID,
                    "customer_managers": ["customer-auditor"],
                    "shared_with": ["manager-one"], "is_shared": "是", "credit_code": "OLD-CREDIT",
                    "phone": "021-00000000",
                    "contacts": [
                        {"id": "contact-1", "name": "联系人一", "phone": "13800000001", "is_valid": True, "is_primary": True},
                        {"id": "contact-2", "name": "联系人二", "phone": "13800000002", "is_valid": True, "is_primary": False},
                    ],
                },
            )
            db.add(customer)
            await db.flush()
            db.add_all([
                FileAttachment(record_id=customer.id, category="客户文件", original_name="customer-contract.pdf", stored_name="customer-contract.pdf", content_type="application/pdf", size=16, path=str(file_path), uploader="customer-admin"),
            ])
            await db.commit()
            self.customer_id = customer.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://customer-center.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.main_module.UPLOAD_ROOT = self.original_upload_root
        shutil.rmtree(self.upload_root, ignore_errors=True)
        await self.engine.dispose()

    async def test_guid_shared_objects_assignment_history_and_failed_assignment_are_atomic(self):
        shared = await self.client.get(f"{API}/customers/{self.customer_id}/shared-objects")
        self.assertEqual(shared.status_code, status.HTTP_200_OK)
        self.assertEqual(shared.json()["customer_guid"], CUSTOMER_GUID)
        self.assertEqual(shared.json()["items"], ["manager-one"])
        shared_post = await self.client.post(f"{API}/customers/{self.customer_id}/shared-objects")
        self.assertEqual(shared_post.status_code, status.HTTP_200_OK)
        self.assertEqual(shared_post.json()["items"], ["manager-one"])

        changed = await self.client.put(f"{API}/customers/{self.customer_id}/managers", json={"managers": ["customer-admin"], "comment": "负责人变更"})
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        history = await self.client.get(f"{API}/customers/{self.customer_id}/assignment-history")
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(history.json()["items"][-1]["to_owner"], "customer-admin")
        before_count = history.json()["total"]
        async with self.sessions() as db:
            before_events = len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
        failed = await self.client.put(f"{API}/customers/{self.customer_id}/managers", json={"managers": ["missing-user"], "comment": "不应写入"})
        self.assertEqual(failed.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        after_failed = await self.client.get(f"{API}/customers/{self.customer_id}/assignment-history")
        self.assertEqual(after_failed.json()["total"], before_count)
        async with self.sessions() as db:
            after_events = len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
        self.assertEqual(after_events, before_events)

    async def test_empty_shared_objects_returns_frontend_placeholder(self):
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, self.customer_id)
            customer.data = {**(customer.data or {}), "shared_with": [], "is_shared": "否"}
            await db.commit()
        response = await self.client.get(f"{API}/customers/{self.customer_id}/shared-objects")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["items"], [{}])
        self.assertEqual(response.json()["customer_guid"], CUSTOMER_GUID)

    async def test_guid_events_and_files_list_and_download(self):
        listed = await self.client.get(f"{API}/customers/guid/{CUSTOMER_GUID}/events")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        created = await self.client.post(f"{API}/customers/guid/{CUSTOMER_GUID}/events", json={"action": "客户事件", "comment": "按 Guid 新增"})
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        events = await self.client.get(f"{API}/customers/guid/{CUSTOMER_GUID}/events")
        self.assertEqual(events.json()["items"][-1]["action"], "客户事件")

        files = await self.client.get(f"{API}/customers/guid/{CUSTOMER_GUID}/files")
        self.assertEqual(files.status_code, status.HTTP_200_OK)
        self.assertEqual(files.json()["items"][0]["original_name"], "customer-contract.pdf")
        download = await self.client.get(f"{API}/customers/guid/{CUSTOMER_GUID}/files/{files.json()['items'][0]['id']}/download")
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(download.content, b"customer-file-d6")

    async def test_contacts_paging_default_and_active_primary_switch(self):
        contacts = await self.client.get(f"{API}/customers/{self.customer_id}/contacts", params={"page": 1, "page_size": 1})
        self.assertEqual(contacts.status_code, status.HTTP_200_OK)
        self.assertEqual((contacts.json()["total"], contacts.json()["page_size"]), (2, 1))
        switched = await self.client.patch(f"{API}/customers/{self.customer_id}/contacts/contact-2/status", json={"is_valid": False, "is_primary": True})
        self.assertEqual(switched.status_code, status.HTTP_200_OK)
        self.assertTrue(switched.json()["is_primary"])
        self.assertFalse(switched.json()["is_valid"])
        refreshed = await self.client.get(f"{API}/customers/{self.customer_id}/contacts")
        rows = {item["id"]: item for item in refreshed.json()["items"]}
        self.assertFalse(rows["contact-1"]["is_primary"])
        self.assertTrue(rows["contact-2"]["is_primary"])

    async def test_empty_contact_status_patch_is_rejected_without_audit(self):
        async with self.sessions() as db:
            before = len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
        for payload in ({}, {"is_primary": False}):
            response = await self.client.patch(f"{API}/customers/{self.customer_id}/contacts/contact-1/status", json=payload)
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        async with self.sessions() as db:
            after = len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
        self.assertEqual(after, before)

    async def test_recycle_blocks_customers_with_linked_contracts_or_cases(self):
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, self.customer_id)
            db.add(BusinessRecord(
                module="contract", serial_no="HT-D6-BLOCK", title="D6 关联合同",
                customer=customer.title, status="履行中", owner="customer-admin", department="上海分所",
                data={"customer_id": customer.id, "customer_no": customer.serial_no},
            ))
            before_events = len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
            await db.commit()

        response = await self.client.post(f"{API}/customers/{self.customer_id}/recycle", json={"comment": "不应删除"})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("客户存在1 个合同", response.json()["detail"])

        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, self.customer_id)
            self.assertEqual(customer.status, "正常")
            after_events = len((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
        self.assertEqual(after_events, before_events)

    async def test_auto_customer_serial_uses_legacy_short_sequence(self):
        serial_prefix = f"SHKH{datetime.now():%y}"
        async with self.sessions() as db:
            db.add(BusinessRecord(
                module="customer", serial_no=f"{serial_prefix}00007", title="CODEX-I11-existing",
                customer="CODEX-I11-existing", status="潜在", owner="customer-admin",
                department="上海分所", data={"customer_type": "客户", "level": "立案客户"},
            ))
            await db.commit()

        response = await self.client.post(f"{API}/customers", json={
            "title": "CODEX-I11-auto-serial",
            "status": "潜在",
            "owner": "customer-admin",
            "customer_type": "客户",
            "level": "立案客户",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        serial_no = response.json()["serial_no"]
        self.assertEqual(serial_no, f"{serial_prefix}00008")
        self.assertRegex(serial_no, r"^SHKH\d{7}$")
        self.assertNotRegex(serial_no, r"\d{10,}")

    async def test_identity_field_filtering_and_workflow_audit(self):
        app.dependency_overrides[current_identity] = lambda: AUDITOR
        updated = await self.client.patch(f"{API}/customers/{self.customer_id}", json={"data": {"phone": "021-99999999", "credit_code": "FORBIDDEN-CREDIT"}, "description": "更新备注"})
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.json()["data"]["phone"], "021-99999999")
        self.assertNotEqual(updated.json()["data"].get("credit_code"), "FORBIDDEN-CREDIT")
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, self.customer_id)
            self.assertNotEqual((customer.data or {}).get("credit_code"), "FORBIDDEN-CREDIT")
            actions = {event.action for event in (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all()}
        self.assertIn("更新客户资料", actions)


if __name__ == "__main__":
    unittest.main()

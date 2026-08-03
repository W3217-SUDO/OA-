"""Runtime contracts for customer-file metadata and contact state fields."""

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
CUSTOMER_GUID = "d11-customer-guid"
ADMIN = {"username": "d11-admin", "role": "admin", "display_name": "客户管理员", "department": "上海分所"}
OUTSIDER = {"username": "d11-outsider", "role": "user", "display_name": "普通员工", "department": "上海分所"}


class CustomerFileContactBackendD11Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [User.__table__, RolePermission.__table__, BusinessRecord.__table__, WorkflowEvent.__table__, FileAttachment.__table__]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
        self.upload_root = Path(tempfile.mkdtemp(prefix="codex-customer-d11-"))
        from app import main as main_module

        self.main_module = main_module
        self.original_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root
        async with self.sessions() as db:
            db.add(User(username="d11-outsider", display_name="普通员工", department="上海分所", role="user", password_hash="test", is_active=True))
            customer = BusinessRecord(
                module="customer",
                serial_no="KH-D11-001",
                title="D11 客户",
                customer="D11 客户",
                status="正常",
                owner="d11-admin",
                department="上海分所",
                data={
                    "customer_guid": CUSTOMER_GUID,
                    "contacts": [
                        {
                            "id": "legacy-contact",
                            "name": "旧联系人",
                            "email": "",
                            "contact_status": "停止联系",
                            "is_valid": True,
                            "is_primary": False,
                        }
                    ],
                },
            )
            other = BusinessRecord(
                module="customer",
                serial_no="KH-D11-002",
                title="D11 其他客户",
                customer="D11 其他客户",
                status="正常",
                owner="d11-admin",
                department="上海分所",
                data={"customer_guid": "d11-other-guid", "contacts": []},
            )
            case = BusinessRecord(
                module="case",
                serial_no="D11-CASE-001",
                title="D11 非客户记录",
                customer="",
                status="在办",
                owner="d11-admin",
                department="上海分所",
                data={},
            )
            db.add_all([customer, other, case])
            await db.flush()
            await db.commit()
            self.customer_id = customer.id
            self.other_customer_id = other.id
            self.case_id = case.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://customer-d11.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.main_module.UPLOAD_ROOT = self.original_upload_root
        shutil.rmtree(self.upload_root, ignore_errors=True)
        await self.engine.dispose()

    async def test_customer_upload_persists_and_projects_guid_license_and_document_date(self):
        response = await self.client.post(
            f"{API}/attachments",
            data={
                "record_id": str(self.customer_id),
                "customer_guid": CUSTOMER_GUID,
                "is_license": "true",
                "document_date": "2026-08-03",
                "category": "客户文件",
                "remark": "营业执照",
            },
            files={"file": ("license.pdf", b"pdf-d11", "application/pdf")},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.text)
        attachment = response.json()
        self.assertEqual(attachment["customer_guid"], CUSTOMER_GUID)
        self.assertTrue(attachment["is_license"])
        self.assertEqual(attachment["document_date"], "2026-08-03")
        async with self.sessions() as db:
            row = await db.get(FileAttachment, attachment["id"])
            self.assertIsNotNone(row)
            self.assertTrue(row.is_license)
            self.assertEqual(row.document_date, date(2026, 8, 3))
        listed = await self.client.get(f"{API}/customers/guid/{CUSTOMER_GUID}/files")
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.text)
        self.assertEqual(listed.json()["items"][0]["customer_guid"], CUSTOMER_GUID)
        self.assertTrue(listed.json()["items"][0]["is_license"])
        self.assertEqual(listed.json()["items"][0]["document_date"], "2026-08-03")

    async def test_customer_guid_mismatch_is_409_and_does_not_write(self):
        response = await self.client.post(
            f"{API}/attachments",
            data={"record_id": str(self.customer_id), "customer_guid": "d11-other-guid", "is_license": "false"},
            files={"file": ("wrong.pdf", b"wrong", "application/pdf")},
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT, response.text)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(FileAttachment.id).where(FileAttachment.original_name == "wrong.pdf")), None)
            self.assertEqual(await db.scalar(select(WorkflowEvent.id).where(WorkflowEvent.record_id == self.customer_id)), None)
        blank = await self.client.post(
            f"{API}/attachments",
            data={"record_id": str(self.customer_id), "customer_guid": ""},
            files={"file": ("blank-guid.pdf", b"blank", "application/pdf")},
        )
        self.assertEqual(blank.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, blank.text)

    async def test_customer_only_metadata_rejects_missing_record_or_guid_without_writes(self):
        scenarios = [
            ("no-record", {}, {"is_license": "true", "document_date": "2026-08-03", "customer_guid": CUSTOMER_GUID}),
            ("non-customer", {"record_id": str(self.case_id)}, {"is_license": "true", "document_date": "2026-08-03", "customer_guid": CUSTOMER_GUID}),
            ("explicit-false", {"record_id": str(self.case_id)}, {"is_license": "false"}),
            ("missing-guid", {"record_id": str(self.customer_id)}, {"is_license": "true", "document_date": "2026-08-03"}),
        ]
        for name, base_data, metadata in scenarios:
            response = await self.client.post(
                f"{API}/attachments",
                data={**base_data, **metadata},
                files={"file": (f"{name}.pdf", b"rejected", "application/pdf")},
            )
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, response.text)
        async with self.sessions() as db:
            for name, _, _ in scenarios:
                self.assertIsNone(await db.scalar(select(FileAttachment.id).where(FileAttachment.original_name == f"{name}.pdf")))
            self.assertEqual(await db.scalar(select(WorkflowEvent.id).where(WorkflowEvent.action.like("%客户文件%"))), None)
        self.assertEqual(list(self.upload_root.iterdir()), [])

    async def test_customer_attachment_without_special_metadata_remains_compatible(self):
        response = await self.client.post(
            f"{API}/attachments",
            data={"record_id": str(self.customer_id), "category": "客户文件"},
            files={"file": ("ordinary.pdf", b"ordinary", "application/pdf")},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.text)
        self.assertFalse(response.json()["is_license"])
        self.assertIsNone(response.json()["document_date"])

    async def test_customer_upload_requires_customer_write_scope(self):
        app.dependency_overrides[current_identity] = lambda: OUTSIDER
        response = await self.client.post(
            f"{API}/attachments",
            data={"record_id": str(self.customer_id), "customer_guid": CUSTOMER_GUID},
            files={"file": ("forbidden.pdf", b"forbidden", "application/pdf")},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.text)

    async def test_contacts_project_independent_snake_case_flags_without_inference(self):
        listed = await self.client.get(f"{API}/customers/{self.customer_id}/contacts")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        legacy = listed.json()["items"][0]
        self.assertTrue(legacy["is_received_email"])
        self.assertTrue(legacy["is_contacted"])
        self.assertTrue(legacy["is_people_base"])

        created = await self.client.post(
            f"{API}/customers/{self.customer_id}/contacts",
            json={
                "name": "D11 联系人",
                "email": "",
                "contact_status": "停止联系",
                "is_valid": False,
                "is_primary": False,
                "is_received_email": False,
                "is_contacted": False,
                "is_people_base": False,
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        created_contact = created.json()
        self.assertEqual(
            {created_contact["is_received_email"], created_contact["is_contacted"], created_contact["is_people_base"]},
            {False},
        )
        contact_id = created_contact["id"]
        updated = await self.client.put(
            f"{API}/customers/{self.customer_id}/contacts/{contact_id}",
            json={
                "name": "D11 联系人",
                "email": "",
                "contact_status": "停止联系",
                "is_valid": False,
                "is_primary": False,
                "is_received_email": True,
                "is_contacted": True,
                "is_people_base": True,
            },
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)
        self.assertTrue(updated.json()["is_received_email"])
        self.assertTrue(updated.json()["is_contacted"])
        self.assertTrue(updated.json()["is_people_base"])
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, self.customer_id)
            persisted = next(item for item in customer.data["contacts"] if item["id"] == contact_id)
            self.assertEqual(persisted["is_received_email"], True)
            self.assertEqual(persisted["is_contacted"], True)
            self.assertEqual(persisted["is_people_base"], True)
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.customer_id))).all())
            self.assertTrue(any("is_received_email" in (event.comment or "") for event in events))
            self.assertTrue(any("is_contacted" in (event.comment or "") for event in events))
            self.assertTrue(any("is_people_base" in (event.comment or "") for event in events))


if __name__ == "__main__":
    unittest.main()

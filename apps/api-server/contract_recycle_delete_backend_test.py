"""In-process backend tests for the contract recycle bin and whole-record delete.

The recycle list uses the shared /records contract projection with scope=recycle,
and the delete endpoint follows the legacy FCM ContractDelete envelope while
removing attachment rows and physical files together with the contract record.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
RECYCLED = "\u5df2\u56de\u6536"  # ???
DRAFT = "\u8349\u7a3f"  # ??
ATTACHMENT_CATEGORY = "\u5408\u540c\u9644\u4ef6"  # ????
RECYCLE_MENU = '    ("contract-recycle", "contract", "\u5408\u540c\u56de\u6536\u7ad9", "", 57),'
RECYCLE_BIN = "\u56de\u6536\u7ad9"
NOT_FOUND_MSG = "\u4e0d\u5b58\u5728\u6216\u5df2\u5220\u9664"
ADMIN_ONLY_MSG = "\u4ec5\u7ba1\u7406\u5458\u53ef\u4ee5\u5220\u9664\u5408\u540c"


class ContractRecycleDeleteBackendTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.upload_root = Path(tempfile.mkdtemp(prefix="codex-contract-recycle-"))
        from app import main as main_module
        self.main_module = main_module
        self.original_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root

        async with self.sessions() as db:
            db.add(User(username="contract-admin", display_name="contract-admin", department="Shanghai", role="admin", password_hash="test", is_active=True))
            db.add(User(username="contract-user", display_name="contract-user", department="Shanghai", role="user", password_hash="test", is_active=True))
            recycled = BusinessRecord(
                module="contract", serial_no="CODEX-CONTRACT-RECYCLE-001", title="recycle target",
                customer="CODEX customer", status=RECYCLED, owner="contract-admin",
                department="Shanghai", description="recycle test", data={},
            )
            draft = BusinessRecord(
                module="contract", serial_no="CODEX-CONTRACT-DRAFT-001", title="draft target",
                customer="CODEX customer", status=DRAFT, owner="contract-admin",
                department="Shanghai", description="recycle test", data={},
            )
            db.add_all([recycled, draft])
            await db.flush()
            self.recycled_id = recycled.id
            self.draft_id = draft.id
            self.attachment_path = self.upload_root / "contract-recycle.pdf"
            self.attachment_path.write_bytes(b"contract-recycle-file")
            db.add(FileAttachment(
                record_id=recycled.id, category=ATTACHMENT_CATEGORY,
                original_name="contract-recycle.pdf", stored_name="contract-recycle.pdf",
                content_type="application/pdf", size=21, path=str(self.attachment_path),
                uploader="contract-admin",
            ))
            db.add(WorkflowEvent(
                record_id=recycled.id, action="move-to-recycle", from_status=DRAFT,
                to_status=RECYCLED, operator="contract-admin", comment="recycle test",
            ))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: {
            "username": "contract-admin", "role": "admin",
            "display_name": "contract-admin", "department": "Shanghai",
        }
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://contract-recycle.test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.main_module.UPLOAD_ROOT = self.original_upload_root
        shutil.rmtree(self.upload_root, ignore_errors=True)
        await self.engine.dispose()

    async def test_recycle_menu_and_scope_isolate_recycled_contracts(self):
        main_source = Path(__file__).resolve().parent / "app" / "main.py"
        self.assertIn(RECYCLE_MENU, main_source.read_text(encoding="utf-8"))

        response = await self.client.get(
            f"{API}/records", params={"module": "contract", "scope": "recycle", "page_size": 100}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["id"], self.recycled_id)
        self.assertEqual(payload["items"][0]["status"], RECYCLED)

        drafts = await self.client.get(
            f"{API}/records",
            params={"module": "contract", "scope": "all", "statuses": DRAFT, "page_size": 100},
        )
        self.assertEqual(drafts.status_code, status.HTTP_200_OK, drafts.text)
        self.assertEqual(drafts.json()["total"], 1)
        self.assertEqual(drafts.json()["items"][0]["id"], self.draft_id)

    async def test_whole_delete_removes_record_attachments_and_physical_file(self):
        response = await self.client.post(
            f"{API}/contracts/delete", json={"contractIds": [self.recycled_id]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        body = response.json()
        self.assertTrue(body["IsSuccess"])
        self.assertEqual(body["deleted"], 1)

        async with self.sessions() as db:
            self.assertIsNone(await db.get(BusinessRecord, self.recycled_id))
            self.assertIsNone(await db.scalar(select(FileAttachment.id).where(FileAttachment.record_id == self.recycled_id)))
            self.assertIsNone(await db.scalar(select(WorkflowEvent.id).where(WorkflowEvent.record_id == self.recycled_id)))
        self.assertFalse(self.attachment_path.exists())

    async def test_whole_delete_failures_keep_records_and_files(self):
        bad_status = await self.client.post(f"{API}/contracts/delete", json={"contractIds": [self.draft_id]})
        self.assertEqual(bad_status.status_code, status.HTTP_200_OK, bad_status.text)
        self.assertFalse(bad_status.json()["IsSuccess"])
        self.assertIn(RECYCLE_BIN, bad_status.json()["Message"])

        missing = await self.client.post(f"{API}/contracts/delete", json={"contractIds": [999999]})
        self.assertEqual(missing.status_code, status.HTTP_200_OK, missing.text)
        self.assertFalse(missing.json()["IsSuccess"])
        self.assertIn(NOT_FOUND_MSG, missing.json()["Message"])

        app.dependency_overrides[current_identity] = lambda: {
            "username": "contract-user", "role": "user",
            "display_name": "contract-user", "department": "Shanghai",
        }
        forbidden = await self.client.post(f"{API}/contracts/delete", json={"contractIds": [self.recycled_id]})
        self.assertEqual(forbidden.status_code, status.HTTP_200_OK, forbidden.text)
        self.assertFalse(forbidden.json()["IsSuccess"])
        self.assertIn(ADMIN_ONLY_MSG, forbidden.json()["Message"])

        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(BusinessRecord, self.draft_id))
            self.assertIsNotNone(await db.get(BusinessRecord, self.recycled_id))
            self.assertIsNotNone(await db.scalar(select(FileAttachment.id).where(FileAttachment.record_id == self.recycled_id)))
        self.assertTrue(self.attachment_path.exists())


if __name__ == "__main__":
    unittest.main()

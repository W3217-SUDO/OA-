"""Dedicated IPR case assisted-fee workflow contract.

The user-facing 协助费 label maps to the legacy CaseAssistedFee subsidy entity.
This test proves it remains a case-bound workflow instead of a generic finance
record and that the explicit confirmation state precedes receipt handling.
"""

from datetime import date, datetime, timezone
from pathlib import Path
import shutil
import tempfile
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app import main as main_module
from app.main import app
from app.models import BusinessRecord, FileAttachment, IprCaseAssistedFee, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix


class IprCaseAssistedFeeWorkflowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {
            "username": "CODEX-IPR-ASSISTED-admin", "role": "admin",
            "display_name": "CODEX IPR Assisted Admin", "department": "IPR",
        }
        async with self.sessions() as db:
            db.add_all([
                User(username="CODEX-IPR-ASSISTED-admin", display_name="CODEX IPR Assisted Admin", department="IPR", password_hash="fixture", role="admin"),
                User(username="CODEX-IPR-ASSISTED-outsider", display_name="CODEX IPR Assisted Outsider", department="Other", password_hash="fixture", role="user"),
                User(username="CODEX-IPR-ASSISTED-manager", display_name="CODEX IPR Assisted Manager", department="IPR", password_hash="fixture", role="manager"),
            ])
            self.case_id = await self._add_record(db, "ipr_case", "在办", "CODEX-IPR-ASSISTED-001")
            self.other_case_id = await self._add_record(db, "ipr_case", "在办", "CODEX-IPR-ASSISTED-002")
            self.archived_case_id = await self._add_record(db, "ipr_case", "已归档", "CODEX-IPR-ASSISTED-ARCHIVED")
            self.generic_record_id = await self._add_record(db, "finance", "草稿", "CODEX-IPR-ASSISTED-GENERIC")
            await db.commit()
        self.upload_root = Path(tempfile.mkdtemp(prefix="codex-ipr-assisted-fee-"))
        self.original_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr-assisted.test")

    async def _add_record(self, db: AsyncSession, module: str, status: str, serial_no: str) -> int:
        record = BusinessRecord(
            module=module, serial_no=serial_no, title=serial_no, customer="CODEX customer",
            status=status, owner="CODEX-IPR-ASSISTED-admin", department="IPR",
            data={}, created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
            updated_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
        )
        db.add(record); await db.flush()
        return record.id

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        main_module.UPLOAD_ROOT = self.original_upload_root
        await self.engine.dispose()
        shutil.rmtree(self.upload_root)
        self.assertFalse(self.upload_root.exists(), "协助费测试回执目录未清理")

    async def _create(self, case_id: int | None = None, assisted_type: str = "专利资助") -> httpx.Response:
        return await self.client.post(
            f"{API}/ipr/cases/{case_id or self.case_id}/assisted-fees",
            json={"assisted_type": assisted_type, "remark": "CODEX workflow fixture"},
        )

    async def test_create_edit_confirm_handle_and_persist_audit_receipt(self):
        created = await self._create()
        self.assertEqual(created.status_code, 201, created.text)
        fee = created.json()
        self.assertEqual(fee["status"], "待确认")
        fee_id = fee["id"]
        blank_type = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees",
            json={"assisted_type": "   ", "remark": "invalid"},
        )
        self.assertEqual(blank_type.status_code, 422, blank_type.text)

        direct_handle = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/transact",
            data={"response_date": "2026-09-05"},
            files={"file": ("receipt.pdf", b"CODEX receipt", "application/pdf")},
        )
        self.assertEqual(direct_handle.status_code, 409, direct_handle.text)

        edited = await self.client.patch(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}",
            json={"assisted_type": "商标资助", "remark": "CODEX edited fixture"},
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["assisted_type"], "商标资助")

        confirmed = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/confirm",
            json={"remark": "CODEX confirmed fixture"},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["status"], "待办理")
        repeated_confirm = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/confirm", json={},
        )
        self.assertEqual(repeated_confirm.status_code, 409, repeated_confirm.text)
        self.assertEqual((await self.client.patch(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}",
            json={"assisted_type": "其他资助", "remark": "blocked"},
        )).status_code, 409)
        invalid_file = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/transact",
            data={"response_date": "2026-09-05"},
            files={"file": ("receipt.txt", b"bad extension", "text/plain")},
        )
        self.assertEqual(invalid_file.status_code, 422, invalid_file.text)
        empty_file = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/transact",
            data={"response_date": "2026-09-05"},
            files={"file": ("receipt.pdf", b"", "application/pdf")},
        )
        self.assertEqual(empty_file.status_code, 422, empty_file.text)

        handled = await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/transact",
            data={"response_date": "2026-09-05", "remark": "CODEX handled fixture"},
            files={"file": ("receipt.pdf", b"CODEX receipt", "application/pdf")},
        )
        self.assertEqual(handled.status_code, 200, handled.text)
        payload = handled.json()
        self.assertEqual(payload["status"], "已办理")
        self.assertEqual(payload["receipt"]["original_name"], "receipt.pdf")
        self.assertEqual((await self.client.post(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}/transact",
            data={"response_date": "2026-09-05"},
            files={"file": ("receipt.pdf", b"repeat", "application/pdf")},
        )).status_code, 409)

        listed = await self.client.get(f"{API}/ipr/cases/{self.case_id}/assisted-fees")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertTrue(listed.json()["capabilities"]["can_manage"])
        self.assertEqual(listed.json()["items"][0]["request_user"], self.identity["username"])
        self.assertTrue(listed.json()["items"][0]["request_user_display_name"])
        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))).all())
            attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == self.case_id))).all())
        self.assertEqual(len(attachments), 1)
        self.assertTrue(Path(attachments[0].path).is_file())
        self.assertEqual((await self.client.get(
            f"{API}/attachments/{payload['receipt']['id']}/download"
        )).status_code, 200)
        self.assertTrue(any(event.action == "确认知识产权案件协助费" and f"协助费 #{fee_id}" in event.comment for event in events))
        self.assertTrue(any(event.action == "办理知识产权案件协助费" for event in events))
        self.assertEqual((await self.client.delete(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}"
        )).status_code, 409)

    async def test_rejects_cross_case_archived_generic_and_unauthorized_mutations(self):
        created = await self._create()
        fee_id = created.json()["id"]
        cross_case = await self.client.patch(
            f"{API}/ipr/cases/{self.other_case_id}/assisted-fees/{fee_id}",
            json={"assisted_type": "商标资助", "remark": "cross case"},
        )
        self.assertEqual(cross_case.status_code, 404, cross_case.text)
        archived = await self._create(self.archived_case_id)
        self.assertEqual(archived.status_code, 409, archived.text)
        generic = await self._create(self.generic_record_id)
        self.assertEqual(generic.status_code, 404, generic.text)
        self.identity = {"username": "CODEX-IPR-ASSISTED-outsider", "role": "user", "department": "Other"}
        outsider_list = await self.client.get(f"{API}/ipr/cases/{self.case_id}/assisted-fees")
        self.assertIn(outsider_list.status_code, {403, 404}, outsider_list.text)
        unauthorized = await self.client.delete(f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}")
        self.assertIn(unauthorized.status_code, {403, 404}, unauthorized.text)
        self.identity = {"username": "CODEX-IPR-ASSISTED-manager", "role": "manager", "department": "IPR"}
        self.assertTrue((await self.client.get(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees"
        )).json()["capabilities"]["can_manage"])

    async def test_pending_confirmation_and_legacy_pending_handle_rows_can_be_deleted(self):
        created = await self._create()
        self.assertEqual((await self.client.delete(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{created.json()['id']}"
        )).status_code, 204)
        async with self.sessions() as db:
            legacy_pending = IprCaseAssistedFee(
                case_record_id=self.case_id, assisted_type="高新技术资助", status="待办理",
                request_date=date(2026, 9, 5), request_user="CODEX-IPR-ASSISTED-admin", response_user="", remark="legacy fixture",
            )
            archived_pending = IprCaseAssistedFee(
                case_record_id=self.archived_case_id, assisted_type="旧资助", status="待办理",
                request_date=date(2026, 9, 5), request_user="CODEX-IPR-ASSISTED-admin", response_user="", remark="archived fixture",
            )
            db.add_all([legacy_pending, archived_pending]); await db.commit(); await db.refresh(legacy_pending); await db.refresh(archived_pending)
            fee_id = legacy_pending.id
            archived_fee_id = archived_pending.id
        self.assertEqual((await self.client.delete(
            f"{API}/ipr/cases/{self.case_id}/assisted-fees/{fee_id}"
        )).status_code, 204)
        self.assertEqual((await self.client.delete(
            f"{API}/ipr/cases/{self.archived_case_id}/assisted-fees/{archived_fee_id}"
        )).status_code, 409)


if __name__ == "__main__":
    unittest.main()

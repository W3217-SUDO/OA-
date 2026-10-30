"""费用票据删除仅使用内存数据库和本任务临时附件。"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
from unittest.mock import patch
import unittest

import httpx
from sqlalchemy import event, select, text
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import DEFAULT_JOB_ROLES
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, FinanceTransaction, JobRole, LegacyFinanceFile, RolePermission, User, WorkflowEvent
from app.security import current_identity
from tests.personnel_role_fixture import bind_system_role_pages


class CaseFeeFiles1012Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.temp = TemporaryDirectory(prefix="CODEX-fee-files-")
        self.path = Path(self.temp.name) / "CODEX-original.pdf"
        self.path.write_bytes(b"CODEX isolated attachment")
        self.identity = {"username": "CODEX-admin", "role": "admin"}
        async with self.sessions() as db:
            db.add_all([User(username="CODEX-admin", display_name="管理员", role="admin", password_hash="x", is_active=True),
                        User(username="CODEX-finance", display_name="财务", role="user", password_hash="x", is_active=True),
                        User(username="CODEX-owner", display_name="经办人", role="user", password_hash="x", is_active=True)])
            # 使用既有财务处理菜单，不人为给财务账号塞 case.fee.delete。
            db.add(RolePermission(role="user", display_name="普通账号", menu_keys=["case", "finance-invoice-pending"], field_keys=["finance.amount"], data_scope="全所数据"))
            case = BusinessRecord(module="case", serial_no="CODEX-1012-CASE", title="隔离案件", status="已归档", owner="CODEX-owner", data={})
            db.add(case); await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-1012-FEE", title="官费", status="已付款", owner="CODEX-owner", data={"case_id": case.id, "case_no": case.serial_no, "amount": 100, "paid_amount": 100, "expense_scope": "律所", "paid_date": "2026-10-12"})
            db.add(fee); await db.flush()
            file = FileAttachment(record_id=fee.id, category="案件票据文件", original_name="CODEX-proof.pdf", stored_name="CODEX-file", path=str(self.path), uploader="CODEX-admin", size=25)
            shared = FileAttachment(record_id=fee.id, category="案件票据文件", original_name="CODEX-other.pdf", stored_name="CODEX-shared", path=str(self.path), uploader="CODEX-admin", size=25)
            db.add_all([file, shared]); await db.flush()
            fee.data = {**fee.data, "receipt_files": [{"attachment_id": file.id, "bill_no": "CODEX-NO", "bill_date": "2026-10-12"}, {"attachment_id": shared.id, "bill_no": "CODEX-OTHER"}]}
            await db.commit()
            self.case_id, self.fee_id, self.file_id, self.shared_id = case.id, fee.id, file.id, shared.id
        self.overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.database
        app.dependency_overrides[current_identity] = lambda: dict(self.identity)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://isolated.test")
        await bind_system_role_pages(self.sessions)

    async def database(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.overrides)
        await self.engine.dispose()
        self.temp.cleanup()

    def url(self, attachment=None):
        base = f"{settings.api_prefix}/cases/{self.case_id}/fees/{self.fee_id}/files"
        return f"{base}/{attachment}" if attachment else base

    async def test_admin_delete_keeps_storage_amount_status_and_audit(self):
        response = await self.client.delete(self.url(self.file_id))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(self.path.is_file())
        async with self.sessions() as db:
            self.assertIsNone(await db.get(FileAttachment, self.file_id))
            self.assertIsNotNone(await db.get(FileAttachment, self.shared_id))
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(fee.status, "已付款")
            self.assertEqual(fee.data["amount"], 100)
            self.assertEqual(fee.data["paid_amount"], 100)
            self.assertEqual([row["attachment_id"] for row in fee.data["receipt_files"]], [self.shared_id])
            self.assertIsNotNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == fee.id, WorkflowEvent.action == "删除费用票据附件")))
        response = await self.client.get(self.url())
        self.assertEqual([row["attachment_id"] for row in response.json()["items"]], [self.shared_id])
        response = await self.client.delete(self.url(self.file_id))
        self.assertEqual(response.status_code, 404)
        response = await self.client.delete(self.url(self.shared_id))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.client.get(self.url())).json()["items"], [])
        self.assertTrue(self.path.is_file())

    async def test_finance_existing_menu_grant_and_revoke_checked_fresh(self):
        self.identity = {"username": "CODEX-finance", "role": "user"}
        response = await self.client.get(self.url())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["can_delete"])
        response = await self.client.delete(self.url(self.file_id))
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            grant = await db.scalar(select(RolePermission).where(RolePermission.role == "user"))
            grant.menu_keys = ["case", "@action:case.fee.receipt.view"]
            await db.commit()
            await bind_system_role_pages(db=db)
        response = await self.client.get(self.url())
        self.assertFalse(response.json()["can_delete"])
        response = await self.client.delete(self.url(self.shared_id))
        self.assertEqual(response.status_code, 403)

    async def test_owner_page_admin_capability_is_not_real_finance_permission(self):
        async with self.sessions() as db:
            grant = await db.scalar(select(RolePermission).where(RolePermission.role == "user"))
            grant.menu_keys = ["case", "@action:case.fee.receipt.view"]
            await db.commit()
            await bind_system_role_pages(db=db)
        self.identity = {"username": "CODEX-owner", "role": "admin", "role_ids": ["admin"], "_page_menu_capability": True, "action_keys": ["*"]}
        response = await self.client.get(self.url())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["can_delete"])
        self.assertEqual((await self.client.delete(self.url(self.file_id))).status_code, 403)

    async def test_platform_grant_is_not_firm_authority(self):
        self.identity = {"username": "CODEX-finance", "role": "user"}
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "expense_scope": "平台"}
            await db.commit()
        self.assertEqual((await self.client.delete(self.url(self.file_id))).status_code, 403)

    async def test_default_finance_jobs_have_real_grant_but_lawyer_does_not(self):
        self.identity = {"username": "CODEX-finance", "role": "user"}
        for code in ("FINANCE", "FINANCE-SPECIALIST", "FINANCE-SUPERVISOR", "HANDLING-LAWYER"):
            with self.subTest(job=code):
                role_code, name, permissions = next(item for item in DEFAULT_JOB_ROLES if item[0] == code)
                async with self.sessions() as db:
                    db.add(JobRole(code=role_code, name=name, permissions=permissions, is_active=True))
                    user = await db.scalar(select(User).where(User.username == "CODEX-finance"))
                    user.profile = {"permission_role_code": code}
                    await db.commit()
                response = await self.client.get(self.url())
                if code == "HANDLING-LAWYER":
                    self.assertTrue(response.status_code == 403 or not response.json()["can_delete"], response.text)
                    self.assertEqual((await self.client.delete(self.url(self.file_id))).status_code, 403)
                else:
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertTrue(response.json()["can_delete"])

    async def test_office_lock_offsets_preserve_instant_and_block_active_delete(self):
        now = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
        future = now + timedelta(minutes=15)
        async with self.sessions() as db:
            file = await db.get(FileAttachment, self.file_id)
            file.word_editor_lock_token = "CODEX-active-lease"
            file.word_editor_lock_expires_at = future
            await db.commit()

        expiry = future

        def retain_driver_offset(target, context):
            # SQLite 不保留时区；仅在测试 ORM 读取边界模拟带偏移的驱动返回值。
            if target.id == self.file_id:
                set_committed_value(target, "word_editor_lock_expires_at", expiry)

        event.listen(FileAttachment, "load", retain_driver_offset)
        try:
            with patch("app.areas.legal.case_fee_files._word_editor_now", return_value=now):
                for expiry in (future.astimezone(timezone(timedelta(hours=-8))),
                               future.astimezone(timezone(timedelta(hours=8))),
                               future.replace(tzinfo=None)):
                    with self.subTest(expires=expiry.isoformat()):
                        response = await self.client.delete(self.url(self.file_id))
                        self.assertEqual(response.status_code, 409, response.text)
                        self.assertIn("正在编辑", response.json()["detail"])
                        async with self.sessions() as db:
                            self.assertIsNotNone(await db.get(FileAttachment, self.file_id))
                            self.assertIsNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.action == "删除费用票据附件")))
                expiry = (now - timedelta(minutes=15)).astimezone(timezone(timedelta(hours=8)))
                response = await self.client.delete(self.url(self.file_id))
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(self.path.is_file())
        finally:
            event.remove(FileAttachment, "load", retain_driver_offset)

    async def test_cross_fee_reference_blocks_and_keeps_all_rows(self):
        async with self.sessions() as db:
            db.add(BusinessRecord(module="finance", serial_no="CODEX-OTHER-FEE", title="另一费用", owner="CODEX-admin", data={"receipt_files": [{"attachment_id": self.file_id}]}))
            await db.commit()
        response = await self.client.delete(self.url(self.file_id))
        self.assertEqual(response.status_code, 409, response.text)
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(FileAttachment, self.file_id))
            self.assertIsNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.action == "删除费用票据附件")))

    async def test_notice_metadata_cleanup_without_changing_business_status(self):
        async with self.sessions() as db:
            notice = BusinessRecord(module="finance_fee_inform", serial_no="CODEX-NOTICE", title="费用通知", owner="CODEX-admin", status="已票据确认", data={"source_fee_id": self.fee_id, "receipt_attachment_id": self.file_id, "bill_no": "CODEX-BILL", "bill_amount": 100, "locked": True})
            db.add(notice); await db.flush()
            file = await db.get(FileAttachment, self.file_id)
            file.record_id = notice.id; file.category = "案件费用通知票据"
            notice_id = notice.id
            await db.commit()
        response = await self.client.delete(self.url(self.file_id))
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            notice = await db.get(BusinessRecord, notice_id)
            self.assertIsNone(notice.data["receipt_attachment_id"])
            self.assertEqual(notice.data["bill_amount"], 100)
            self.assertEqual(notice.status, "已票据确认")

    async def test_commit_failure_rolls_back_metadata_file_and_audit(self):
        with patch.object(AsyncSession, "commit", side_effect=RuntimeError("CODEX transaction failure")):
            self.assertEqual((await self.client.delete(self.url(self.file_id))).status_code, 500)
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(FileAttachment, self.file_id))
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertIn(self.file_id, [item["attachment_id"] for item in fee.data["receipt_files"]])
            self.assertIsNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.action == "删除费用票据附件")))

    async def test_payment_and_invoice_provenance_both_returned(self):
        async with self.sessions() as db:
            invoice = BusinessRecord(module="invoice", serial_no="CODEX-INVOICE", title="发票", status="已开票", owner="CODEX-admin", data={"case_fee_ids": [self.fee_id], "invoice_no": "CODEX-REAL", "invoice_date": "2026-10-10"})
            voucher = BusinessRecord(module="invoice", serial_no="CODEX-PAYMENT", title="付款凭证", status="已开票", owner="CODEX-admin", data={"case_fee_ids": [self.fee_id], "purpose": "付款凭证", "invoice_no": "命名凭证", "invoice_date": "2026-10-12"})
            transaction = FinanceTransaction(finance_record_id=self.fee_id, transaction_type="付款", transaction_date=date(2026, 10, 11), amount=100, operator="CODEX-admin", voucher_no="CODEX-TRANS")
            db.add_all([invoice, voucher, transaction]); await db.flush()
            db.add_all([FileAttachment(record_id=invoice.id, category="案件发票文件", original_name="CODEX-invoice.pdf", stored_name="CODEX-invoice", path=str(self.path), uploader="CODEX-admin", remark="CODEX-历史导入说明：按原始账本关联"),
                        FileAttachment(record_id=voucher.id, category="付款凭证", original_name="CODEX-payment.pdf", stored_name="CODEX-payment", path=str(self.path), uploader="CODEX-admin"),
                        FileAttachment(record_id=self.fee_id, finance_transaction_id=transaction.id, category="付款凭证", original_name="CODEX-transaction.pdf", stored_name="CODEX-transaction", path=str(self.path), uploader="CODEX-admin")])
            await db.commit()
        response = await self.client.get(self.url())
        self.assertEqual(response.status_code, 200, response.text)
        rows = {item["original_name"]: item for item in response.json()["items"]}
        self.assertEqual(rows["CODEX-invoice.pdf"]["kind"], "invoice")
        self.assertEqual(rows["CODEX-invoice.pdf"]["remark"], "CODEX-历史导入说明：按原始账本关联")
        self.assertEqual(rows["CODEX-payment.pdf"]["kind"], "payment")
        self.assertEqual(rows["CODEX-payment.pdf"]["remark"], "")
        self.assertEqual(rows["CODEX-transaction.pdf"]["bill_date"], "2026-10-11")

    async def test_deleted_legacy_key_is_not_recovered_or_reprojected(self):
        from scripts.recover_imported_invoice_files import recover
        key = "CODEX-legacy-file"
        async with self.sessions() as db:
            await db.execute(text('CREATE TABLE IF NOT EXISTS "FAM_AR_CaseFee" ("CaseFeeId" TEXT, "CaseFeeGuid" TEXT)'))
            await db.execute(text('INSERT INTO "FAM_AR_CaseFee" ("CaseFeeId", "CaseFeeGuid") VALUES (:id, :guid)'), {"id": "90001", "guid": "CODEX-FEE-GUID"})
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "legacy_kind": "ar_case_fee", "case_fee_id": "90001"}
            file = await db.get(FileAttachment, self.file_id)
            file.remark = f"原始发票文件 {key}"
            db.add(LegacyFinanceFile(legacy_key=key, legacy_case_fee_id="CODEX-FEE-GUID", filename=file.original_name, size_bytes=self.path.stat().st_size))
            await db.commit()
        response = await self.client.delete(self.url(self.file_id))
        self.assertEqual(response.status_code, 200, response.text)
        manifest = Path(self.temp.name) / "CODEX-manifest.jsonl"
        manifest.write_text(json.dumps({"key": key, "filename": "CODEX-proof.pdf", "size": self.path.stat().st_size,
            "sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(), "local_name": self.path.name}), encoding="utf-8")
        with patch("app.database.SessionLocal", self.sessions):
            result = await recover(manifest_path=manifest, source_dir=Path(self.temp.name), apply=False)
        self.assertEqual(result["attachments_to_create"], 0)
        self.assertEqual(result["deleted_links_skipped"], 1)
        async with self.sessions() as db:
            # 即使旧恢复结果被再次带入，业务投影仍按精确来源键识别删除状态。
            db.add(FileAttachment(record_id=self.fee_id, category="案件发票文件", original_name="CODEX-proof.pdf", stored_name="CODEX-recreated", path=str(self.path), uploader="CODEX-admin", remark=f"原始发票文件 {key}"))
            await db.commit()
        response = await self.client.get(self.url())
        self.assertEqual([row["attachment_id"] for row in response.json()["items"]], [self.shared_id])


if __name__ == "__main__":
    unittest.main()

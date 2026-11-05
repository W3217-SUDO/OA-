"""501618（高勤兰 11-05）：案件文件 收据自定义文件导入、发票文件导入（案件/合同）。先预览不写入，确认后挂成案件文档。"""
import io
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.ipr import fee_file_import
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User
from app.security import current_identity

API = settings.api_prefix
ME = {"username": "gql618", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"], "display_name": "高勤兰", "department": "知产部", "action_keys": ["*"]}


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class IprFeeFileImport501618Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.upload_root = Path(tempfile.mkdtemp(prefix="ipr618-"))
        self.original_root = fee_file_import.UPLOAD_ROOT
        fee_file_import.UPLOAD_ROOT = self.upload_root
        async with self.sessions() as db:
            db.add(User(username="gql618", display_name="高勤兰", department="知产部", role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="ipr_case", serial_no="SHPU1800025", title="专利甲", customer="客户甲", status="年费监控", owner="gql618",
                                  department="知产部", data={"case_kind": "专利", "legacy_system_case_no": "21800025", "application_no": "2018000001"})
            db.add(case)
            await db.flush()
            self.case_id = case.id
            db.add_all([
                BusinessRecord(module="invoice", serial_no="INV-1", title="发票1", customer="客户甲", status="已开票", owner="gql618", department="知产部",
                               data={"invoice_no": "888888", "case_ids": [case.id], "amount": 1000}),
                BusinessRecord(module="invoice", serial_no="INV-2", title="发票2", customer="客户乙", status="已开票", owner="gql618", department="知产部",
                               data={"invoice_no": "777777", "contract_no": "HT-1", "case_ids": [], "amount": 500}),
            ])
            await db.commit()
        self.previous = dict(app.dependency_overrides)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ME)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr618.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        fee_file_import.UPLOAD_ROOT = self.original_root
        shutil.rmtree(self.upload_root, ignore_errors=True)
        await self.engine.dispose()

    async def attachments(self):
        async with self.sessions() as db:
            return list((await db.scalars(select(FileAttachment))).all())

    async def test_receipt_zip_preview_then_import_only_valid_rows(self):
        payload = zip_bytes({"A21800025F21002.jpg": b"img", "A99999999F1.jpg": b"img", "bad-name.jpg": b"img"})
        files = {"file": ("receipts.zip", payload, "application/zip")}
        preview = await self.client.post(f"{API}/ipr/fee-file-import/receipts", files=files)
        self.assertEqual(preview.status_code, 200, preview.text)
        body = preview.json()
        self.assertEqual((body["total"], body["importable"]), (3, 1))
        ok = next(item for item in body["items"] if item["file_name"] == "A21800025F21002.jpg")
        self.assertEqual((ok["serial_no"], ok["fee_code"], ok["status"]), ("SHPU1800025", "21002", "可导入"))
        self.assertEqual(await self.attachments(), [], "预览不写入")
        confirmed = await self.client.post(f"{API}/ipr/fee-file-import/receipts", files=files, data={"confirm": "true"})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["created"], 1)
        [attachment] = await self.attachments()
        self.assertEqual((attachment.record_id, attachment.category, attachment.file_type_code), (self.case_id, "官费收据", "IPR-RECEIPT"))
        self.assertIn("21002", attachment.remark)

    async def test_invoice_import_case_and_contract(self):
        case_files = {"file": ("888888.pdf", b"pdf", "application/pdf")}
        preview = await self.client.post(f"{API}/ipr/fee-file-import/invoices", files=case_files, data={"scope": "case"})
        self.assertEqual(preview.json()["importable"], 1, preview.text)
        wrong = await self.client.post(f"{API}/ipr/fee-file-import/invoices", files={"file": ("777777.pdf", b"pdf", "application/pdf")}, data={"scope": "case"})
        self.assertEqual(wrong.json()["importable"], 0, "合同发票不能走案件导入")
        await self.client.post(f"{API}/ipr/fee-file-import/invoices", files=case_files, data={"scope": "case", "confirm": "true"})
        contract = await self.client.post(f"{API}/ipr/fee-file-import/invoices", files={"file": ("777777.pdf", b"pdf", "application/pdf")},
                                          data={"scope": "contract", "confirm": "true"})
        self.assertEqual(contract.status_code, 200, contract.text)
        rows = sorted((item.category, item.record_id == self.case_id, item.invoice_record_id is not None) for item in await self.attachments())
        self.assertEqual(rows, [("发票", True, True), ("发票文件", False, True)])


if __name__ == "__main__":
    unittest.main()

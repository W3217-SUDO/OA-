"""Contract and runtime coverage for the concrete seal backend gap closure (E).

The static class reads source files only.  The runtime class uses an in-memory
SQLite database and a temporary upload root, and never touches business data.
"""

from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main
from app.database import Base
from app.main import (
    SealApplicationInput,
    SealBatchStampInput,
    SealPackageDownloadInput,
    SealStampInput,
    batch_stamp_seal_applications,
    create_seal_application,
    list_attachments,
    package_download_seal_files,
    stamp_seal_application,
    upload_attachment,
    upload_seal_application_files,
)
from app.models import BusinessRecord, FileAttachment, RolePermission, SealAsset, SealAssetAudit, User, WorkflowEvent


HERE = Path(__file__).resolve().parent
LOCAL_MAIN = HERE / "app" / "main.py"
OLD_ROOT = HERE.parent.parent.parent / "旧系统归档源码" / "SH.CRM.WEB"
OLD_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentController.cs"
OLD_FILE_CONTROLLER = OLD_ROOT / "Areas" / "AWS" / "Controllers" / "OfficialDocumentFileController.cs"
OLD_CREATE = OLD_ROOT / "Areas" / "AWS" / "Views" / "OfficialDocument" / "PartialView" / "Create.cshtml"
OLD_JS = OLD_ROOT / "Scripts" / "AWS" / "OfficialDocument" / "AWS.OfficialDocument.js"

ADMIN = {"username": "admin", "role": "admin", "department": "上海分所"}


class SealBackendGapEContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = LOCAL_MAIN.read_text(encoding="utf-8-sig")
        cls.old_controller = OLD_CONTROLLER.read_text(encoding="utf-8-sig")
        cls.old_file_controller = OLD_FILE_CONTROLLER.read_text(encoding="utf-8-sig")
        cls.old_create = OLD_CREATE.read_text(encoding="utf-8-sig")
        cls.old_js = OLD_JS.read_text(encoding="utf-8-sig")

    def _span(self, function_name: str, end_marker: str = "@app.") -> str:
        start = self.local.index(f"async def {function_name}")
        end = self.local.find(end_marker, start + 10)
        return self.local[start:] if end < 0 else self.local[start:end]

    def _seal_application_dto(self) -> str:
        return self.local[
            self.local.index("class SealApplicationInput"):self.local.index("class SealPackageDownloadInput")
        ]

    def test_legacy_print_remark_and_multi_seal_type_contract(self):
        self.assertIn("@Html.TextBoxFor(m => m.OfficialDocument.Basic.PrintQuantity", self.old_create)
        self.assertIn("OfficialDocument_Basic_Remark", self.old_create)
        self.assertIn('officialDocument.PrintQuantity = $("#OfficialDocument_Basic_PrintQuantity").val();', self.old_js)
        self.assertIn('officialDocument.Remark = $("#OfficialDocument_Basic_Remark").val();', self.old_js)
        self.assertIn('name="OfficialDocument_Basic_SealType"', self.old_create)
        self.assertIn("sealTypeId = sealTypeId | parseInt($(this).val())", self.old_js)
        dto = self._seal_application_dto()
        for token in ("print_quantity: int | None", "remark: str", "seal_types: list[str]"):
            self.assertIn(token, dto)

    def test_create_and_update_persist_print_remark_and_seal_types(self):
        for function_name in ("create_seal_application", "update_seal_application"):
            source = self._span(function_name)
            for token in ('"print_quantity"', '"remark"', '"seal_types"', "REQUIRED_SEAL_TYPES"):
                self.assertIn(token, source)

    def test_stamp_attachment_handling_is_enforced_and_atomic(self):
        stamp_dto = self.local[self.local.index("class SealStampInput"):self.local.index("class SealAssetInput")]
        batch_dto = self.local[self.local.index("class SealBatchStampInput"):self.local.index("class SealAssetInput")]
        self.assertIn("stamp_attachment_id", stamp_dto)
        self.assertIn("stamp_attachment_id", batch_dto)
        stamp = self._span("stamp_seal_application")
        for token in ("stamp_attachment_id", "FileAttachment", "record_id != item.id", 'category != "用印文件"', "status_code=404"):
            self.assertIn(token, stamp)
        batch = self._span("batch_stamp_seal_applications")
        for token in ("stamp_attachment_id", "source_attachment", "FileAttachment", "unlink(missing_ok=True)", "await db.rollback()"):
            self.assertIn(token, batch)
        upload = self._span("upload_attachment")
        for token in ('record.status not in {"草稿", "待用印"}', "target.unlink(missing_ok=True)", "await db.rollback()"):
            self.assertIn(token, upload)
        seal_upload = self._span("upload_seal_application_files")
        for token in ('record.status not in {"草稿", "待用印"}', "target.unlink(missing_ok=True)", "await db.rollback()"):
            self.assertIn(token, seal_upload)

    def test_package_download_filters_seal_attachment_category(self):
        source = self._span("package_download_seal_files")
        self.assertIn('FileAttachment.category == "用印文件"', source)

    def test_attachment_list_contract_has_server_pagination(self):
        source = self._span("list_attachments")
        for token in ("page: int = Query(1", "page_size: int = Query(15", "items[(page - 1) * page_size", '"page"', '"page_size"', '"pages"'):
            self.assertIn(token, source)

    def test_legacy_batch_upload_and_file_list_pagination_evidence(self):
        self.assertIn("StampFileUpload(string officialDocumentNos)", self.old_controller)
        self.assertIn("OfficialDocumentFiles(string officialDocumentGuid, int? pageNo, int? pageSize)", self.old_file_controller)
        self.assertIn("result.PageSize = pageSize > 0 ? pageSize.Value : 15", self.old_file_controller)


class SealBackendGapERuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="codex-seal-gap-e-")
        self.upload_root = Path(self.tempdir.name) / "uploads"
        self.upload_root.mkdir()
        self.original_upload_root = main.UPLOAD_ROOT
        main.UPLOAD_ROOT = self.upload_root

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = [
            BusinessRecord.__table__,
            WorkflowEvent.__table__,
            SealAsset.__table__,
            SealAssetAudit.__table__,
            FileAttachment.__table__,
            User.__table__,
            RolePermission.__table__,
        ]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.db = self.session_factory()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        await self.engine.dispose()
        main.UPLOAD_ROOT = self.original_upload_root
        self.tempdir.cleanup()

    async def add_asset(self, suffix: str = "A") -> SealAsset:
        asset = SealAsset(
            code=f"CODEX-GAP-E-{suffix}",
            name=f"测试印章-{suffix}",
            seal_type="公章",
            custodian="admin",
            location="测试柜",
            status="可用",
        )
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def add_record(self, status: str, *, copies: int = 1, asset: SealAsset | None = None, suffix: str = "R") -> BusinessRecord:
        if asset is None:
            asset = await self.add_asset(suffix)
        record = BusinessRecord(
            module="seal",
            serial_no=f"CODEX-GAP-E-{suffix}",
            title=f"用印缺口测试-{suffix}",
            customer="测试客户",
            status=status,
            owner="alice",
            department="上海分所",
            data={
                "seal_asset_id": asset.id,
                "copies": copies,
                "use_type": "行政用印",
                "document_names": "测试文件.pdf",
            },
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.commit()
        return record

    async def add_attachment(self, record: BusinessRecord, suffix: str, category: str = "用印文件") -> FileAttachment:
        path = self.upload_root / f"{suffix}.pdf"
        path.write_bytes(f"{suffix}-content".encode())
        item = FileAttachment(
            record_id=record.id,
            category=category,
            original_name=f"{suffix}.pdf",
            stored_name=path.name,
            content_type="application/pdf",
            size=path.stat().st_size,
            path=str(path),
            uploader="alice",
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def event_count(self, record_ids: list[int] | None = None) -> int:
        query = select(func.count()).select_from(WorkflowEvent)
        if record_ids is not None:
            query = query.where(WorkflowEvent.record_id.in_(record_ids))
        return int(await self.db.scalar(query) or 0)

    async def test_create_persists_print_quantity_remark_and_multi_seal_types(self) -> None:
        asset = await self.add_asset("FIELDS")
        await self.db.commit()
        body = SealApplicationInput(
            title="字段测试用印",
            seal_asset_id=asset.id,
            copies=2,
            print_quantity=5,
            remark="打印两份留档",
            seal_types=["法人章", "公章"],
            purpose="测试",
            use_date=date.today(),
            use_type="行政用印",
        )
        result = await create_seal_application(body, ADMIN, self.db)
        self.assertEqual(result["data"]["copies"], 2)
        self.assertEqual(result["data"]["print_quantity"], 5)
        self.assertEqual(result["data"]["remark"], "打印两份留档")
        self.assertEqual(result["data"]["seal_types"], ["公章", "法人章"])

    async def test_invalid_seal_type_is_rejected_before_record_creation(self) -> None:
        asset = await self.add_asset("BAD-TYPE")
        await self.db.commit()
        body = SealApplicationInput(
            title="非法印章类型",
            seal_asset_id=asset.id,
            copies=1,
            seal_types=["不存在的印章"],
            purpose="测试",
            use_date=date.today(),
            use_type="行政用印",
        )
        with self.assertRaises(HTTPException) as raised:
            await create_seal_application(body, ADMIN, self.db)
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            await self.db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "seal")),
            0,
        )

    async def test_single_stamp_validates_and_persists_attachment_id(self) -> None:
        record = await self.add_record("待用印", suffix="SINGLE-OWN")
        own = await self.add_attachment(record, "single-own")
        other_record = await self.add_record("待用印", suffix="SINGLE-OTHER")
        foreign = await self.add_attachment(other_record, "single-foreign")
        await self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            await stamp_seal_application(
                record.id, SealStampInput(actual_copies=1, stamp_attachment_id=foreign.id), ADMIN, self.db
            )
        self.assertEqual(raised.exception.status_code, 404)
        await self.db.refresh(record)
        self.assertEqual(record.status, "待用印")
        self.assertEqual(await self.event_count([record.id]), 0)

        result = await stamp_seal_application(
            record.id,
            SealStampInput(actual_copies=1, archive_no="ARC-SINGLE", stamp_attachment_id=own.id),
            ADMIN,
            self.db,
        )
        self.assertEqual(result["data"]["stamp_attachment_id"], own.id)

    async def test_batch_stamp_copies_attachment_and_records_stamp_ids(self) -> None:
        first = await self.add_record("待用印", suffix="BATCH-FIRST")
        second = await self.add_record("待用印", suffix="BATCH-SECOND")
        source = await self.add_attachment(first, "batch-source")
        await self.db.commit()

        result = await batch_stamp_seal_applications(
            SealBatchStampInput(
                application_ids=[first.id, second.id],
                actual_copies=1,
                archive_no="ARC-BATCH",
                stamp_attachment_id=source.id,
            ),
            ADMIN,
            self.db,
        )
        self.assertEqual(result["processed"], 2)
        await self.db.refresh(first)
        await self.db.refresh(second)
        self.assertEqual((first.status, second.status), ("已用印", "已用印"))
        self.assertEqual(first.data["stamp_attachment_id"], source.id)
        copied = await self.db.get(FileAttachment, second.data["stamp_attachment_id"])
        self.assertIsNotNone(copied)
        self.assertEqual(copied.record_id, second.id)
        self.assertEqual(copied.category, "用印文件")
        self.assertTrue(Path(copied.path).is_file())
        self.assertEqual(Path(copied.path).read_bytes(), Path(source.path).read_bytes())
        self.assertEqual(
            await self.db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == second.id)),
            1,
        )
        self.assertEqual(await self.event_count([first.id, second.id]), 2)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(SealAssetAudit)), 2)

    async def test_batch_stamp_rejects_attachment_outside_selection_atomically(self) -> None:
        first = await self.add_record("待用印", suffix="BATCH-BAD-1")
        second = await self.add_record("待用印", suffix="BATCH-BAD-2")
        outsider = await self.add_record("待用印", suffix="BATCH-BAD-3")
        foreign = await self.add_attachment(outsider, "batch-foreign")
        await self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            await batch_stamp_seal_applications(
                SealBatchStampInput(
                    application_ids=[first.id, second.id],
                    actual_copies=1,
                    stamp_attachment_id=foreign.id,
                ),
                ADMIN,
                self.db,
            )
        self.assertEqual(raised.exception.status_code, 404)
        await self.db.refresh(first)
        await self.db.refresh(second)
        self.assertEqual((first.status, second.status), ("待用印", "待用印"))
        self.assertEqual(await self.event_count([first.id, second.id]), 0)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(SealAssetAudit)), 0)

    async def test_package_download_only_includes_seal_file_category(self) -> None:
        record = await self.add_record("待用印", suffix="PKG")
        seal_file = await self.add_attachment(record, "pkg-seal", category="用印文件")
        await self.add_attachment(record, "pkg-other", category="普通附件")
        await self.db.commit()

        response = await package_download_seal_files(
            SealPackageDownloadInput(application_ids=[record.id]), ADMIN, self.db
        )
        chunks = [chunk async for chunk in response.body_iterator]
        archive = zipfile.ZipFile(io.BytesIO(b"".join(chunks)))
        names = archive.namelist()
        self.assertEqual(len(names), 1)
        self.assertIn(f"{record.serial_no}/{seal_file.id}-pkg-seal.pdf", names[0])

    async def test_attachment_list_paginates_server_side(self) -> None:
        record = await self.add_record("待用印", suffix="PAGE")
        for index in range(3):
            await self.add_attachment(record, f"page-{index}")
        await self.db.commit()

        first = await list_attachments(
            record_id=record.id, category="用印文件", page=1, page_size=2, identity=ADMIN, db=self.db
        )
        self.assertEqual(len(first["items"]), 2)
        self.assertEqual(first["total"], 3)
        self.assertEqual((first["page"], first["page_size"], first["pages"]), (1, 2, 2))

        second = await list_attachments(
            record_id=record.id, category="用印文件", page=2, page_size=2, identity=ADMIN, db=self.db
        )
        self.assertEqual(len(second["items"]), 1)
        first_ids = {item["id"] for item in first["items"]}
        self.assertTrue(all(item["id"] not in first_ids for item in second["items"]))

    async def test_upload_attachment_allows_awaiting_stamp_and_compensates_on_failure(self) -> None:
        record = await self.add_record("待用印", suffix="UPLOAD")
        await self.db.commit()

        class FakeUpload:
            filename = "stamp-scan.pdf"
            content_type = "application/pdf"

            async def read(self):
                return b"stamp-scan"

        item = await upload_attachment(
            FakeUpload(),
            record_id=record.id,
            finance_transaction_id=None,
            customer_guid=None,
            is_license=None,
            document_date=None,
            category="用印文件",
            remark="",
            identity=ADMIN,
            db=self.db,
        )
        self.assertEqual(item["record_id"], record.id)
        stored = await self.db.get(FileAttachment, item["id"])
        self.assertIsNotNone(stored)
        self.assertTrue(Path(stored.path).is_file())
        await self.db.refresh(record)
        self.assertIn("stamp-scan.pdf", record.data["document_names"])
        self.assertEqual(await self.event_count([record.id]), 1)

        before_count = len(list(self.upload_root.glob("*")))
        rollback_record = await self.add_record("待用印", suffix="UPLOAD-ROLLBACK")
        await self.db.commit()
        rollback_record_id = rollback_record.id
        with patch.object(self.db, "commit", new=AsyncMock(side_effect=RuntimeError("simulated commit failure"))):
            with self.assertRaisesRegex(RuntimeError, "simulated commit failure"):
                await upload_attachment(
                    FakeUpload(),
                    record_id=rollback_record_id,
                    finance_transaction_id=None,
                    customer_guid=None,
                    is_license=None,
                    document_date=None,
                    category="用印文件",
                    remark="",
                    identity=ADMIN,
                    db=self.db,
                )
        self.assertEqual(
            await self.db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == rollback_record_id)),
            0,
        )
        self.assertEqual(await self.event_count([rollback_record_id]), 0)
        self.assertEqual(len(list(self.upload_root.glob("*"))), before_count)

    async def test_seal_specific_upload_allows_awaiting_stamp(self) -> None:
        record = await self.add_record("待用印", suffix="SEAL-UPLOAD")
        await self.db.commit()

        class FakeUpload:
            filename = "seal-scan.pdf"
            content_type = "application/pdf"

            async def read(self):
                return b"seal-scan"

        result = await upload_seal_application_files(
            record.id, [FakeUpload()], remark="盖章扫描件", identity=ADMIN, db=self.db
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["original_name"], "seal-scan.pdf")
        await self.db.refresh(record)
        self.assertIn("seal-scan.pdf", record.data["document_names"])
        self.assertEqual(await self.event_count([record.id]), 1)


if __name__ == "__main__":
    unittest.main()

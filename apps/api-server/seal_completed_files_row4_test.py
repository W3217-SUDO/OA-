from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app import main
from app.database import Base
from app.main import (
    SEAL_APPLICATION_FILE_CATEGORY,
    SEAL_STAMPED_FILE_CATEGORY,
    SealStampInput,
    _seal_record_dict,
    download_attachment,
    list_seal_application_files,
    stamp_seal_application,
    upload_seal_application_files,
)
from app.models import BusinessRecord, ContractObject, FileAttachment, LegacyOfficialDocument, LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile, RolePermission, SealAsset, SealAssetAudit, User, WorkflowEvent


ADMIN = {"username": "codex_row4_stamper", "role": "admin", "department": "上海分所"}


class SealCompletedFilesRow4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="codex-seal-row4-")
        self.original_upload_root = main.UPLOAD_ROOT
        main.UPLOAD_ROOT = Path(self.tempdir.name)
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = [
            BusinessRecord.__table__,
            ContractObject.__table__,
            FileAttachment.__table__,
            WorkflowEvent.__table__,
            SealAsset.__table__,
            SealAssetAudit.__table__,
            User.__table__,
            RolePermission.__table__,
            LegacyOfficialDocument.__table__,
            LegacyOfficialDocumentAudit.__table__,
            LegacyOfficialDocumentFile.__table__,
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

    async def test_completed_list_counts_and_downloads_every_stamped_file(self) -> None:
        applicant = User(
            username="codex_row4_applicant",
            password_hash="unused",
            display_name="验收申请人王芳",
            role="staff",
            department="上海分所",
            is_active=True,
        )
        stamper = User(
            username=ADMIN["username"],
            password_hash="unused",
            display_name="验收用印人陈静",
            role="admin",
            department="上海分所",
            is_active=True,
        )
        asset = SealAsset(
            code="CODEX-817-R4-ASSET",
            name="第4行验收公章",
            seal_type="公章",
            custodian=ADMIN["username"],
            location="测试柜",
            status="可用",
        )
        self.db.add_all([applicant, stamper, asset])
        await self.db.flush()
        record = BusinessRecord(
            module="seal",
            serial_no="CODEX-817-R4-SEAL",
            title="第4行已用印多文件验收",
            customer="第4行验收客户",
            status="待用印",
            owner=applicant.username,
            department="上海分所",
            data={
                "seal_asset_id": asset.id,
                "copies": 2,
                "approver": stamper.username,
                "use_type": "行政用印",
                "document_names": "申请阶段待用印文件.pdf",
            },
        )
        self.db.add(record)
        await self.db.flush()
        source_path = main.UPLOAD_ROOT / "row4-source.pdf"
        source_path.write_bytes(b"source")
        self.db.add(FileAttachment(
            record_id=record.id,
            category=SEAL_APPLICATION_FILE_CATEGORY,
            original_name="申请阶段待用印文件.pdf",
            stored_name=source_path.name,
            content_type="application/pdf",
            size=source_path.stat().st_size,
            path=str(source_path),
            uploader=applicant.username,
        ))
        await self.db.commit()

        await upload_seal_application_files(
            record.id,
            [
                UploadFile(file=io.BytesIO(b"stamped-one"), filename="盖章文件一.pdf"),
                UploadFile(file=io.BytesIO(b"stamped-two"), filename="盖章文件二.pdf"),
            ],
            "第4行验收",
            ADMIN,
            self.db,
        )
        stamped = list((await self.db.scalars(
            select(FileAttachment)
            .where(FileAttachment.record_id == record.id, FileAttachment.category == SEAL_STAMPED_FILE_CATEGORY)
            .order_by(FileAttachment.id)
        )).all())
        self.assertEqual([item.original_name for item in stamped], ["盖章文件一.pdf", "盖章文件二.pdf"])

        await stamp_seal_application(
            record.id,
            SealStampInput(actual_copies=2, stamp_attachment_ids=[item.id for item in stamped]),
            ADMIN,
            self.db,
        )
        await self.db.refresh(record)
        projection = await _seal_record_dict(record, self.db)
        self.assertEqual(record.status, "已用印")
        self.assertEqual(projection["owner_display_name"], applicant.display_name)
        self.assertEqual(projection["data"]["approver_display_name"], stamper.display_name)
        self.assertEqual(projection["file_count"], 3)
        self.assertEqual(projection["application_file_count"], 1)
        self.assertEqual(projection["stamped_file_count"], 2)
        self.assertEqual(projection["file_category"], "用印附件")
        self.assertEqual(projection["application_file_names"], ["申请阶段待用印文件.pdf"])
        self.assertEqual(projection["stamped_file_names"], ["盖章文件一.pdf", "盖章文件二.pdf"])
        self.assertEqual(projection["data"]["stamp_attachment_ids"], [item.id for item in stamped])

        listed = await list_seal_application_files(record.id, 1, 15, ADMIN, self.db)
        self.assertEqual(listed["total"], 3)
        self.assertEqual(
            {item["original_name"] for item in listed["items"]},
            {"申请阶段待用印文件.pdf", "盖章文件一.pdf", "盖章文件二.pdf"},
        )
        for item in stamped:
            response = await download_attachment(item.id, ADMIN, self.db)
            self.assertEqual(Path(response.path).read_bytes(), Path(item.path).read_bytes())


if __name__ == "__main__":
    unittest.main()

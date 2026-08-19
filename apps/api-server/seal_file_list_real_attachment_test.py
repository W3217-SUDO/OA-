from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main
from app.database import Base
from app.main import SealApplicationInput, _seal_record_dict, create_seal_application, list_seal_application_files
from app.models import BusinessRecord, FileAttachment, RolePermission, SealAsset, User, WorkflowEvent


ADMIN = {"username": "codex_seal_files_admin", "role": "admin", "department": "上海分所"}


class SealFileListRealAttachmentTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="codex-seal-real-files-")
        self.original_upload_root = main.UPLOAD_ROOT
        main.UPLOAD_ROOT = Path(self.tempdir.name)
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = [
            BusinessRecord.__table__,
            FileAttachment.__table__,
            WorkflowEvent.__table__,
            SealAsset.__table__,
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

    async def test_contract_application_copies_real_file_and_lists_it(self) -> None:
        self.db.add(User(
            username=ADMIN["username"], password_hash="unused", display_name="用印验收管理员",
            role="admin", department="上海分所", is_active=True,
        ))
        asset = SealAsset(
            code="CODEX-SEAL-FILE-ASSET", name="用印验收公章", seal_type="公章",
            custodian=ADMIN["username"], location="测试柜", status="可用",
        )
        contract = BusinessRecord(
            module="contract", serial_no="CODEX-SEAL-FILE-CONTRACT", title="真实附件合同",
            customer="真实附件客户", status="审批通过", owner=ADMIN["username"], department="上海分所", data={},
        )
        self.db.add_all([asset, contract])
        await self.db.flush()
        source_path = main.UPLOAD_ROOT / "source-contract.pdf"
        source_path.write_bytes(b"real contract file")
        self.db.add(FileAttachment(
            record_id=contract.id, category="合同附件", original_name="真实合同附件.pdf",
            stored_name=source_path.name, content_type="application/pdf", size=source_path.stat().st_size,
            path=str(source_path), uploader=ADMIN["username"],
        ))
        await self.db.commit()

        created = await create_seal_application(SealApplicationInput(
            title="真实附件用印申请", contract_no=contract.serial_no, use_type="合同用印",
            seal_asset_id=asset.id, copies=1, purpose="合同盖章", use_date=date.today(),
            document_names="只有名字不能算附件.pdf",
        ), ADMIN, self.db)

        self.assertEqual(created["file_count"], 1)
        self.assertEqual(created["data"]["file_names"], ["真实合同附件.pdf"])
        listed = await list_seal_application_files(created["id"], 1, 15, ADMIN, self.db)
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["items"][0]["original_name"], "真实合同附件.pdf")
        copied = await self.db.scalar(select(FileAttachment).where(
            FileAttachment.id == listed["items"][0]["id"]
        ))
        self.assertIsNotNone(copied)
        self.assertTrue(Path(copied.path).is_file())
        self.assertEqual(Path(copied.path).read_bytes(), b"real contract file")

    async def test_legacy_filename_without_file_row_is_not_counted(self) -> None:
        record = BusinessRecord(
            module="seal", serial_no="CODEX-SEAL-NAME-ONLY", title="文件名空壳申请",
            customer="", status="待审批", owner=ADMIN["username"], department="上海分所",
            data={"document_names": "不存在的文件.pdf"},
        )
        self.db.add(record)
        await self.db.commit()
        projection = await _seal_record_dict(record, self.db)
        self.assertEqual(projection["file_count"], 0)
        self.assertEqual(projection["data"]["file_names"], [])


if __name__ == "__main__":
    unittest.main()

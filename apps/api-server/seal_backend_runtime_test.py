"""Isolated runtime coverage for Seal workflow contracts.

The tests use an in-memory SQLite database and a temporary upload root.  They
call the FastAPI route functions with a real AsyncSession so transaction and
file-compensation behavior is exercised without touching the development DB.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main
from app.database import Base
from app.main import (
    AttachmentBatchInput,
    SealApplicationInput,
    SealApprovalInput,
    SealBatchApplicationInput,
    SealBatchStampInput,
    approve_seal_application,
    batch_delete_seal_attachments,
    batch_stamp_seal_applications,
    batch_withdraw_seal_applications,
    create_seal_application,
)
from app.models import BusinessRecord, FileAttachment, SealAsset, SealAssetAudit, WorkflowEvent


ADMIN = {"username": "admin", "role": "admin", "department": "上海分所"}


class SealBackendRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="codex-seal-runtime-")
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
            code=f"CODEX-RUNTIME-{suffix}",
            name=f"测试印章-{suffix}",
            seal_type="公章",
            custodian="admin",
            location="测试柜",
            status="可用",
        )
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def add_record(
        self,
        status: str,
        *,
        copies: int = 1,
        asset: SealAsset | None = None,
        suffix: str = "R",
    ) -> BusinessRecord:
        if asset is None:
            asset = await self.add_asset(suffix)
        record = BusinessRecord(
            module="seal",
            serial_no=f"CODEX-RUNTIME-{suffix}",
            title=f"运行测试用印-{suffix}",
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

    async def event_count(self, record_ids: list[int] | None = None) -> int:
        query = select(func.count()).select_from(WorkflowEvent)
        if record_ids is not None:
            query = query.where(WorkflowEvent.record_id.in_(record_ids))
        return int(await self.db.scalar(query) or 0)

    async def test_reject_without_comment_returns_422_and_preserves_status(self) -> None:
        record = await self.add_record("待审批", suffix="REJECT")

        with self.assertRaises(HTTPException) as raised:
            await approve_seal_application(record.id, SealApprovalInput(approved=False, comment="   "), ADMIN, self.db)

        self.assertEqual(raised.exception.status_code, 422)
        await self.db.refresh(record)
        self.assertEqual(record.status, "待审批")
        self.assertEqual(await self.event_count([record.id]), 0)

    async def test_invalid_use_type_returns_422_without_creating_record(self) -> None:
        asset = await self.add_asset("USE-TYPE")
        await self.db.commit()
        body = SealApplicationInput(
            title="非法用印类型",
            seal_asset_id=asset.id,
            copies=1,
            purpose="契约测试",
            use_type="不支持的类型",
            use_date=date.today(),
            document_names="测试文件.pdf",
        )

        with self.assertRaises(HTTPException) as raised:
            await create_seal_application(body, ADMIN, self.db)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            await self.db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "seal")),
            0,
        )

    async def test_batch_withdraw_is_atomic_and_writes_events_when_valid(self) -> None:
        invalid = await self.add_record("草稿", suffix="WITHDRAW-BAD")
        valid = await self.add_record("待审批", suffix="WITHDRAW-GOOD")

        with self.assertRaises(HTTPException) as raised:
            await batch_withdraw_seal_applications(
                SealBatchApplicationInput(application_ids=[valid.id, invalid.id]), ADMIN, self.db
            )
        self.assertEqual(raised.exception.status_code, 409)
        await self.db.refresh(invalid)
        await self.db.refresh(valid)
        self.assertEqual((invalid.status, valid.status), ("草稿", "待审批"))
        self.assertEqual(await self.event_count([invalid.id, valid.id]), 0)

        second = await self.add_record("待用印", suffix="WITHDRAW-GOOD-2")
        result = await batch_withdraw_seal_applications(
            SealBatchApplicationInput(application_ids=[valid.id, second.id], comment="统一撤回"), ADMIN, self.db
        )
        self.assertEqual(result["processed"], 2)
        await self.db.refresh(valid)
        await self.db.refresh(second)
        self.assertEqual((valid.status, second.status), ("已撤回", "已撤回"))
        self.assertEqual(await self.event_count([valid.id, second.id]), 2)

    async def test_batch_stamp_is_atomic_and_records_asset_usage_and_audit(self) -> None:
        first_asset = await self.add_asset("STAMP-1")
        second_asset = await self.add_asset("STAMP-2")
        first = await self.add_record("待用印", copies=1, asset=first_asset, suffix="STAMP-1")
        second = await self.add_record("待用印", copies=1, asset=second_asset, suffix="STAMP-2")

        with self.assertRaises(HTTPException) as raised:
            await batch_stamp_seal_applications(
                SealBatchStampInput(application_ids=[first.id, second.id], actual_copies=2), ADMIN, self.db
            )
        self.assertEqual(raised.exception.status_code, 409)
        await self.db.refresh(first)
        await self.db.refresh(second)
        await self.db.refresh(first_asset)
        await self.db.refresh(second_asset)
        self.assertEqual((first.status, second.status), ("待用印", "待用印"))
        self.assertEqual((first_asset.usage_count, second_asset.usage_count), (0, 0))
        self.assertEqual(await self.event_count([first.id, second.id]), 0)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(SealAssetAudit)), 0)

        result = await batch_stamp_seal_applications(
            SealBatchStampInput(application_ids=[first.id, second.id], actual_copies=1, archive_no="ARC-RUNTIME"),
            ADMIN,
            self.db,
        )
        self.assertEqual(result["processed"], 2)
        await self.db.refresh(first)
        await self.db.refresh(second)
        await self.db.refresh(first_asset)
        await self.db.refresh(second_asset)
        self.assertEqual((first.status, second.status), ("已用印", "已用印"))
        self.assertEqual((first_asset.usage_count, second_asset.usage_count), (1, 1))
        self.assertEqual(await self.event_count([first.id, second.id]), 2)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(SealAssetAudit)), 2)

    async def add_attachment(self, record: BusinessRecord, suffix: str) -> FileAttachment:
        path = self.upload_root / f"{suffix}.pdf"
        path.write_bytes(f"{suffix}-content".encode())
        item = FileAttachment(
            record_id=record.id,
            category="用印文件",
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

    async def test_batch_attachment_delete_removes_rows_files_and_restores_on_commit_failure(self) -> None:
        record = await self.add_record("草稿", suffix="FILES")
        first = await self.add_attachment(record, "runtime-first")
        second = await self.add_attachment(record, "runtime-second")
        await self.db.commit()
        first_path, second_path = Path(first.path), Path(second.path)

        result = await batch_delete_seal_attachments(
            AttachmentBatchInput(attachment_ids=[first.id, second.id]), ADMIN, self.db
        )
        self.assertEqual(result["deleted"], 2)
        self.assertIsNone(await self.db.get(FileAttachment, first.id))
        self.assertIsNone(await self.db.get(FileAttachment, second.id))
        self.assertFalse(first_path.exists())
        self.assertFalse(second_path.exists())
        self.assertEqual(await self.event_count([record.id]), 2)

        rollback_record = await self.add_record("草稿", suffix="FILES-ROLLBACK")
        rollback_item = await self.add_attachment(rollback_record, "runtime-rollback")
        await self.db.commit()
        rollback_record_id = rollback_record.id
        rollback_item_id = rollback_item.id
        rollback_path = Path(rollback_item.path)

        with patch.object(self.db, "commit", new=AsyncMock(side_effect=RuntimeError("simulated commit failure"))):
            with self.assertRaisesRegex(RuntimeError, "simulated commit failure"):
                await batch_delete_seal_attachments(
                    AttachmentBatchInput(attachment_ids=[rollback_item.id]), ADMIN, self.db
                )

        restored = await self.db.get(FileAttachment, rollback_item_id)
        self.assertIsNotNone(restored)
        self.assertTrue(rollback_path.exists())
        self.assertEqual(await self.event_count([rollback_record_id]), 0)
        self.assertFalse(any(self.upload_root.glob(".seal-delete-*")))


if __name__ == "__main__":
    unittest.main()

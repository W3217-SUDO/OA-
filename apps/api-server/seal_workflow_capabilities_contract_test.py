"""Focused executable contracts for unified seal workflow capabilities."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main
from app.database import Base
from app.main import (
    ContractSealApplicationInput,
    SEAL_APPLICATION_FILE_CATEGORY,
    SEAL_STAMPED_FILE_CATEGORY,
    SealApprovalInput,
    SealStampInput,
    _seal_record_dict,
    approve_seal_application,
    create_contract_seal_application,
    list_seal_application_files,
    stamp_seal_application,
)
from app.models import BusinessRecord, ContractApprovalStep, FileAttachment, JobRole, LegacyOfficialDocument, LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile, RolePermission, SealAsset, SealAssetAudit, User, WorkflowEvent


APPLICANT = {"username": "seal-cap-applicant", "role": "user", "department": "上海分所"}
AUDITOR = {"username": "seal-cap-auditor", "role": "user", "department": "上海分所"}
OTHER_AUDITOR = {"username": "seal-cap-other", "role": "user", "department": "上海分所"}
STAMPER = {"username": "seal-cap-stamper", "role": "user", "department": "上海分所"}


class SealWorkflowCapabilitiesContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="seal-capabilities-")
        self.original_upload_root = main.UPLOAD_ROOT
        main.UPLOAD_ROOT = Path(self.tempdir.name)
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = [
            BusinessRecord.__table__, ContractApprovalStep.__table__, FileAttachment.__table__, WorkflowEvent.__table__,
            SealAsset.__table__, SealAssetAudit.__table__, User.__table__, JobRole.__table__, RolePermission.__table__,
            LegacyOfficialDocument.__table__, LegacyOfficialDocumentAudit.__table__, LegacyOfficialDocumentFile.__table__,
        ]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.db = self.sessions()
        self.db.add_all([
            JobRole(code="SEAL-APPLY", name="用印申请岗", permissions=["用印申请"]),
            JobRole(code="SEAL-AUDIT", name="用印审批岗", permissions=["用印审批"]),
            JobRole(code="SEAL-STAMP", name="印章管理岗", permissions=["印章管理"]),
            User(username=APPLICANT["username"], password_hash="unused", display_name="申请人", role="user", department="上海分所", profile={"permission_role": "用印申请岗"}),
            User(username=AUDITOR["username"], password_hash="unused", display_name="审批人", role="user", department="上海分所", profile={"permission_role": "用印审批岗"}),
            User(username=OTHER_AUDITOR["username"], password_hash="unused", display_name="其他审批人", role="user", department="上海分所", profile={"permission_role": "用印审批岗"}),
            User(username=STAMPER["username"], password_hash="unused", display_name="用印人", role="user", department="上海分所", profile={"permission_role": "印章管理岗"}),
            SealAsset(code="SEAL-CAP-ASSET", name="能力测试公章", seal_type="公章", custodian=STAMPER["username"], status="可用"),
        ])
        await self.db.commit()
        self.asset = await self.db.scalar(select(SealAsset).where(SealAsset.code == "SEAL-CAP-ASSET"))

    async def asyncTearDown(self) -> None:
        await self.db.close()
        await self.engine.dispose()
        main.UPLOAD_ROOT = self.original_upload_root
        self.tempdir.cleanup()

    async def _seal(self, serial: str, *, status: str = "待审批", approver: str = AUDITOR["username"], owner: str = APPLICANT["username"]) -> BusinessRecord:
        record = BusinessRecord(
            module="seal", serial_no=serial, title=serial, customer="能力测试客户", status=status,
            owner=owner, department="上海分所", data={"seal_asset_id": self.asset.id, "copies": 2, "approver": approver, "use_type": "行政用印"},
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def test_assigned_and_legacy_approval_use_the_same_action_capability(self) -> None:
        assigned = await self._seal("SEAL-CAP-ASSIGNED")
        legacy = await self._seal("SEAL-CAP-LEGACY", approver="")
        denied = await self._seal("SEAL-CAP-DENIED", approver=OTHER_AUDITOR["username"])
        await self.db.commit()

        projection = await _seal_record_dict(assigned, self.db, identity=AUDITOR)
        self.assertTrue(projection["capabilities"]["approve"])
        self.assertTrue(projection["capabilities"]["reject"])
        self.assertEqual(projection["action_keys"], ["approve", "reject"])
        self.assertTrue((await _seal_record_dict(legacy, self.db, identity=AUDITOR))["capabilities"]["approve"])
        self.assertFalse((await _seal_record_dict(denied, self.db, identity=AUDITOR))["capabilities"]["approve"])

        await approve_seal_application(assigned.id, SealApprovalInput(approved=True, comment="通过"), AUDITOR, self.db)
        await self.db.refresh(assigned)
        self.assertEqual(assigned.status, "待用印")
        with self.assertRaises(HTTPException) as rejected:
            await approve_seal_application(denied.id, SealApprovalInput(approved=True, comment="越权"), AUDITOR, self.db)
        self.assertEqual(rejected.exception.status_code, 403)

    async def test_both_attachment_classes_remain_visible_after_stamping_and_empty_scan_is_idempotent(self) -> None:
        record = await self._seal("SEAL-CAP-FILES", status="待用印")
        application_path = main.UPLOAD_ROOT / "application.pdf"
        stamped_path = main.UPLOAD_ROOT / "stamped.pdf"
        application_path.write_bytes(b"application")
        stamped_path.write_bytes(b"stamped")
        self.db.add_all([
            FileAttachment(record_id=record.id, category=SEAL_APPLICATION_FILE_CATEGORY, original_name="申请文件.pdf", stored_name=application_path.name, content_type="application/pdf", size=application_path.stat().st_size, path=str(application_path), uploader=APPLICANT["username"]),
            FileAttachment(record_id=record.id, category=SEAL_STAMPED_FILE_CATEGORY, original_name="盖章文件.pdf", stored_name=stamped_path.name, content_type="application/pdf", size=stamped_path.stat().st_size, path=str(stamped_path), uploader=STAMPER["username"]),
        ])
        await self.db.commit()

        projection = await _seal_record_dict(record, self.db, identity=STAMPER)
        self.assertEqual((projection["application_file_count"], projection["stamped_file_count"], projection["file_count"]), (1, 1, 2))
        self.assertTrue(projection["capabilities"]["stamp"])
        listed = await list_seal_application_files(record.id, 1, 15, {"username": "seal-cap-stamper", "role": "admin", "department": "上海分所"}, self.db)
        self.assertEqual({row["category"] for row in listed["items"]}, {SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY})

        empty_scan = await self._seal("SEAL-CAP-EMPTY", status="待用印")
        await self.db.commit()
        await stamp_seal_application(empty_scan.id, SealStampInput(actual_copies=1, stamp_attachment_ids=[]), STAMPER, self.db)
        await stamp_seal_application(empty_scan.id, SealStampInput(actual_copies=1, stamp_attachment_ids=[]), STAMPER, self.db)
        await self.db.refresh(empty_scan)
        await self.db.refresh(self.asset)
        self.assertEqual(empty_scan.status, "已用印")
        self.assertNotIn("stamp_attachment_ids", empty_scan.data)
        self.assertEqual(self.asset.usage_count, 1)

    async def test_contract_sync_rejects_zero_or_cross_contract_sources_and_persists_selected_ids(self) -> None:
        contract = BusinessRecord(module="contract", serial_no="SEAL-CAP-CONTRACT", title="能力测试合同", customer="能力测试客户", status="审批通过", owner=APPLICANT["username"], department="上海分所", data={})
        other = BusinessRecord(module="contract", serial_no="SEAL-CAP-OTHER", title="其他合同", customer="其他客户", status="审批通过", owner=APPLICANT["username"], department="上海分所", data={})
        self.db.add_all([contract, other])
        await self.db.flush()
        body = ContractSealApplicationInput(approver=AUDITOR["username"], seal_asset_id=self.asset.id, copies=1, purpose="合同签署", use_date=date.today())
        with self.assertRaises(HTTPException) as no_file:
            await create_contract_seal_application(contract.id, body, APPLICANT, self.db)
        self.assertEqual(no_file.exception.status_code, 409)

        other_path = main.UPLOAD_ROOT / "other.pdf"
        other_path.write_bytes(b"other")
        wrong = FileAttachment(record_id=other.id, category="合同文档", original_name="其他合同.pdf", stored_name=other_path.name, content_type="application/pdf", size=other_path.stat().st_size, path=str(other_path), uploader=APPLICANT["username"])
        self.db.add(wrong)
        await self.db.commit()
        cross_body = body.model_copy(update={"source_attachment_ids": [wrong.id]})
        with self.assertRaises(HTTPException) as cross_file:
            await create_contract_seal_application(contract.id, cross_body, APPLICANT, self.db)
        self.assertEqual(cross_file.exception.status_code, 422)

        valid_path = main.UPLOAD_ROOT / "current.pdf"
        valid_path.write_bytes(b"current")
        source = FileAttachment(record_id=contract.id, category="合同文档", original_name="当前合同.pdf", stored_name=valid_path.name, content_type="application/pdf", size=valid_path.stat().st_size, path=str(valid_path), uploader=APPLICANT["username"])
        self.db.add(source)
        await self.db.commit()
        created = await create_contract_seal_application(contract.id, body, APPLICANT, self.db)
        self.assertEqual(created["data"]["source_attachment_ids"], [source.id])
        copied = list((await self.db.scalars(select(FileAttachment).where(FileAttachment.record_id == created["id"], FileAttachment.category == SEAL_APPLICATION_FILE_CATEGORY))).all())
        self.assertEqual([attachment.original_name for attachment in copied], ["当前合同.pdf"])


if __name__ == "__main__":
    unittest.main()

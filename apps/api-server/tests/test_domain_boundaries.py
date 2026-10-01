"""领域路由迁移后，核对回款事务与用印文件补偿。"""

from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi import HTTPException, UploadFile

from app.areas.legal.router import import_business_records
from app.areas.legal import seals
from app.core.incoming_settlement import _active_settlements_by_receipt, _revert_incoming_allocation
from app.database import Base
from app.models import BusinessRecord, FileAttachment, FinanceTransaction, ReceivablePlan, User
from app.models_shared import AttachmentBatchInput


class DomainBoundaryTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tempdir = TemporaryDirectory(prefix="oa-test-enterprise-boundaries-")
        self.upload_root = Path(self.tempdir.name) / "uploads"
        self.upload_root.mkdir()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.tempdir.cleanup()

    async def test_settlement_guard_keeps_legacy_inactive_statuses(self) -> None:
        async with self.sessions() as db:
            rows = [BusinessRecord(
                module="finance_settlement", serial_no=f"ENTERPRISE-BOUNDARIES-{index}",
                title="隔离结算", customer="隔离客户", status=record_status,
                owner="enterprise-admin", data={"receipt_id": "42"},
            ) for index, record_status in enumerate(
                ["已拒绝", "已驳回", "已退回", "已撤回", "已作废", "待审批"], start=1,
            )]
            db.add_all(rows)
            await db.commit()
            active = await _active_settlements_by_receipt(db, {42})
            self.assertEqual(active[42].id, rows[-1].id)
            self.assertEqual(
                await _active_settlements_by_receipt(db, {42}, exclude_application_ids={rows[-1].id}),
                {},
            )

    async def test_generic_case_import_remains_blocked(self) -> None:
        file = UploadFile(file=BytesIO(b"serial_no,title\nCASE-1,Case 1\n"), filename="cases.csv")
        with patch("app.core.permissions._require_record_module_menu", new=AsyncMock()):
            with self.assertRaises(HTTPException) as raised:
                await import_business_records(
                    module="case", file=file,
                    identity={"username": "enterprise-admin", "role": "admin"}, db=object(),
                )
        self.assertEqual(raised.exception.status_code, 409)

    async def test_allocation_reversal_remains_in_callers_transaction(self) -> None:
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="ENTERPRISE-BOUNDARIES-CONTRACT",
                title="隔离合同", customer="隔离客户", status="已审批", owner="enterprise-admin", data={},
            )
            fee = BusinessRecord(
                module="finance", serial_no="ENTERPRISE-BOUNDARIES-FEE",
                title="隔离费用", customer="隔离客户", status="已收款", owner="enterprise-admin",
                data={"received_amount": 100, "cashed_amount": 100, "incoming_payment_id": 42},
            )
            db.add_all([contract, fee])
            await db.flush()
            plan = ReceivablePlan(
                contract_record_id=contract.id, phase="代理费", due_date=date.today(),
                amount=100, received_amount=100, status="已收款",
            )
            transaction = FinanceTransaction(
                finance_record_id=fee.id, transaction_type="收款", amount=100,
                transaction_date=date.today(), operator="enterprise-admin",
            )
            db.add_all([plan, transaction])
            await db.commit()
            fee_id, plan_id, transaction_id = fee.id, plan.id, transaction.id

        async with self.sessions() as db:
            await _revert_incoming_allocation(
                {"amount": 100, "receivable_plan_id": plan_id, "fee_record_id": fee_id,
                 "transaction_id": transaction_id},
                db, payment_id=42,
            )
            await db.flush()
            self.assertEqual((await db.get(ReceivablePlan, plan_id)).received_amount, 0)
            self.assertIsNone(await db.get(FinanceTransaction, transaction_id))
            await db.rollback()

        async with self.sessions() as db:
            self.assertEqual((await db.get(ReceivablePlan, plan_id)).received_amount, 100)
            self.assertEqual((await db.get(BusinessRecord, fee_id)).data["received_amount"], 100)
            self.assertIsNotNone(await db.get(FinanceTransaction, transaction_id))

    async def test_seal_file_and_row_restore_when_commit_fails(self) -> None:
        identity = {"username": "enterprise-admin", "role": "admin", "department": "测试"}
        file_path = self.upload_root / "seal-proof.pdf"
        file_path.write_bytes(b"seal-proof")
        async with self.sessions() as db:
            db.add(User(
                username=identity["username"], display_name="测试管理员", role="admin",
                department="测试", password_hash="unused", is_active=True,
            ))
            record = BusinessRecord(
                module="seal", serial_no="ENTERPRISE-BOUNDARIES-SEAL",
                title="隔离用印", customer="隔离客户", status="草稿",
                owner=identity["username"], department="测试", data={"document_names": file_path.name},
            )
            db.add(record)
            await db.flush()
            attachment = FileAttachment(
                record_id=record.id, category="用印文件", original_name=file_path.name,
                stored_name=file_path.name, path=str(file_path), content_type="application/pdf",
                size=file_path.stat().st_size, uploader=identity["username"],
            )
            db.add(attachment)
            await db.commit()
            attachment_id = attachment.id

            with patch.object(seals, "UPLOAD_ROOT", self.upload_root):
                with patch.object(db, "commit", new=AsyncMock(side_effect=RuntimeError("commit failed"))):
                    with self.assertRaisesRegex(RuntimeError, "commit failed"):
                        await seals.batch_delete_seal_attachments(
                            AttachmentBatchInput(attachment_ids=[attachment_id]), identity, db,
                        )
            self.assertIsNotNone(await db.get(FileAttachment, attachment_id))
            self.assertEqual(file_path.read_bytes(), b"seal-proof")
            self.assertFalse(list(self.upload_root.glob(".pending-delete-*")))

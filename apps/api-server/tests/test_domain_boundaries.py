"""领域路由迁移后，核对回款事务与用印文件补偿。"""

from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from copy import deepcopy

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi import HTTPException, UploadFile

from app.areas.legal.router import import_business_records
from app.areas.legal import seals
from app.core.incoming_settlement import _active_settlements_by_receipt, _revert_incoming_allocation
from app.database import Base
from app.models import BusinessRecord, FileAttachment, FinanceTransaction, ReceivablePlan, User
from app.models_shared import AttachmentBatchInput
from app.areas.personal_agent import service as personal_service
from app.areas.personal_agent.confirmation_history import project_personal_actions
from app.agent_mcp import service as tool_service


class PersonalConfirmationBoundaryTest(IsolatedAsyncioTestCase):
    def request(self, status, owner="本人"):
        return BusinessRecord(
            id=1, module="agent_mcp_action", serial_no="MCP-request-1", owner=owner,
            status=status, data={"request_id": "request-1", "error": {"status_code": 409, "detail": {"detail": "原业务拒绝"}} if status == "执行失败" else None},
        )

    def state(self):
        return {"conversation_id": "default", "messages": [], "pending_actions": [{
            "id": "action-1", "type": "mcp.call", "status": "pending", "requested_by": "本人",
            "payload": {"request_id": "request-1"}, "summary": "旧待确认卡",
        }]}

    async def test_persistent_status_projection_is_read_only_and_identity_scoped(self):
        for stored, visible in (("执行失败", "failed"), ("已执行", "succeeded"), ("已拒绝", "rejected"), ("执行中", "executing"), ("待确认", "pending")):
            with self.subTest(status=stored):
                state = self.state()
                original = deepcopy(state)
                record = self.request(stored)
                db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [record])))
                result = await project_personal_actions(state, {"username": "本人"}, db)
                self.assertEqual(result["pending_actions"][0]["status"], visible)
                self.assertEqual(state, original)
                self.assertEqual(record.status, stored)
                self.assertIsNot(result["pending_actions"][0], state["pending_actions"][0])
                query = db.scalars.await_args.args[0]
                parameters = query.compile().params
                self.assertIn("本人", parameters.values())
                self.assertIn("agent_mcp_action", parameters.values())
                self.assertIn(["MCP-request-1"], parameters.values())
                if stored == "执行失败":
                    self.assertEqual(result["pending_actions"][0]["error"]["detail"]["detail"], "原业务拒绝")
        db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [])))
        with self.assertRaises(HTTPException) as raised:
            await project_personal_actions(self.state(), {"username": "本人"}, db)
        self.assertEqual(raised.exception.status_code, 404, "其他所有者的请求不能被投影")
        foreign = self.state()
        foreign["pending_actions"][0]["requested_by"] = "别人"
        db.scalars.reset_mock()
        with self.assertRaises(HTTPException) as raised:
            await project_personal_actions(foreign, {"username": "本人"}, db)
        self.assertEqual(raised.exception.status_code, 403)
        db.scalars.assert_not_awaited()

    async def test_personal_state_and_conversation_reads_project_without_saving(self):
        state = self.state()
        original = deepcopy(state)
        record = self.request("执行失败")
        db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [record])))
        with patch.object(personal_service, "ensure_identity_file", new=AsyncMock(return_value="身份")), \
             patch.object(personal_service, "_read_state", return_value=state), \
             patch.object(personal_service, "_user_dir", return_value=Path("isolated-unit")), \
             patch.object(personal_service.conversations, "list_conversations", new=AsyncMock(return_value={"state": state, "items": [], "active_id": "default"})), \
             patch.object(personal_service.conversations, "save_state", new=AsyncMock()) as save:
            identity = {"username": "本人"}
            direct = await personal_service.personal_state(identity, db)
            snapshot = await personal_service.manage_conversations(identity, db=db)
            self.assertEqual(direct["pending_actions"][0]["status"], "failed")
            self.assertEqual(snapshot["state"]["pending_actions"][0]["status"], "failed")
            self.assertEqual(state, original)
            save.assert_not_awaited()

    async def test_decided_mcp_requests_remain_non_replayable(self):
        for status in ("执行失败", "已执行", "已拒绝", "执行中"):
            with self.subTest(status=status):
                record = self.request(status)
                db = SimpleNamespace(scalar=AsyncMock(return_value=record))
                with patch.object(tool_service, "require_human_decision"), \
                     patch.object(tool_service, "authenticated_identity", new=AsyncMock(return_value={"username": "本人"})), \
                     patch.object(tool_service, "execute_original", new=AsyncMock()) as execute:
                    with self.assertRaises(HTTPException) as raised:
                        await tool_service.decide_tool_request("request-1", "approved", {"username": "本人"}, db)
                    self.assertEqual(raised.exception.status_code, 409)
                    self.assertEqual(record.status, status)
                    execute.assert_not_awaited()


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

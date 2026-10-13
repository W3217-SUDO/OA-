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
from app.areas.personal_agent.confirmation_history import begin_personal_decision, project_personal_actions, read_confirmation_detail, read_confirmation_history
from app.areas.personal_agent.action_presentation import dismiss_personal_actions
from app.areas.personal_agent import conversations
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
        for action_type in ("create_task", "approve_contract"):
            for stored, visible in (("执行失败", "failed"), ("已执行", "succeeded"), ("已拒绝", "rejected"), ("执行中", "executing"), ("待确认", "pending")):
                with self.subTest(action_type=action_type, status=stored):
                    state = self.state()
                    state["pending_actions"][0]["type"] = action_type
                    original = deepcopy(state)
                    record = self.request(stored)
                    record.module, record.serial_no = "personal_agent_action", "PA-action-1"
                    db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [record])))
                    result = await project_personal_actions(state, {"username": "本人"}, db)
                    self.assertEqual(result["pending_actions"][0]["status"], visible)
                    self.assertEqual(result["pending_actions"][0]["error"], record.data["error"])
                    self.assertEqual(state, original)
                    self.assertEqual(record.status, stored)
            db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [])))
            result = await project_personal_actions(state, {"username": "本人"}, db)
            self.assertEqual(result["pending_actions"][0], state["pending_actions"][0], "升级前无 PA 存档时保留原 pending")
            db = SimpleNamespace(scalars=AsyncMock(side_effect=[SimpleNamespace(all=lambda: []), SimpleNamespace(all=lambda: ["PA-action-1"])]))
            with self.assertRaises(HTTPException) as raised:
                await project_personal_actions(state, {"username": "本人"}, db)
            self.assertEqual(raised.exception.status_code, 403, "他人的 PA 存档不能冒充无存档旧请求")

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
                for action_type in ("create_task", "approve_contract"):
                    action = {**self.state()["pending_actions"][0], "type": action_type}
                    record.module, record.serial_no = "personal_agent_action", "PA-action-1"
                    with self.assertRaises(HTTPException) as raised:
                        await begin_personal_decision(action, "approved", "", {"username": "本人"}, self.state(), db)
                    self.assertEqual(raised.exception.status_code, 409)

    async def test_action_dismissal_persists_only_presentation_and_keeps_audit(self):
        with TemporaryDirectory(prefix="oa-test-action-dismiss-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            state = {**snapshot["state"], "pending_actions": self.state()["pending_actions"]}
            await conversations.save_state(directory, state)
            original = conversations.read_state(directory, state["conversation_id"])
            record = self.request("执行失败")
            db = SimpleNamespace(scalar=AsyncMock(return_value="本人"),
                                 scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [record])), commit=AsyncMock())
            result = await dismiss_personal_actions(directory, state["conversation_id"], ["action-1"], {"username": "本人"}, db)
            stored = conversations.read_state(directory, state["conversation_id"])
            self.assertEqual(stored["dismissed_action_ids"], ["action-1"])
            self.assertEqual({**stored, "dismissed_action_ids": []}, original)
            self.assertEqual(result["state"]["pending_actions"][0]["status"], "failed")
            self.assertEqual(stored["pending_actions"][0]["status"], "pending", "原结构化请求不被展示投影重写")
            self.assertEqual(record.status, "执行失败")
            with patch.object(conversations, "_write_json", wraps=conversations._write_json) as write:
                again = await dismiss_personal_actions(directory, state["conversation_id"], ["action-1"], {"username": "本人"}, db)
                self.assertEqual(again["state"]["dismissed_action_ids"], ["action-1"])
                write.assert_not_called()
            await conversations.save_state(directory, {**stored, "dismissed_action_ids": ["departed-action", "action-1"]})
            with patch.object(conversations, "_write_json", wraps=conversations._write_json) as write:
                self.assertEqual(conversations.read_state(directory, state["conversation_id"])["dismissed_action_ids"],
                                 ["departed-action", "action-1"])
                write.assert_not_called()
                cleaned = await dismiss_personal_actions(directory, state["conversation_id"], ["action-1"], {"username": "本人"}, db)
                self.assertEqual(cleaned["state"]["dismissed_action_ids"], ["action-1"])
                self.assertEqual(conversations.read_state(directory, state["conversation_id"]), stored)
                self.assertEqual(write.call_count, 1)
            await conversations.save_state(directory, stored)
            self.assertEqual(conversations.read_state(directory, state["conversation_id"])["dismissed_action_ids"], ["action-1"])
            db.commit.assert_not_awaited()
            async with conversations.conversation_operation(directory, state["conversation_id"]):
                with self.assertRaises(HTTPException) as raised:
                    await dismiss_personal_actions(directory, state["conversation_id"], ["action-1"], {"username": "本人"}, db)
                self.assertEqual(raised.exception.status_code, 409)
            record.owner = "别人"
            with self.assertRaises(HTTPException) as raised:
                await dismiss_personal_actions(directory, state["conversation_id"], ["action-1"], {"username": "本人"}, db)
            self.assertEqual(raised.exception.status_code, 403)
            self.assertEqual(conversations.read_state(directory, state["conversation_id"]), stored)

    async def test_batch_dismissal_validates_all_ids_before_one_presentation_write(self):
        with TemporaryDirectory(prefix="oa-test-action-batch-dismiss-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            first = self.state()["pending_actions"][0]
            second = {**first, "id": "action-2", "payload": {"request_id": "request-2"}}
            state = {**snapshot["state"], "pending_actions": [first, second],
                     "dismissed_action_ids": ["departed-action", "action-1"]}
            await conversations.save_state(directory, state)
            record = self.request("待确认")
            other = self.request("待确认")
            other.id, other.serial_no = 2, "MCP-request-2"
            db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [record, other])), commit=AsyncMock())
            before = conversations.read_state(directory, state["conversation_id"])
            with patch.object(conversations, "_write_json", wraps=conversations._write_json) as write:
                self.assertEqual(conversations.read_state(directory, state["conversation_id"])["dismissed_action_ids"],
                                 ["departed-action", "action-1"])
                write.assert_not_called()
                for ids, expected in ((["action-1", "missing"], 404), (["action-1", "action-1"], 422), ([], 422)):
                    with self.assertRaises(HTTPException) as raised:
                        await dismiss_personal_actions(directory, state["conversation_id"], ids, {"username": "本人"}, db)
                    self.assertEqual(raised.exception.status_code, expected)
                    self.assertEqual(conversations.read_state(directory, state["conversation_id"]), before)
                other.owner = "别人"
                with self.assertRaises(HTTPException) as raised:
                    await dismiss_personal_actions(directory, state["conversation_id"], ["action-1", "action-2"], {"username": "本人"}, db)
                self.assertEqual(raised.exception.status_code, 403)
                write.assert_not_called()
                other.owner = "本人"
                result = await dismiss_personal_actions(directory, state["conversation_id"], ["action-1", "action-2"], {"username": "本人"}, db)
                self.assertEqual(write.call_count, 1)
                self.assertEqual(result["state"]["dismissed_action_ids"], ["action-1", "action-2"])
                self.assertEqual({**conversations.read_state(directory, state["conversation_id"]),
                                  "dismissed_action_ids": before["dismissed_action_ids"]}, before)
                self.assertEqual(len(result["state"]["pending_actions"]), 2)
                self.assertEqual(record.status, "待确认")
                self.assertEqual(other.status, "待确认")
                db.commit.assert_not_awaited()

    async def test_pending_history_preserves_legacy_and_real_conversation_source(self):
        with TemporaryDirectory(prefix="oa-test-action-history-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            original = self.state()["pending_actions"][0]
            original["preview"] = {"operation_name": "真实操作", "method": "POST", "path_template": "/api/v1/isolated-operation",
                                   "params": {"path": {}, "query": {}, "body": {}}}
            legacy = {"id": "legacy-action", "type": "create_task", "requested_by": "本人", "status": "pending",
                      "payload": {"title": "旧任务"}, "summary": "旧任务", "created_at": "2026-10-13T00:00:00+00:00"}
            state = {**snapshot["state"], "pending_actions": [original, legacy]}
            await conversations.save_state(directory, state)
            before = conversations.read_state(directory, state["conversation_id"])
            record = self.request("待确认")
            record.data = {**record.data, "tool_name": "真实操作", "summary": "真实操作", "preview": original["preview"]}
            db = SimpleNamespace(scalar=AsyncMock(return_value=1),
                                 scalars=AsyncMock(side_effect=[SimpleNamespace(all=lambda: []),
                                                              SimpleNamespace(all=lambda: [record]), SimpleNamespace(all=lambda: [])]),
                                 commit=AsyncMock())
            history = await read_confirmation_history({"username": "本人"}, db, status="pending", directory=directory)
            self.assertEqual(history["total"], 2)
            self.assertEqual([item["status"] for item in history["items"]], ["pending", "pending"])
            self.assertTrue(all(item["can_decide"] for item in history["items"]))
            self.assertTrue(all(item["conversation_id"] == state["conversation_id"] for item in history["items"]))
            self.assertEqual(history["items"][0]["id"], "request-1")
            self.assertEqual(history["items"][0]["action_id"], "action-1")
            db.scalars = AsyncMock(side_effect=[SimpleNamespace(all=lambda: []), SimpleNamespace(all=lambda: [])])
            second = await read_confirmation_history({"username": "本人"}, db, status="pending", page=2, page_size=1, directory=directory)
            self.assertEqual(second["total"], 2)
            self.assertEqual([item["id"] for item in second["items"]], ["legacy-action"])
            record.data["context"] = {"conversation_id": state["conversation_id"], "conversation_title": state["conversation_title"]}
            for stored, visible in (("待确认", "pending"), ("执行失败", "failed"), ("已执行", "succeeded"), ("已拒绝", "rejected")):
                record.status = stored
                db.scalar = AsyncMock(side_effect=[record, None])
                detail = await read_confirmation_detail("mcp", "request-1", {"username": "本人"}, db, directory=directory)
                self.assertEqual(detail["action"]["id"], "action-1")
                self.assertEqual(detail["action"]["status"], visible)
                self.assertEqual(detail["can_decide"], visible == "pending")
            db.scalar = AsyncMock(return_value=None)
            detail = await read_confirmation_detail("personal_action", "legacy-action", {"username": "本人"}, db, directory=directory)
            self.assertTrue(detail["can_decide"])
            self.assertEqual(detail["action"]["payload"], legacy["payload"])
            record.owner = "别人"
            db.scalar = AsyncMock(return_value=record)
            with self.assertRaises(HTTPException) as raised:
                await read_confirmation_detail("mcp", "request-1", {"username": "本人"}, db, directory=directory)
            self.assertEqual(raised.exception.status_code, 403)
            self.assertEqual(conversations.read_state(directory, state["conversation_id"]), before)
            db.commit.assert_not_awaited()

    async def test_truncated_mcp_card_keeps_true_preview_without_fabricating_action(self):
        with TemporaryDirectory(prefix="oa-test-action-truncated-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            record = self.request("待确认")
            record.data = {**record.data, "tool_name": "原工具", "summary": "原请求", "preview": {"params": {"body": {"value": "原参数"}}},
                           "context": {"conversation_id": snapshot["state"]["conversation_id"], "conversation_title": "原对话"}}
            db = SimpleNamespace(scalar=AsyncMock(side_effect=[record, None]), commit=AsyncMock())
            detail = await read_confirmation_detail("mcp", "request-1", {"username": "本人"}, db, directory=directory)
            self.assertEqual(detail["conversation_id"], snapshot["state"]["conversation_id"])
            self.assertEqual(detail["request_preview"], record.data["preview"])
            self.assertIsNone(detail["action"])
            self.assertIsNone(detail["item"]["action_id"])
            self.assertFalse(detail["can_decide"], "30条截断后不能捏造原操作ID或自动恢复可执行卡")
            self.assertEqual(conversations.read_state(directory)["pending_actions"], [])
            db.commit.assert_not_awaited()

    async def test_removed_personal_actions_use_archive_without_becoming_replayable(self):
        with TemporaryDirectory(prefix="oa-test-action-archive-") as temporary:
            directory = Path(temporary)
            record = BusinessRecord(module="personal_agent_action", owner="本人", status="执行失败", title="原操作",
                                    data={"action_id": "archived-action", "action_type": "create_task", "summary": "原操作",
                                          "payload": {"title": "原任务"}, "conversation_id": "default", "conversation_title": "原对话",
                                          "error": {"status_code": 409, "detail": "原业务拒绝"}})
            db = SimpleNamespace(scalar=AsyncMock(side_effect=[record, None]), commit=AsyncMock())
            detail = await read_confirmation_detail("personal_action", "archived-action", {"username": "本人"}, db, directory=directory)
            self.assertEqual(detail["action"]["payload"], record.data["payload"])
            self.assertEqual(detail["action"]["status"], "failed")
            self.assertEqual(detail["item"]["error"], record.data["error"])
            self.assertEqual(detail["conversation_id"], "default")
            self.assertFalse(detail["can_decide"])
            self.assertEqual(conversations.read_state(directory)["pending_actions"], [])
            self.assertEqual(list(directory.iterdir()), [], "读取历史不能生成会话或补建业务存档")
            db.commit.assert_not_awaited()


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

"""领域路由迁移后，核对回款事务与用印文件补偿。"""

import asyncio
from datetime import date
import hashlib
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
from app.areas.personal_agent import identity_storage
from app.agent_mcp import auth as tool_auth
from app.agent_mcp import service as tool_service
from app.core import generated_file_storage as generated_storage
from app.core.generated_file_records import FILE_MODULE, SPACE_MODULE
from app.areas.personal_agent.ai_space_service import list_space_files, space_file_record, space_file_bytes
from sqlalchemy import func, select


class GeneratedFileStorageBoundaryTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.db = self.sessions()
        self.users = [User(username=name, display_name="同名员工", role=role, role_ids=[role],
                           password_hash="unused", is_active=True)
                      for name, role in (("codex-ai-a", "user"), ("codex-ai-b", "user"), ("codex-ai-admin", "admin"))]
        self.db.add_all(self.users)
        await self.db.commit()
        self.actor = self.users[0]
        self.objects = {}
        self.patches = [patch.object(generated_storage, "_load_credentials", return_value=None),
                        patch("app.agent_mcp.auth.authenticated_identity", new=self.identity),
                        patch.object(generated_storage, "oss_put_editor_revision", new=AsyncMock(side_effect=self.put)),
                        patch.object(generated_storage, "read_generated_bytes", new=AsyncMock(side_effect=self.read)),
                        patch.object(generated_storage, "resolve_generated_scope", wraps=generated_storage.resolve_generated_scope),
                        patch.object(personal_service.settings, "ai_oss_bucket", "codex-ai-test"),
                        patch.object(personal_service.settings, "ai_oss_prefix", "CODEX/AI空间"),
                        patch.object(personal_service.settings, "ai_oss_endpoint", "https://oss.invalid"),
                        patch.object(personal_service.settings, "ai_oss_credentials_file", "isolated-ai-credentials.csv")]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        await self.db.close()
        await self.engine.dispose()

    async def identity(self, db=None):
        return {"username": self.actor.username, "role": self.actor.role, "_actual_role_ids": self.actor.role_ids}

    async def put(self, bucket, key, content, content_type, *, endpoint):
        plan = await self.db.scalar(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE)
                                    .order_by(BusinessRecord.id.desc()))
        self.assertEqual(plan.status, "uploading")
        self.assertEqual(plan.data["path"], f"oss://{bucket}/{key}")
        self.assertEqual(plan.data["endpoint"], endpoint)
        self.objects[plan.data["path"]] = content
        return True

    async def read(self, item, *, max_bytes=20 * 1024 * 1024):
        return self.objects[item.path]

    async def save(self, **overrides):
        args = {"name": "真实结果.xls", "content": b"actual-xls-content", "content_type": "application/vnd.ms-excel",
                "source_kind": "mcp_export", "conversation_id": "source-conversation"}
        args.update(overrides)
        return await generated_storage.save_generated_file(self.db, await self.identity(), **args)

    async def test_real_names_stable_owners_and_one_attachment(self):
        first = await self.save()
        self.assertEqual(first["file"]["status"], "available")
        self.assertEqual(first["file"]["owner_user_id"], self.actor.id)
        self.assertIn(f"/同名员工--u{self.actor.id}/", first["attachment"].path)
        self.assertTrue(first["attachment"].path.endswith("/真实结果.xls"))
        self.assertEqual(first["file"]["attachment_id"], first["attachment"].id)
        self.assertEqual(first["file"]["content_type"], "application/vnd.ms-excel")
        old_folder = first["attachment"].path.split("/" + first["file"]["id"] + "/")[0]
        self.actor.display_name = "改名员工"
        await self.db.commit()
        second = await self.save(name="第二结果.xls")
        self.assertTrue(second["attachment"].path.startswith(old_folder + "/"))
        self.actor = self.users[1]
        third = await self.save()
        self.assertIn(f"/同名员工--u{self.actor.id}/", third["attachment"].path)
        self.assertNotEqual(first["attachment"].path, third["attachment"].path)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 3)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(BusinessRecord)
                                             .where(BusinessRecord.module == SPACE_MODULE)), 2)

    async def test_zero_byte_case_text_create_edit_and_generic_upload_are_preserved(self):
        from app.api_schemas.case_documents import CaseAiDraftCreateInput, CaseAiDraftUpdateInput
        from app.areas.legal.case_documents import create_case_ai_draft, update_case_ai_draft_content
        from app.areas.system.attachments import upload_attachment
        from app.core.constants import AI_SPACE_CATEGORY

        self.actor = self.users[2]
        case = BusinessRecord(module="case", serial_no="CODEX-AI-ZERO", title="零字节兼容案件",
                              owner=self.actor.username, status="草稿", data={})
        self.db.add(case)
        await self.db.commit()
        empty_sha = hashlib.sha256(b"").hexdigest()
        for suffix in ("txt", "md"):
            created = await create_case_ai_draft(case.id, CaseAiDraftCreateInput(name=f"空白.{suffix}", content=""),
                                                 identity=await self.identity(), db=self.db)
            self.assertEqual(created["size"], 0)
            item = await self.db.get(FileAttachment, created["id"])
            old_path = item.path
            edited = await update_case_ai_draft_content(case.id, item.id, CaseAiDraftUpdateInput(content=""),
                                                       identity=await self.identity(), db=self.db)
            self.assertEqual(edited["size"], 0)
            self.assertEqual(self.objects[old_path], b"")
        with patch("app.core.case_automation.advance_case_for_uploaded_document", new=AsyncMock()), \
                patch("app.core.documents._sync_case_document_readiness", new=AsyncMock()):
            uploaded = await upload_attachment(
                file=UploadFile(filename="原空文件.txt", file=BytesIO(b"")), record_id=case.id,
                finance_transaction_id=None, source_case_id=None, customer_guid=None,
                is_license=None, document_date=None, category=AI_SPACE_CATEGORY, remark="",
                identity=await self.identity(), db=self.db,
            )
        self.assertEqual(uploaded["size"], 0)
        records = (await self.db.scalars(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE))).all()
        self.assertEqual(len(records), 5)
        for record in records:
            self.assertEqual(record.status, "available")
            self.assertEqual(record.data["size"], 0)
            self.assertEqual(record.data["sha256"], empty_sha)
            self.assertEqual(self.objects[record.data["path"]], b"")

    async def test_bound_employee_is_authoritative_and_conflicting_binding_rejected(self):
        employee = BusinessRecord(module="hr", serial_no="CODEX-AI-HR", title="真实档案姓名", owner=self.actor.username,
                                  data={"username": self.actor.username, "system_user_id": self.actor.id})
        self.db.add(employee)
        await self.db.commit()
        result = await self.save()
        self.assertEqual(result["file"]["owner_name"], "真实档案姓名")
        self.assertIn("/真实档案姓名--u", result["attachment"].path)
        employee.data = {"username": self.actor.username, "system_user_id": self.users[1].id}
        await self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            await self.save()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(self.objects), 1)

    async def test_missing_config_or_name_never_uploads_or_falls_back(self):
        with patch.object(personal_service.settings, "ai_oss_bucket", ""):
            with self.assertRaises(HTTPException) as raised:
                await self.save()
            self.assertEqual(raised.exception.status_code, 503)
        self.actor.display_name = ""
        await self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            await self.save()
        self.assertEqual(raised.exception.status_code, 422)
        self.assertFalse(self.objects)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)

    async def test_failed_readback_is_tracked_without_available_attachment(self):
        with patch.object(generated_storage, "read_generated_bytes", new=AsyncMock(return_value=b"changed")):
            with self.assertRaises(HTTPException) as raised:
                await self.save()
        self.assertEqual(raised.exception.status_code, 409)
        plan = await self.db.scalar(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE))
        self.assertEqual(plan.status, "uncertain")
        self.assertIn(plan.data["path"], self.objects)
        self.assertIsNone(plan.data["attachment_id"])
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)

    async def test_callback_failure_keeps_plan_and_rolls_back_final_attachment(self):
        callback = AsyncMock(side_effect=RuntimeError("isolated final transaction failure"))
        with self.assertRaises(HTTPException):
            await self.save(on_available=callback)
        plan = await self.db.scalar(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE))
        self.assertEqual(plan.status, "uncertain")
        self.assertEqual(plan.data["error"], "文件保存未完成（RuntimeError），请人工核对")
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)
        self.assertEqual(len(self.objects), 1)

    async def test_owner_access_rejects_page_admin_but_real_admin_reads(self):
        result = await self.save()
        owner_id = self.actor.id
        self.actor = self.users[1]
        spoof = {"username": self.actor.username, "role": "admin", "_actual_role_ids": ["admin"], "_page_menu_capability": True}
        with self.assertRaises(HTTPException) as raised:
            await space_file_record(result["file"]["id"], spoof, self.db)
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual((await list_space_files(await self.identity(), self.db, page=1, page_size=20))["total"], 0)
        self.actor = self.users[2]
        item = await space_file_record(result["file"]["id"], await self.identity(), self.db)
        self.assertEqual(item.data["owner_user_id"], owner_id)
        listing = await list_space_files(await self.identity(), self.db, page=1, page_size=20, owner_user_id=owner_id)
        self.assertEqual(listing["total"], 1)
        from app.core.permissions import _require_record_module_menu
        from app.core.system import _record_module_menu_allowed
        with self.assertRaises(HTTPException) as raised:
            await _require_record_module_menu(FILE_MODULE, await self.identity(), self.db, action="编辑")
        self.assertEqual(raised.exception.status_code, 403)
        self.assertFalse(_record_module_menu_allowed(FILE_MODULE, spoof, {}))

    async def test_download_checks_real_bytes_and_name_validation(self):
        for name in ("../x.xls", "a\\b.xls", "x\x00.xls", "C:x.xls"):
            with self.assertRaises(HTTPException):
                generated_storage.safe_original_name(name)
        result = await self.save()
        with patch("app.areas.personal_agent.ai_space_service.read_generated_bytes", new=AsyncMock(return_value=b"actual-xls-content")):
            item, content = await space_file_bytes(result["file"]["id"], await self.identity(), self.db)
        self.assertEqual(item["id"], result["file"]["id"])
        self.assertEqual(content, b"actual-xls-content")
        with patch("app.areas.personal_agent.ai_space_service.read_generated_bytes", new=AsyncMock(return_value=b"wrong")):
            with self.assertRaises(HTTPException) as raised:
                await space_file_bytes(result["file"]["id"], await self.identity(), self.db)
        self.assertEqual(raised.exception.status_code, 409)

    async def test_case_attachment_is_indexed_once_and_revisions_keep_original_bytes(self):
        self.actor = self.users[2]
        case = BusinessRecord(module="case", serial_no="CODEX-AI-CASE", title="真实案件名称", owner=self.actor.username,
                              status="草稿", data={})
        self.db.add(case)
        await self.db.commit()
        with patch("app.core.permissions._require_case_attachment_upload_access", new=AsyncMock()):
            first = await self.save(case_record=case, source_kind="case_ai_draft")
            old_path = first["attachment"].path
            second = await self.save(case_record=case, attachment=first["attachment"], content=b"second-revision",
                                     source_kind="case_ai_draft")
        self.assertEqual(first["attachment"].id, second["attachment"].id)
        self.assertEqual(second["attachment"].record_id, case.id)
        self.assertEqual(second["file"]["case_id"], case.id)
        self.assertIn(f"/CODEX-AI-CASE-真实案件名称--c{case.id}/", second["attachment"].path)
        self.assertNotEqual(old_path, second["attachment"].path)
        self.assertEqual(self.objects[old_path], b"actual-xls-content")
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 1)
        listing = await list_space_files(await self.identity(), self.db, page=1, page_size=20)
        self.assertEqual(listing["total"], 2)
        self.assertEqual({item["attachment_id"] for item in listing["items"]}, {second["attachment"].id})

    async def test_final_commit_failure_keeps_remote_object_and_uncertain_plan(self):
        commit = self.db.commit
        calls = 0

        async def fail_final_commit():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("isolated final commit failed")
            await commit()

        with patch.object(self.db, "commit", new=fail_final_commit):
            with self.assertRaises(HTTPException):
                await self.save()
        self.assertEqual(calls, 3)
        plan = await self.db.scalar(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE))
        self.assertEqual(plan.status, "uncertain")
        self.assertIn(plan.data["path"], self.objects)
        self.assertIsNone(plan.data["attachment_id"])
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)

    async def test_cancelled_upload_keeps_uncertain_plan(self):
        import asyncio

        with patch.object(generated_storage, "oss_put_editor_revision", new=AsyncMock(side_effect=asyncio.CancelledError())):
            with self.assertRaises(asyncio.CancelledError):
                await self.save()
        plan = await self.db.scalar(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE))
        self.assertEqual(plan.status, "uncertain")
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)

    async def test_no_case_message_capability_and_true_message_save(self):
        from app.areas.personal_agent.ai_space_service import save_space_message

        identity = {**await self.identity(), "display_name": self.actor.display_name}
        state = {"conversation_id": "original", "messages": [], "pending_actions": []}
        with patch.object(personal_service, "ModelToolSession", wraps=personal_service.ModelToolSession) as tool_session, \
                patch("app.core.oss_attachments._load_credentials", return_value=None), \
                patch.object(personal_service, "_agent_skill_for_identity", new=AsyncMock(return_value=SimpleNamespace(id="test", name="测试技能"))), \
                patch.object(personal_service, "prepare_materials", new=AsyncMock(return_value={"case": None, "readings": [], "can_save_document": False})), \
                patch.object(personal_service, "build_context", new=AsyncMock(return_value={})), \
                patch.object(personal_service, "_prompt_messages", return_value=[]), \
                patch.object(personal_service, "request_model", new=AsyncMock(return_value="真实完整回答")), \
                patch.object(personal_service, "_save_state", new=AsyncMock()):
            result = await personal_service._generate_response(identity, self.db, "生成文书", AsyncMock(), state=state,
                                                               skill_id="test", attachment_ids=[], case_id=None, document_ids=[],
                                                               response_mode="fast", on_progress=None)
        message = result["state"]["messages"][-1]
        tool_session.assert_called_once_with(conversation_id="original")
        self.assertTrue(message["can_save_document"])
        self.assertTrue(message["can_save_personal_document"])
        self.assertFalse(message["can_save_case_document"])
        with TemporaryDirectory(prefix="oa-test-personal-message-") as temporary:
            directory = Path(temporary)
            snapshot = await conversations.create_conversation(directory)
            snapshot["state"]["messages"] = [message]
            await conversations.save_state(directory, snapshot["state"])
            body = SimpleNamespace(conversation_id=snapshot["state"]["conversation_id"], message_index=0,
                                   name="真实文书.docx", expected_content_sha256=hashlib.sha256(message["content"].encode()).hexdigest())
            with patch.object(personal_service, "_user_dir", return_value=directory):
                saved = await save_space_message(body, identity, self.db)
                self.assertEqual(saved["source_kind"], "assistant_message")
                self.assertEqual(saved["conversation_id"], body.conversation_id)
                body.expected_content_sha256 = "0" * 64
                with self.assertRaises(HTTPException) as raised:
                    await save_space_message(body, identity, self.db)
                self.assertEqual(raised.exception.status_code, 409)

    async def test_ai_endpoint_is_separate_for_signed_download_and_missing_config(self):
        from urllib.parse import urlsplit
        from app.core.oss_attachments import oss_attachment_signed_url

        old = SimpleNamespace(path="oss://historical-test/old.docx")
        new = SimpleNamespace(path="oss://codex-ai-test/CODEX/AI空间/new.docx")
        with patch("app.core.oss_attachments._load_credentials", return_value=("isolated-id", "isolated-secret")) as load, \
                patch.object(personal_service.settings, "oss_endpoint", "https://oss-old.invalid"), \
                patch.object(personal_service.settings, "ai_oss_endpoint", "https://oss-ai.invalid"), \
                patch.object(personal_service.settings, "ai_oss_credentials_file", "explicit-ai-credentials.csv"):
            self.assertEqual(urlsplit(oss_attachment_signed_url(old)).hostname, "historical-test.oss-old.invalid")
            load.assert_called_with()
            self.assertEqual(urlsplit(oss_attachment_signed_url(new)).hostname, "codex-ai-test.oss-ai.invalid")
            load.assert_called_with("explicit-ai-credentials.csv")
            with patch.object(personal_service.settings, "ai_oss_endpoint", ""):
                with self.assertRaises(HTTPException) as raised:
                    oss_attachment_signed_url(new)
                self.assertEqual(raised.exception.status_code, 503)
                self.assertEqual(urlsplit(oss_attachment_signed_url(old)).hostname, "historical-test.oss-old.invalid")
        with patch.object(personal_service.settings, "ai_oss_credentials_file", ""), \
                patch.object(personal_service.settings, "oss_credentials_file", "must-not-inherit.csv"):
            with self.assertRaises(HTTPException) as raised:
                oss_attachment_signed_url(new)
            self.assertEqual(raised.exception.status_code, 503)

    async def test_unlinked_hr_owner_is_creator_not_employee_binding(self):
        self.db.add(BusinessRecord(module="hr", serial_no="CODEX-AI-UNLINKED", title="其他档案姓名",
                                   owner=self.actor.username, data={}))
        await self.db.commit()
        saved = await self.save()
        self.assertEqual(saved["file"]["owner_name"], self.actor.display_name)
        self.assertIn(f"/同名员工--u{self.actor.id}/", saved["attachment"].path)

    async def test_generic_case_ai_upload_preserves_shared_storage_and_workflow(self):
        from app.areas.system.attachments import upload_attachment
        from app.core.constants import AI_SPACE_CATEGORY

        self.actor = self.users[2]
        case = BusinessRecord(module="case", serial_no="CODEX-AI-GENERIC", title="隔离案件",
                              owner=self.actor.username, status="草稿", data={})
        self.db.add(case)
        await self.db.commit()
        file = UploadFile(filename="草稿.docx", file=BytesIO(b"uploaded-unchanged"))
        with patch("app.core.permissions._require_case_attachment_upload_access", new=AsyncMock()), \
                patch("app.core.case_automation.advance_case_for_uploaded_document", new=AsyncMock()) as advance, \
                patch("app.core.documents._sync_case_document_readiness", new=AsyncMock()) as readiness, \
                patch("app.areas.system.attachments.Path.write_bytes", side_effect=AssertionError("AI must not write local")):
            result = await upload_attachment(file=file, record_id=case.id, finance_transaction_id=None,
                                             source_case_id=None, customer_guid=None, is_license=None, document_date=None,
                                             category=AI_SPACE_CATEGORY, remark="原上传备注", identity=await self.identity(), db=self.db)
        self.assertEqual(result["storage_backend"], "oss")
        self.assertEqual(result["category"], AI_SPACE_CATEGORY)
        self.assertEqual(result["remark"], "原上传备注")
        advance.assert_awaited_once()
        readiness.assert_awaited_once()
        from app.data_models.records import WorkflowEvent
        event = await self.db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == case.id))
        self.assertEqual(event.action, "上传归档材料")
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 1)
        self.assertEqual(len(self.objects), 1)
        with patch.object(file, "read", new=AsyncMock(return_value=b"x" * (20 * 1024 * 1024 + 1))), \
                patch("app.core.permissions._require_case_attachment_upload_access", new=AsyncMock()), \
                patch("app.core.cases._save_case_ai_upload", new=AsyncMock()) as save:
            with self.assertRaises(HTTPException) as raised:
                await upload_attachment(file=file, record_id=case.id, finance_transaction_id=None,
                                        source_case_id=None, customer_guid=None, is_license=None, document_date=None,
                                        category=AI_SPACE_CATEGORY, remark="", identity=await self.identity(), db=self.db)
            self.assertEqual(raised.exception.status_code, 413)
            save.assert_not_awaited()

    async def test_configuration_ready_is_not_put_permission_proof_and_reads_do_not_create_space(self):
        from app.areas.personal_agent.ai_space_service import space_info

        with patch("app.core.oss_attachments._load_credentials", return_value=None):
            info = await space_info(await self.identity(), self.db)
            self.assertTrue(info["configured"])
            self.assertFalse(info["put_verified"])
            self.assertEqual(info["verification_scope"], "configuration_only")
            with patch.object(personal_service.settings, "ai_oss_endpoint", ""):
                with self.assertRaises(HTTPException) as raised:
                    await space_info(await self.identity(), self.db)
                self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(BusinessRecord)
                                             .where(BusinessRecord.module == SPACE_MODULE)), 0)
        self.assertFalse(self.objects)

    async def test_committed_available_state_is_not_rewritten_as_failed_when_ack_is_lost(self):
        commit = self.db.commit
        calls = 0

        async def commit_with_lost_ack():
            nonlocal calls
            calls += 1
            await commit()
            if calls == 2:
                raise RuntimeError("isolated committed response lost")

        with patch.object(self.db, "commit", new=commit_with_lost_ack):
            with self.assertRaises(HTTPException) as raised:
                await self.save()
        self.assertEqual(raised.exception.detail["status"], "available")
        self.assertIn("文件已持久提交为 available", raised.exception.detail["detail"])
        plan = await self.db.scalar(select(BusinessRecord).where(BusinessRecord.module == FILE_MODULE))
        self.assertEqual(plan.status, "available")
        self.assertIsNone(plan.data["error"])
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 1)


class PersonalIdentityStorageBoundaryTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = TemporaryDirectory(prefix="CODEX-personal-identity-")
        root = Path(self.temporary.name)
        self.engine = create_async_engine("sqlite+aiosqlite:///" + (root / "identity.sqlite").as_posix())
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.db = self.sessions()
        self.actor = User(username="CODEX-identity-owner", display_name="真实员工", role="user", role_ids=["user"],
                          password_hash="unused", is_active=True)
        self.db.add(self.actor)
        await self.db.commit()
        self.username = self.actor.username
        self.objects = {}
        self.writer = AsyncMock(side_effect=self.put)
        self.patches = [patch.object(generated_storage, "_load_credentials", return_value=None),
                        patch.object(identity_storage, "_load_credentials", return_value=None),
                        patch.object(tool_auth, "authenticated_identity", new=self.identity),
                        patch.object(generated_storage, "oss_put_editor_revision", new=self.writer),
                        patch.object(generated_storage, "read_generated_bytes", new=AsyncMock(side_effect=self.read)),
                        patch.object(personal_service, "_user_permission_payload", new=AsyncMock(return_value={
                            "menu_keys": ["task"], "action_keys": ["task.read"], "data_scope": "本人数据",
                        })),
                        patch.object(personal_service.settings, "personal_agent_root", str(root / "runtime")),
                        patch.object(personal_service.settings, "ai_oss_bucket", "codex-ai-test"),
                        patch.object(personal_service.settings, "ai_oss_prefix", "CODEX/AI空间"),
                        patch.object(personal_service.settings, "ai_oss_endpoint", "https://oss.invalid"),
                        patch.object(personal_service.settings, "ai_oss_credentials_file", "isolated-credentials.csv")]
        for item in self.patches:
            item.start()
        self.context = tool_auth.AuthContext(None, "isolated-request-token", {
            "method": "POST", "path": personal_service.settings.api_prefix + "/personal-agent/messages",
        })
        self.context_token = tool_auth._auth_context.set(self.context)

    async def asyncTearDown(self):
        tool_auth._auth_context.reset(self.context_token)
        for item in reversed(self.patches):
            item.stop()
        await self.db.close()
        await self.engine.dispose()
        self.temporary.cleanup()

    async def identity(self, db=None):
        return {"username": self.username}

    async def put(self, bucket, key, content, content_type, *, endpoint):
        self.objects[f"oss://{bucket}/{key}"] = content
        return True

    async def read(self, item, *, max_bytes):
        return self.objects[item.path]

    async def safe_identity(self):
        return await personal_service.personal_identity(await self.identity(), self.db)

    async def persist(self, *, db=None, conversation_id="default"):
        identity = await self.safe_identity()
        return await identity_storage.persist_personal_identity(
            db or self.db, identity, content=personal_service._identity_markdown(identity), conversation_id=conversation_id,
        )

    async def claims(self):
        return (await self.db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == SPACE_MODULE, BusinessRecord.serial_no.like("PAID-%"),
        ).execution_options(populate_existing=True))).all()

    async def test_post_archives_only_actual_identity_before_model_and_preserves_local_file(self):
        forged = {"username": self.actor.username, "display_name": "伪造姓名", "role": "admin", "action_keys": ["all"]}

        async def generate(identity, db, text, on_delta, **kwargs):
            self.assertEqual(identity["role"], "user")
            self.assertEqual(identity["action_keys"], ["task.read"])
            self.assertEqual(len(self.objects), 1)
            expected = personal_service._identity_markdown(identity)
            self.assertEqual(next(iter(self.objects.values())), expected.encode("utf-8"))
            self.assertEqual(personal_service._identity_path(self.actor.username).read_text(encoding="utf-8"), expected)
            return {"state": kwargs["state"], "response": "模型回答不是身份文件来源"}

        with patch.object(personal_service, "_generate_response", new=AsyncMock(side_effect=generate)):
            await personal_service.generate_response(forged, self.db, "第一次真实提问", AsyncMock())
            await personal_service.generate_response(forged, self.db, "再次提问", AsyncMock())
        self.assertEqual(self.writer.await_count, 1)
        files = await list_space_files(await self.identity(), self.db, page=1, page_size=20)
        self.assertEqual(files["total"], 1)
        self.assertEqual(files["items"][0]["source_kind"], "personal_identity")
        self.assertEqual(files["items"][0]["name"], "IDENTITY.md")
        self.assertEqual(files["items"][0]["conversation_id"], "default")

    async def test_reads_never_claim_or_put_identity(self):
        self.context.scope["method"] = "GET"
        identity = await self.safe_identity()
        await personal_service.personal_state(identity, self.db)
        await personal_service.manage_conversations(identity, db=self.db)
        self.assertEqual(await self.claims(), [])
        self.writer.assert_not_awaited()

    async def test_versions_reuse_history_hash_and_keep_original_bytes(self):
        first = await self.persist()
        original = dict(self.objects)
        self.actor.display_name = "真实改名员工"
        await self.db.commit()
        second = await self.persist(conversation_id="other-conversation")
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.actor.display_name = "真实员工"
        await self.db.commit()
        again = await self.persist(conversation_id="third-conversation")
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(self.writer.await_count, 2)
        self.assertTrue(all(self.objects[path] == raw for path, raw in original.items()))
        self.assertEqual(len(await self.claims()), 2)
        self.assertTrue(all(len(row.serial_no) <= 64 and row.status == "available" for row in await self.claims()))

    async def test_real_auth_and_post_origin_are_required(self):
        identity = await self.safe_identity()
        for method, path in (("GET", "/personal-agent/state"), ("POST", "/personal-agent/conversations")):
            self.context.scope.update(method=method, path=personal_service.settings.api_prefix + path)
            with self.assertRaises(HTTPException) as raised:
                await self.persist()
            self.assertEqual(raised.exception.status_code, 403)
        self.context.scope.update(method="POST", path=personal_service.settings.api_prefix + "/personal-agent/messages")
        with self.assertRaises(HTTPException) as raised:
            await identity_storage.persist_personal_identity(
                self.db, {**identity, "username": "another-person"}, content="不可信内容", conversation_id="default")
        self.assertEqual(raised.exception.status_code, 403)
        self.context.active = False
        with self.assertRaises(HTTPException) as raised:
            await self.persist()
        self.assertEqual(raised.exception.status_code, 401)
        self.writer.assert_not_awaited()
        self.assertEqual(await self.claims(), [])

    async def test_failed_and_uncertain_claims_never_automatically_retry(self):
        with patch.object(identity_storage, "save_generated_file", new=AsyncMock(side_effect=HTTPException(503, "配置失败"))):
            with self.assertRaises(HTTPException):
                await self.persist()
        self.assertEqual((await self.claims())[0].status, "failed")
        with self.assertRaises(HTTPException) as raised:
            await self.persist(conversation_id="different-conversation")
        self.assertEqual(raised.exception.detail["status"], "failed")
        self.writer.assert_not_awaited()
        self.actor.display_name = "新内容员工"
        await self.db.commit()
        with patch.object(generated_storage, "read_generated_bytes", new=AsyncMock(side_effect=HTTPException(502, "读取失败"))):
            with self.assertRaises(HTTPException):
                await self.persist()
        with self.assertRaises(HTTPException) as raised:
            await self.persist()
        self.assertEqual(raised.exception.detail["status"], "uncertain")
        self.assertEqual(self.writer.await_count, 1)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)

    async def test_cancelled_upload_retains_uncertain_claim(self):
        with patch.object(generated_storage, "oss_put_editor_revision", new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await self.persist()
        self.assertEqual((await self.claims())[0].status, "uncertain")
        with self.assertRaises(HTTPException) as raised:
            await self.persist()
        self.assertEqual(raised.exception.detail["status"], "uncertain")
        self.writer.assert_not_awaited()

    async def test_claim_available_is_atomic_with_file_commit_and_lost_ack_does_not_reupload(self):
        commit = self.db.commit
        count = 0

        async def lost_ack():
            nonlocal count
            count += 1
            await commit()
            if count == 3:
                raise RuntimeError("isolated committed acknowledgment lost")

        with patch.object(self.db, "commit", new=lost_ack):
            with self.assertRaises(HTTPException):
                await self.persist()
        claim = (await self.claims())[0]
        self.assertEqual(claim.status, "available")
        file = await self.db.get(BusinessRecord, claim.data["file_record_id"])
        self.assertEqual(file.status, "available")
        self.assertEqual(file.data["file_id"], claim.data["file_id"])
        again = await self.persist()
        self.assertEqual(again["id"], claim.data["file_id"])
        self.assertEqual(self.writer.await_count, 1)

    async def test_final_commit_failure_does_not_publish_claim_or_replay(self):
        commit = self.db.commit
        count = 0

        async def fail_final():
            nonlocal count
            count += 1
            if count == 3:
                raise RuntimeError("isolated final transaction failed")
            await commit()

        with patch.object(self.db, "commit", new=fail_final):
            with self.assertRaises(HTTPException):
                await self.persist()
        claim = (await self.claims())[0]
        self.assertEqual(claim.status, "uncertain")
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 0)
        with self.assertRaises(HTTPException):
            await self.persist()
        self.assertEqual(self.writer.await_count, 1)

    async def test_different_sessions_compete_on_persistent_unique_claim(self):
        identity = await self.safe_identity()
        await generated_storage.resolve_generated_scope(self.db, identity)
        await self.db.commit()
        original = identity_storage._claim
        arrivals = 0
        ready = asyncio.Event()

        async def simultaneous(db, serial):
            nonlocal arrivals
            claim = await original(db, serial)
            if claim is None:
                arrivals += 1
                if arrivals == 2:
                    ready.set()
                await asyncio.wait_for(ready.wait(), 5)
            return claim

        async def contender(conversation_id):
            async with self.sessions() as db:
                return await identity_storage.persist_personal_identity(
                    db, identity, content=personal_service._identity_markdown(identity), conversation_id=conversation_id)

        with patch.object(identity_storage, "_claim", new=simultaneous):
            results = await asyncio.gather(contender("first-conversation"), contender("second-conversation"), return_exceptions=True)
        for result in results:
            if isinstance(result, HTTPException):
                self.assertEqual(result.status_code, 409)
            else:
                self.assertIsInstance(result, dict)
                self.assertEqual(result["status"], "available")
        self.assertTrue(any(isinstance(result, dict) for result in results))
        self.assertEqual(self.writer.await_count, 1)
        self.assertEqual(len(await self.claims()), 1)
        self.assertEqual(await self.db.scalar(select(func.count()).select_from(FileAttachment)), 1)

    async def test_uploading_claim_cannot_be_taken_over_by_another_session(self):
        identity = await self.safe_identity()
        started = asyncio.Event()
        finish = asyncio.Event()

        async def blocked_put(*args, **kwargs):
            started.set()
            await asyncio.wait_for(finish.wait(), 5)
            return await self.put(*args, **kwargs)

        with patch.object(generated_storage, "oss_put_editor_revision", new=AsyncMock(side_effect=blocked_put)) as writer:
            first = asyncio.create_task(self.persist())
            try:
                await asyncio.wait_for(started.wait(), 5)
                async with self.sessions() as db:
                    with self.assertRaises(HTTPException) as raised:
                        await identity_storage.persist_personal_identity(
                            db, identity, content=personal_service._identity_markdown(identity), conversation_id="other-session")
                    self.assertEqual(raised.exception.detail["status"], "uploading")
                    self.assertEqual(raised.exception.status_code, 409)
            finally:
                finish.set()
                await first
            self.assertEqual(writer.await_count, 1)
        self.assertEqual((await self.claims())[0].status, "available")


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

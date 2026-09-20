"""合并后的关联与只读权限回归，数据库和附件均独立清理。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import select

import finance_0916_batch_test as fixtures
from finance_0916_batch_test import API, IDENTITY, app, current_identity
from app.models import AgentDocument, BusinessRecord, FileAttachment, RolePermission, User, WorkflowEvent


class MergeVisibilityTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.FinanceBatchTest.asyncSetUp
    asyncTearDown = fixtures.FinanceBatchTest.asyncTearDown

    async def test_case_reader_sees_source_task_without_write_permission(self):
        with tempfile.TemporaryDirectory(prefix="CODEX-merge-task-") as directory:
            path = Path(directory) / "material.txt"
            path.write_text("原任务附件", encoding="utf-8")
            async with self.sessions() as db:
                user = await db.scalar(select(User).where(User.username == IDENTITY["username"]))
                user.role = "user"
                user.role_ids = ["user"]
                db.add(RolePermission(role="user", display_name="案件查看角色", menu_keys=["case-mine"],
                    field_keys=[], data_scope="本人及共享数据"))
                db.add(User(username="CODEX-outsider", display_name="无关人员", role="user", role_ids=["user"],
                    department="other", password_hash="unused", is_active=True))
                case = await db.get(BusinessRecord, self.case_id)
                case.data = {**case.data, "merged_sources": [{"id": 90001, "serial_no": "CODEX-source", "data": {}}]}
                task = BusinessRecord(module="task", serial_no="CODEX-merge-task", title="来源任务",
                    owner="other", status="进行中", data={"case_no": "CODEX-source", "source": "案件任务", "initiator": "other"})
                other = BusinessRecord(module="task", serial_no="CODEX-unrelated-task", title="其他任务",
                    owner="other", data={"case_no": "CODEX-other"})
                db.add_all([task, other]); await db.flush()
                attachment = FileAttachment(record_id=task.id, category="任务资料附件", original_name=path.name,
                    stored_name=path.name, path=str(path), size=path.stat().st_size, uploader="other")
                db.add_all([attachment, WorkflowEvent(record_id=task.id, action="原始日志", operator="other")])
                await db.commit()
                task_id, other_id, attachment_id = task.id, other.id, attachment.id
            app.dependency_overrides[current_identity] = lambda: {**IDENTITY, "role": "user", "role_ids": ["user"]}
            base = f"{API}/cases/{self.case_id}/tasks"
            result = await self.client.get(base)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertIn(task_id, [item["id"] for item in result.json()["items"]])
            result = await self.client.get(f"{base}/{task_id}")
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["history"][0]["action"], "原始日志")
            self.assertEqual(result.json()["materials"][0]["task_context_id"], task_id)
            with patch("app.core.storage.UPLOAD_ROOT", Path(directory)):
                result = await self.client.get(f"{base}/{task_id}/attachments/{attachment_id}/download")
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.content.decode("utf-8"), "原任务附件")
            self.assertEqual((await self.client.get(f"{base}/{other_id}")).status_code, 404)
            self.assertEqual((await self.client.get(f"{API}/tasks/{task_id}/history")).status_code, 403)
            app.dependency_overrides[current_identity] = lambda: {"username": "CODEX-outsider", "role": "user"}
            self.assertIn((await self.client.get(f"{base}/{task_id}")).status_code, [403, 404])

    async def test_merge_serial_clue_and_converted_fee_preserves_content(self):
        async with self.sessions() as db:
            source = BusinessRecord(module="case", serial_no="CODEX-merge-source", title="来源",
                owner=IDENTITY["username"], customer="Batch customer", status="一审准备开庭",
                data={"case_type": "民事争议", "investigation_clue": "CODEX-clue-number"})
            clue = BusinessRecord(module="clue", serial_no="CODEX-clue-number", title="原线索",
                owner=IDENTITY["username"], data={"original": "完整信息"})
            db.add_all([source, clue]); await db.flush()
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {"converted_case_id": source.id, "amount": 100, "expense_scope": "律所"}
            document = AgentDocument(job_no="CODEX-merge-document", template_id=1, record_id=source.id,
                title="来源文档", content="完整原文", creator=IDENTITY["username"])
            db.add(document); await db.commit()
            source_id, clue_id, document_id = source.id, clue.id, document.id
        result = await self.client.post(f"{API}/cases/{self.case_id}/merge", json={"source_case_no": "CODEX-merge-source"})
        self.assertEqual(result.status_code, 200, result.text)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            self.assertIn(clue_id, case.data["investigation_clue_ids"])
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(fee.data["case_id"], self.case_id)
            self.assertEqual(fee.data["converted_case_id"], self.case_id)
            self.assertEqual(fee.data["amount"], 100)
            document = await db.get(AgentDocument, document_id)
            self.assertEqual(document.record_id, self.case_id)
            self.assertEqual(document.content, "完整原文")
            self.assertEqual((await db.get(BusinessRecord, source_id)).status, "已合并")
            # 模拟旧版本只迁移附件、遗漏生成记录的实际历史状态。
            document.record_id = source_id
            await db.commit()
        from scripts.repair_case_relations import plan
        from app.core.case_relation_repair import repair_case_relations
        spec = {"existing_merges": [{"source": "CODEX-merge-source", "target": "CODEX-0916-case"}]}
        async with self.sessions() as db:
            snapshot = await plan(spec, db)
            self.assertEqual([row["id"] for row in snapshot["tables"]["agent_documents"]], [document_id])
            self.assertEqual({row["id"] for row in snapshot["relations"]}, {source_id, self.case_id})
            await db.rollback()
        async with self.sessions() as db:
            await repair_case_relations(spec, db)
            await db.commit()
        async with self.sessions() as db:
            self.assertEqual((await db.get(AgentDocument, document_id)).record_id, self.case_id)
            snapshot = await plan(spec, db)
            self.assertEqual(snapshot["tables"], {})
            await db.rollback()

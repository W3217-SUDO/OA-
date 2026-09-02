import importlib
import tempfile
import unittest
from pathlib import Path

import httpx
from docx import Document
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, SystemParameter, User, WorkflowEvent
from app.security import current_identity


main_module = importlib.import_module("app.main")
IDENTITY = {"username": "CODEX-828-ROW5-user", "display_name": "第5行经办人", "role": "user", "department": "上海分所"}


class CaseDocumentOperationsRow5Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="codex-828-row5-")
        self.previous_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = Path(self.temp_dir.name)
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-828-ROW5-CASE", title="第5行案件文档操作验收",
                customer="第5行客户", status="文书准备", owner=IDENTITY["username"], department=IDENTITY["department"],
                data={"case_type": "民事案件", "handling_lawyers": ["第5行律师"], "opponent": "第5行被告", "settlement_amount": "120000"},
            )
            unrelated = BusinessRecord(
                module="contract", serial_no="CODEX-828-ROW5-CON", title="第5行无关合同",
                customer="第5行客户", status="草稿", owner=IDENTITY["username"], department=IDENTITY["department"], data={},
            )
            db.add_all([
                case, unrelated,
                User(
                    username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"], role="user", role_ids=["user"], password_hash="test-only",
                ),
                SystemParameter(category="case_file_type", code="ROW5-SUBJECT", name="主体及委托资料", sort_order=1, is_active=True),
                SystemParameter(category="case_file_type", code="ROW5-COURT", name="法院诉讼文书", sort_order=2, is_active=True),
            ])
            await db.flush()
            self.case_id = case.id
            self.unrelated_id = unrelated.id
            own_path = Path(self.temp_dir.name) / "own.txt"; own_path.write_text("own", encoding="utf-8")
            other_path = Path(self.temp_dir.name) / "other.txt"; other_path.write_text("other", encoding="utf-8")
            unrelated_path = Path(self.temp_dir.name) / "contract.txt"; unrelated_path.write_text("contract", encoding="utf-8")
            own = FileAttachment(record_id=case.id, category="主体及委托资料", original_name="own.txt", stored_name="own.txt", content_type="text/plain", size=3, path=str(own_path), uploader=IDENTITY["username"], remark="")
            other = FileAttachment(record_id=case.id, category="主体及委托资料", original_name="other.txt", stored_name="other.txt", content_type="text/plain", size=5, path=str(other_path), uploader="another-user", remark="")
            unrelated_attachment = FileAttachment(record_id=unrelated.id, category="合同文档", original_name="contract.txt", stored_name="contract.txt", content_type="text/plain", size=8, path=str(unrelated_path), uploader=IDENTITY["username"], remark="")
            db.add_all([own, other, unrelated_attachment]); await db.commit()
            self.own_id, self.other_id, self.unrelated_attachment_id = own.id, other.id, unrelated_attachment.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row5.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides)
        main_module.UPLOAD_ROOT = self.previous_upload_root
        await self.engine.dispose(); self.temp_dir.cleanup()

    async def test_delete_is_atomic_and_limited_to_current_uploader_for_ordinary_user(self):
        denied = await self.client.post(f"{settings.api_prefix}/cases/attachments/delete", json={"attachment_ids": [self.own_id, self.other_id]})
        self.assertEqual(denied.status_code, 403, denied.text)
        self.assertIn("只能删除本人上传的文件", denied.json()["detail"])
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(FileAttachment, self.own_id))
            self.assertIsNotNone(await db.get(FileAttachment, self.other_id))
        allowed = await self.client.post(f"{settings.api_prefix}/cases/attachments/delete", json={"attachment_ids": [self.own_id]})
        self.assertEqual(allowed.status_code, 200, allowed.text)

    async def test_move_changes_only_current_case_file_category_and_writes_audit(self):
        moved = await self.client.post(
            f"{settings.api_prefix}/cases/{self.case_id}/attachments/move",
            json={"attachment_ids": [self.own_id], "category": "法院诉讼文书"},
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(FileAttachment, self.own_id)).category, "法院诉讼文书")
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id, WorkflowEvent.action == "更改案件文档目录")), 1)
        unrelated = await self.client.post(
            f"{settings.api_prefix}/cases/{self.case_id}/attachments/move",
            json={"attachment_ids": [self.unrelated_attachment_id], "category": "法院诉讼文书"},
        )
        self.assertEqual(unrelated.status_code, 409, unrelated.text)

    async def test_new_legacy_generation_actions_create_distinct_formal_documents(self):
        expected = {
            "archive-cover": ("归档封面", "案件卷宗"),
            "compensation-payment-application": ("代收代付赔偿款申请单", "赔偿款金额：120000"),
        }
        for document_type, (name, visible_text) in expected.items():
            response = await self.client.post(f"{settings.api_prefix}/cases/{self.case_id}/documents/{document_type}")
            self.assertEqual(response.status_code, 201, response.text)
            self.assertIn(name, response.json()["original_name"])
            async with self.sessions() as db:
                attachment = await db.get(FileAttachment, response.json()["id"])
                self.assertEqual(attachment.category, "庭审及庭后文件")
                text = "\n".join(paragraph.text for paragraph in Document(attachment.path).paragraphs)
            self.assertIn(visible_text, text)


if __name__ == "__main__":
    unittest.main()

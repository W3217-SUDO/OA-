"""10.22 第 17 行：刑事案件文档目录按旧系统刑事目录，上传/移动/转入校验与文书落点按案件类型区分。

根因：正式目录是全类型共用的民事常量（主体及委托资料等五个），刑事案件没有自己的目录。
"""

import unittest
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import DEFAULT_SYSTEM_PARAMETERS, case_document_category_for
from app.core.documents import _validate_case_attachment_move_category, _validate_case_formal_document_category
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1022-17-"
IDENTITY = {"username": f"{PREFIX}admin", "display_name": "第17行管理员", "role": "admin", "department": "上海分所"}
CRIMINAL_STAGE = ["委托手续及证明", "起诉书及证据", "辩论意见及证据", "法院裁判文书"]
CIVIL_STAGE = ["主体及委托资料", "起诉材料及证据", "答辩材料及证据", "法院诉讼文书", "庭审及庭后文件"]


class CriminalCaseDocumentFoldersRow17Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            criminal = self._case(f"{PREFIX}XS-001", "刑事案件")
            history = self._case(f"{PREFIX}XS-002", "刑事案件")
            civil = self._case(f"{PREFIX}MS-001", "民事争议")
            db.add_all([
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"],
                     role="admin", password_hash="x", is_active=True),
                SystemParameter(category="case_type", code="110", name="民事争议", extra={}, is_active=True),
                SystemParameter(category="case_type", code="120", name="刑事案件", extra={}, is_active=True),
                *[SystemParameter(category=category, code=code, name=name, extra=dict(extra), is_active=True)
                  for category, code, name, extra in DEFAULT_SYSTEM_PARAMETERS if category == "case_file_type"],
                criminal, history, civil,
            ])
            await db.flush()
            # 新系统里已上传到民事目录名下的刑事历史文件：保持原分类显示。
            db.add(FileAttachment(record_id=history.id, category="起诉材料及证据", original_name=f"{PREFIX}历史.pdf",
                                  stored_name=f"{PREFIX}history.pdf", path="/nonexistent", uploader=IDENTITY["username"]))
            await db.commit()
            self.ids = {"criminal": criminal.id, "history": history.id, "civil": civil.id}
        app.dependency_overrides[get_db] = self._override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row17.test")
        self.uploaded_paths: list[Path] = []

    def _case(self, serial_no, case_type):
        return BusinessRecord(
            module="case", serial_no=serial_no, title=f"{serial_no} 文档", customer=f"{PREFIX}客户", status="文书准备",
            owner=IDENTITY["username"], department=IDENTITY["department"],
            data={"case_type": case_type, "case_creation_step": "completed", "case_creation_approval_status": "已通过",
                  "handling_lawyer_usernames": [IDENTITY["username"]], "case_team_usernames": [IDENTITY["username"]]},
        )

    async def _override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        for path in self.uploaded_paths:
            path.unlink(missing_ok=True)
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _folders(self, key):
        response = await self.client.get(f"{API}/cases/{self.ids[key]}/document-folders")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_criminal_tree_uses_legacy_criminal_folders(self):
        payload = await self._folders("criminal")
        tree = {node["value"]: node for node in payload["tree"]}
        group = tree["案件文档全部"]
        self.assertEqual(group["label"], "诉讼阶段文件")
        self.assertEqual([item["value"] for item in group["options"]], CRIMINAL_STAGE)
        self.assertIn("公安机关文件", tree)
        self.assertIn("检察机关文件", tree)
        for name in CIVIL_STAGE:
            self.assertNotIn(name, payload["folders"])
        for name in [*CRIMINAL_STAGE, "公安机关文件", "检察机关文件"]:
            self.assertIn(name, payload["folders"])

    async def test_criminal_history_civil_folder_stays_visible_but_not_a_target(self):
        payload = await self._folders("history")
        group = next(node for node in payload["tree"] if node["value"] == "案件文档全部")
        historical = next(item for item in group["options"] if item["value"] == "起诉材料及证据")
        self.assertTrue(historical["disabled"])
        async with self.sessions() as db:
            attachment = await db.scalar(select(FileAttachment).where(FileAttachment.record_id == self.ids["history"]))
            self.assertEqual(attachment.category, "起诉材料及证据")

    async def test_civil_tree_unchanged(self):
        payload = await self._folders("civil")
        group = next(node for node in payload["tree"] if node["value"] == "案件文档全部")
        self.assertEqual(group["label"], "案件文档")
        self.assertEqual([item["value"] for item in group["options"]], CIVIL_STAGE)
        self.assertNotIn("公安机关文件", [node["value"] for node in payload["tree"]])

    async def _upload(self, key, category):
        response = await self.client.post(
            f"{API}/attachments", data={"record_id": str(self.ids[key]), "category": category},
            files={"file": (f"{PREFIX}upload.txt", b"row17", "text/plain")},
        )
        if response.status_code == 201:
            async with self.sessions() as db:
                for item in (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == self.ids[key]))).all():
                    self.uploaded_paths.append(Path(item.path))
        return response

    async def test_upload_validation_by_case_type(self):
        self.assertEqual((await self._upload("criminal", "公安机关文件")).status_code, 201)
        self.assertEqual((await self._upload("criminal", "委托手续及证明")).status_code, 201)
        response = await self._upload("criminal", "主体及委托资料")
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self._upload("civil", "公安机关文件")).status_code, 422)
        self.assertEqual((await self._upload("civil", "主体及委托资料")).status_code, 201)

    async def test_move_and_promote_validation_by_case_type(self):
        async with self.sessions() as db:
            criminal = await db.get(BusinessRecord, self.ids["criminal"])
            civil = await db.get(BusinessRecord, self.ids["civil"])
            for validate in (_validate_case_attachment_move_category, _validate_case_formal_document_category):
                self.assertEqual(await validate(criminal, "检察机关文件", db), "检察机关文件")
                with self.assertRaises(HTTPException) as caught:
                    await validate(criminal, "庭审及庭后文件", db)
                self.assertEqual(caught.exception.status_code, 422)
                self.assertEqual(await validate(civil, "庭审及庭后文件", db), "庭审及庭后文件")
                with self.assertRaises(HTTPException):
                    await validate(civil, "检察机关文件", db)

    def test_generated_document_placement_by_case_type(self):
        self.assertEqual(case_document_category_for("authorization-letter", "刑事案件"), "委托手续及证明")
        self.assertEqual(case_document_category_for("execution-lawyer-letter", "刑事案件"), "委托手续及证明")
        self.assertEqual(case_document_category_for("settlement-list", "刑事案件"), "法院裁判文书")
        self.assertEqual(case_document_category_for("authorization-letter", "民事争议"), "主体及委托资料")
        self.assertEqual(case_document_category_for("unknown-type", "刑事案件"), "案件生成文书")


if __name__ == "__main__":
    unittest.main()

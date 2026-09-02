import importlib
import tempfile
import unittest
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity


main_module = importlib.import_module("app.main")
ORDINARY = {
    "username": "CODEX-901-R37-user",
    "display_name": "第37行经办人",
    "role": "user",
    "department": "上海分所",
}
ADMIN = {
    "username": "CODEX-901-R37-admin",
    "display_name": "第37行管理员",
    "role": "admin",
    "role_ids": ["admin"],
    "department": "上海分所",
}
API = settings.api_prefix


class CaseDocumentOperationsRow37Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="codex-901-row37-")
        self.upload_root = Path(self.temp_dir.name)
        self.previous_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = self.upload_root
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case",
                serial_no="CODEX-901-R37-CASE",
                title="第37行案件文档验收",
                customer="第37行客户",
                status="文书准备",
                owner=ORDINARY["username"],
                department=ORDINARY["department"],
                data={"case_type": "民事案件", "case_team_usernames": [ORDINARY["username"]]},
            )
            db.add(case)
            db.add_all([
                User(
                    username=ORDINARY["username"], display_name=ORDINARY["display_name"],
                    department=ORDINARY["department"], role="user", role_ids=["user"], password_hash="test-only",
                ),
                User(
                    username=ADMIN["username"], display_name=ADMIN["display_name"],
                    department=ADMIN["department"], role="admin", role_ids=["admin"], password_hash="test-only",
                ),
            ])
            await db.flush()
            self.case_id = case.id
            own_path = self.upload_root / "row37-own.txt"
            foreign_path = self.upload_root / "row37-foreign.txt"
            own_path.write_text("own", encoding="utf-8")
            foreign_path.write_text("foreign", encoding="utf-8")
            own = FileAttachment(
                record_id=case.id,
                category="案件文件",
                original_name=own_path.name,
                stored_name=own_path.name,
                content_type="text/plain",
                size=own_path.stat().st_size,
                path=str(own_path),
                uploader=ORDINARY["username"],
                remark="第37行本人文件",
            )
            foreign = FileAttachment(
                record_id=case.id,
                category="案件文件",
                original_name=foreign_path.name,
                stored_name=foreign_path.name,
                content_type="text/plain",
                size=foreign_path.stat().st_size,
                path=str(foreign_path),
                uploader="CODEX-901-R37-foreign",
                remark="第37行他人文件",
            )
            db.add_all([own, foreign])
            await db.commit()
            self.own_id = own.id
            self.foreign_id = foreign.id
            self.foreign_path = foreign_path

        self.identity = ORDINARY

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row37.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        main_module.UPLOAD_ROOT = self.previous_upload_root
        await self.engine.dispose()
        self.temp_dir.cleanup()

    async def test_ordinary_user_cannot_delete_foreign_upload_and_batch_is_atomic(self) -> None:
        response = await self.client.post(
            f"{API}/cases/attachments/delete",
            json={"attachment_ids": [self.own_id, self.foreign_id]},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIn("只能删除本人上传的文件", response.json()["detail"])
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(FileAttachment, self.own_id))
            self.assertIsNotNone(await db.get(FileAttachment, self.foreign_id))

    async def test_administrator_override_deletes_foreign_upload_and_writes_audit(self) -> None:
        self.identity = ADMIN
        response = await self.client.post(
            f"{API}/cases/attachments/delete",
            json={"attachment_ids": [self.foreign_id]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"deleted": 1})
        async with self.sessions() as db:
            self.assertIsNone(await db.get(FileAttachment, self.foreign_id))
            audit_count = await db.scalar(
                select(func.count()).select_from(WorkflowEvent).where(
                    WorkflowEvent.record_id == self.case_id,
                    WorkflowEvent.action == "批量删除案件文件",
                    WorkflowEvent.operator == ADMIN["username"],
                )
            )
        self.assertEqual(audit_count, 1)
        self.assertFalse(self.foreign_path.exists())

    async def test_generation_returns_persisted_downloadable_attachment_visible_after_refresh(self) -> None:
        self.identity = ADMIN
        generated = await self.client.post(f"{API}/cases/{self.case_id}/documents/archive-cover")
        self.assertEqual(generated.status_code, 201, generated.text)
        item = generated.json()
        self.assertEqual(item["record_id"], self.case_id)
        self.assertEqual(item["uploader"], ADMIN["username"])
        self.assertGreater(item["size"], 1000)
        async with self.sessions() as db:
            persisted = await db.get(FileAttachment, item["id"])
            self.assertIsNotNone(persisted)
            self.assertTrue(Path(persisted.path).is_file())
            self.assertEqual(Path(persisted.path).stat().st_size, item["size"])
        downloaded = await self.client.get(f"{API}/attachments/{item['id']}/download")
        self.assertEqual(downloaded.status_code, 200, downloaded.text)
        self.assertEqual(len(downloaded.content), item["size"])
        refreshed = await self.client.get(f"{API}/attachments", params={"record_id": self.case_id})
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        refreshed_item = next(row for row in refreshed.json()["items"] if row["id"] == item["id"])
        self.assertEqual(refreshed_item["original_name"], item["original_name"])


if __name__ == "__main__":
    unittest.main()

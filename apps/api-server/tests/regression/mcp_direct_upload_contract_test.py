"""MCP 直接上传附件的 multipart、权限入口和后续 files 参数契约。"""

import tempfile
import unittest
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_mcp.catalog import get_catalog
from app.areas.system import attachments as attachments_module
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import FileAttachment
from app.security import current_identity


class McpDirectUploadContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {"username": "codex-mcp-upload", "role": "admin", "display_name": "MCP上传测试", "department": "测试"}

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.upload_dir = tempfile.TemporaryDirectory()
        self.previous_upload_root = attachments_module.UPLOAD_ROOT
        attachments_module.UPLOAD_ROOT = Path(self.upload_dir.name)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://mcp-upload.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        attachments_module.UPLOAD_ROOT = self.previous_upload_root
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        self.upload_dir.cleanup()
        await self.engine.dispose()

    async def test_real_multipart_returns_id_for_mcp_files_group(self):
        response = await self.client.post(
            f"{settings.api_prefix}/agent-tools/upload",
            files={"file": ("CODEX-mcp-upload.txt", "真实 multipart 内容".encode(), "text/plain")},
            data={"category": "个人智能体材料", "remark": "MCP直接上传契约"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        attachment_id = payload["attachment_id"]
        self.assertIsInstance(attachment_id, int)
        self.assertEqual(payload["next_mcp_files_argument"], {"files": {"file": attachment_id}})
        async with self.sessions() as db:
            item = await db.get(FileAttachment, attachment_id)
            self.assertIsNotNone(item)
            self.assertEqual(Path(item.path).read_bytes(), "真实 multipart 内容".encode())

        spec = next(item for item in get_catalog(app).tools if item.name == "oa_upload_attachment_post")
        params = spec.validate_arguments({"files": {"file": attachment_id}})
        self.assertEqual(params["files"], {"file": attachment_id})

    async def test_json_path_is_rejected_as_file(self):
        response = await self.client.post(
            f"{settings.api_prefix}/agent-tools/upload", json={"file": "/tmp/CODEX-fake.txt"},
        )
        self.assertEqual(response.status_code, 422, response.text)

    async def test_business_relation_fields_are_rejected_before_storage(self):
        response = await self.client.post(
            f"{settings.api_prefix}/agent-tools/upload",
            files={"file": ("CODEX-related.txt", b"must not attach", "text/plain")},
            data={"record_id": "123"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(FileAttachment, 1))


if __name__ == "__main__":
    unittest.main()

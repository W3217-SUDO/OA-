import unittest
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, SystemParameter
from app.security import current_identity


IDENTITY = {
    "username": "CODEX-812-ROW22-admin",
    "display_name": "第22行验收管理员",
    "role": "admin",
    "department": "上海分所",
}


class CaseDocumentUploadRow22Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case",
                serial_no="CODEX-812-ROW22-CASE",
                title="第22行案件文档上传验收",
                customer="第22行客户",
                status="待立案审批",
                owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_type": "民事案件",
                    "case_creation_step": "completed",
                    "case_creation_approval_status": "待审批",
                },
            )
            db.add_all([
                case,
                SystemParameter(category="case_file_type", code="ROW22-EVIDENCE", name="起诉材料及证据", sort_order=1, is_active=True),
            ])
            await db.commit()
            await db.refresh(case)
            self.case_id = case.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://row22.test",
        )
        self.uploaded_paths: list[Path] = []

    async def asyncTearDown(self):
        for path in self.uploaded_paths:
            path.unlink(missing_ok=True)
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_pending_creation_case_can_upload_documents(self):
        capability_response = await self.client.get(
            f"{settings.api_prefix}/cases/{self.case_id}/action-capabilities"
        )
        self.assertEqual(capability_response.status_code, 200, capability_response.text)
        capabilities = capability_response.json()
        self.assertTrue(capabilities["can_write"])
        self.assertTrue(capabilities["can_upload_attachment"])

        upload_response = await self.client.post(
            f"{settings.api_prefix}/attachments",
            data={"record_id": str(self.case_id), "category": "起诉材料及证据"},
            files={"file": ("row22-evidence.txt", b"row22 evidence", "text/plain")},
        )
        self.assertEqual(upload_response.status_code, 201, upload_response.text)
        async with self.sessions() as db:
            attachment = await db.scalar(
                select(FileAttachment).where(FileAttachment.record_id == self.case_id)
            )
            self.assertIsNotNone(attachment)
            self.assertEqual(attachment.original_name, "row22-evidence.txt")
            self.uploaded_paths.append(Path(attachment.path))


if __name__ == "__main__":
    unittest.main()

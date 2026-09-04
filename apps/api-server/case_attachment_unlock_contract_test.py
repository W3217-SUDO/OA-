import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity


IDENTITY = {"username": "CODEX-CIVIL-UNLOCK", "display_name": "解锁测试用户", "role": "user", "department": "测试部门"}


class CaseAttachmentUnlockContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="CODEX-CIVIL-UNLOCK-1", title="民事文件解锁", customer="测试客户", status="执行", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "民事案件"})
            other_case = BusinessRecord(module="case", serial_no="CODEX-CIVIL-UNLOCK-2", title="另一民事案件", customer="测试客户", status="执行", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "民事案件"})
            db.add_all([
                case,
                other_case,
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="user", role_ids=["user"], password_hash="test-only"),
                User(username="unauthorized-user", display_name="无权测试用户", department="其他部门", role="user", role_ids=["user"], password_hash="test-only"),
            ])
            await db.flush()
            locked = FileAttachment(record_id=case.id, category="案件文档", original_name="locked.pdf", stored_name="locked.pdf", content_type="application/pdf", size=1, path="unused", uploader=IDENTITY["username"], is_locked=True, locked_by="locker")
            unlocked = FileAttachment(record_id=case.id, category="案件文档", original_name="unlocked.pdf", stored_name="unlocked.pdf", content_type="application/pdf", size=1, path="unused", uploader=IDENTITY["username"], is_locked=False)
            other = FileAttachment(record_id=other_case.id, category="案件文档", original_name="other.pdf", stored_name="other.pdf", content_type="application/pdf", size=1, path="unused", uploader=IDENTITY["username"], is_locked=True)
            db.add_all([locked, unlocked, other])
            await db.commit()
            self.case_id, self.locked_id, self.unlocked_id, self.other_id = case.id, locked.id, unlocked.id, other.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://civil-unlock.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_unlock_clears_lock_and_writes_audit(self):
        response = await self.client.post(f"{settings.api_prefix}/cases/{self.case_id}/attachments/{self.locked_id}/unlock")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_locked"])
        async with self.sessions() as db:
            attachment = await db.get(FileAttachment, self.locked_id)
            self.assertFalse(attachment.is_locked)
            self.assertIsNone(attachment.locked_at)
            self.assertEqual(attachment.locked_by, "")
            audit_count = await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id, WorkflowEvent.action == "解锁民事案件文件"))
            self.assertEqual(audit_count, 1)

    async def test_rejects_unlocked_cross_case_and_invisible_case(self):
        unlocked = await self.client.post(f"{settings.api_prefix}/cases/{self.case_id}/attachments/{self.unlocked_id}/unlock")
        self.assertEqual(unlocked.status_code, 409, unlocked.text)
        cross_case = await self.client.post(f"{settings.api_prefix}/cases/{self.case_id}/attachments/{self.other_id}/unlock")
        self.assertEqual(cross_case.status_code, 404, cross_case.text)
        app.dependency_overrides[current_identity] = lambda: {**IDENTITY, "username": "unauthorized-user", "department": "其他部门"}
        invisible = await self.client.post(f"{settings.api_prefix}/cases/{self.case_id}/attachments/{self.locked_id}/unlock")
        self.assertIn(invisible.status_code, {403, 404}, invisible.text)


if __name__ == "__main__":
    unittest.main()

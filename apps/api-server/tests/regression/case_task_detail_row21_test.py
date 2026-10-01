"""8.28 row 21: published case tasks start immediately and retain full detail history."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row21-admin", "role": "admin", "display_name": "第21行管理员", "department": "诉讼部"}


class CaseTaskDetailRow21Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(
                module="case", serial_no="CODEX-828-R21-CASE", title="第21行案件", customer="第21行客户",
                status="文书准备", owner=ADMIN["username"], department=ADMIN["department"],
                data={"case_type": "民事案件", "case_creation_step": "completed", "handling_lawyer_usernames": [ADMIN["username"]]},
            )
            db.add(case)
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row21.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_case_task_starts_immediately_and_supports_feedback_and_withdrawal(self) -> None:
        start_at = datetime.now().replace(microsecond=0)
        end_at = start_at + timedelta(days=7)
        created = await self.client.post(f"{API}/tasks", json={
            "title": "第21行案件任务", "customer": "ignored", "owner": ADMIN["username"],
            "collaborators": [], "case_no": "CODEX-828-R21-CASE",
            "start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
            "deadline": str(end_at.date()), "priority": "普通", "source": "案件任务", "description": "详情验收",
        })
        self.assertEqual(created.status_code, 201, created.text)
        task = created.json()
        self.assertEqual(task["status"], "待处理")
        self.assertEqual(task["workflow_status"], "待处理")
        self.assertEqual(task["start_at"], start_at.isoformat())

        history = await self.client.get(f"{API}/tasks/{task['id']}/history")
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["items"][0]["to_status"], "待处理")

        accepted = await self.client.post(f"{API}/tasks/{task['id']}/accept", json={"comment": "负责人接受任务"})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["workflow_status"], "处理中")

        feedback = await self.client.post(
            f"{API}/tasks/{task['id']}/feedback",
            data={"comment": "第21行过程留言"},
            files={"files": ("row21.txt", b"row21 attachment", "text/plain")},
        )
        self.assertEqual(feedback.status_code, 201, feedback.text)
        self.assertEqual(feedback.json()["attachments"][0]["category"], "任务反馈附件")

        withdrawn = await self.client.post(f"{API}/tasks/{task['id']}/withdraw", json={"comment": "第21行撤回"})
        self.assertEqual(withdrawn.status_code, 200, withdrawn.text)
        self.assertEqual(withdrawn.json()["status"], "已撤回")

        async with self.sessions() as db:
            stored = await db.get(BusinessRecord, task["id"])
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == task["id"]).order_by(WorkflowEvent.id))).all())
            attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == task["id"]))).all())
        self.assertEqual(stored.status, "已撤回")
        self.assertEqual([event.action for event in events], ["发起任务", "接收任务", "任务沟通", "上传任务反馈附件", "撤回任务"])
        self.assertEqual(len(attachments), 1)
        Path(attachments[0].path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

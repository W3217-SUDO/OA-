"""Ordinary case-event CRUD, reminder projection and permission contract."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, CaseEvent, JobRole, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "case-event-admin", "role": "admin", "display_name": "事件管理员", "department": "诉讼部"}
VIEWER = {"username": "case-event-viewer", "role": "user", "display_name": "事件查看人", "department": "诉讼部"}


class CaseEventContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = ADMIN
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=VIEWER["username"], display_name=VIEWER["display_name"], department=VIEWER["department"], role="user", password_hash="x", is_active=True, profile={"permission_role_code": "CASE-EVENT-VIEWER"}),
                JobRole(code="CASE-EVENT-VIEWER", name="案件事件只读岗", permissions=["case-mine"], data_scope="全所数据", is_active=True),
            ])
            case = BusinessRecord(
                module="case", serial_no="CODEX-CASE-EVENT-001", title="案件事件验收",
                customer="CODEX 客户", status="在办", owner=ADMIN["username"], department=ADMIN["department"],
                data={"case_team_usernames": [ADMIN["username"]], "case_creation_step": "completed"},
            )
            archived = BusinessRecord(
                module="case", serial_no="CODEX-CASE-EVENT-ARCHIVED", title="归档案件事件验收",
                customer="CODEX 客户", status="已归档", owner=ADMIN["username"], department=ADMIN["department"], data={},
            )
            other_case = BusinessRecord(
                module="case", serial_no="CODEX-CASE-EVENT-002", title="跨案事件验收",
                customer="CODEX 客户", status="在办", owner=ADMIN["username"], department=ADMIN["department"],
                data={"case_team_usernames": [ADMIN["username"]]},
            )
            smoke_case = BusinessRecord(
                module="case", serial_no="SMOKE-CASE-EVENT-CLEANUP", title="SMOKE 案件事件清理验收",
                customer="SMOKE 客户", status="在办", owner=ADMIN["username"], department=ADMIN["department"],
                data={"case_team_usernames": [ADMIN["username"]]},
            )
            db.add_all([case, archived, other_case, smoke_case])
            await db.flush()
            self.case_id, self.archived_case_id, self.other_case_id, self.smoke_case_id = case.id, archived.id, other_case.id, smoke_case.id
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-event.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    @staticmethod
    def payload(**overrides) -> dict:
        today = date.today()
        body = {
            "event_type": "举证期限", "event_time": f"{today.isoformat()}T23:55:00+08:00",
            "content": "CODEX-案件事件材料提交", "deadline": str(today + timedelta(days=2)),
            "reminder_enabled": True, "remind_at": f"{today + timedelta(days=1)}T00:05:00+08:00",
        }
        body.update(overrides)
        return body

    async def test_crud_preserves_datetime_projects_reminder_and_audits(self) -> None:
        for invalid in ({"event_type": None}, {"event_type": "   "}):
            rejected = await self.client.post(f"{API}/cases/{self.case_id}/events", json=self.payload(**invalid))
            self.assertEqual(rejected.status_code, 422, rejected.text)
        created = await self.client.post(f"{API}/cases/{self.case_id}/events", json=self.payload())
        self.assertEqual(created.status_code, 201, created.text)
        event = created.json()
        shanghai = ZoneInfo("Asia/Shanghai")
        self.assertEqual(datetime.fromisoformat(event["event_time"]).astimezone(shanghai).strftime("%Y-%m-%d %H:%M"), f"{date.today()} 23:55")
        self.assertEqual(datetime.fromisoformat(event["remind_at"]).astimezone(shanghai).strftime("%Y-%m-%d %H:%M"), f"{date.today() + timedelta(days=1)} 00:05")
        self.assertEqual(event["status"], "待处理")

        listed = await self.client.get(f"{API}/cases/{self.case_id}/events")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["total"], 1)
        self.assertTrue(listed.json()["capabilities"]["can_create"])

        updated = await self.client.patch(
            f"{API}/cases/{self.case_id}/events/{event['id']}",
            json={"status": "已完成", "reminder_enabled": False, "content": "CODEX-案件事件已完成"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["status"], "已完成")
        self.assertFalse(updated.json()["reminder_enabled"])

        second = await self.client.post(
            f"{API}/cases/{self.case_id}/events",
            json=self.payload(event_type="答辩期限", content="CODEX-答辩材料", event_time=f"{date.today() + timedelta(days=1)}T11:25:00+08:00", reminder_enabled=False, remind_at=None),
        )
        self.assertEqual(second.status_code, 201, second.text)
        other = await self.client.post(f"{API}/cases/{self.other_case_id}/events", json=self.payload(content="CODEX-跨案事件", reminder_enabled=False, remind_at=None))
        self.assertEqual(other.status_code, 201, other.text)
        mixed = await self.client.request("DELETE", f"{API}/cases/{self.case_id}/events", json={"event_ids": [event["id"], other.json()["id"]]})
        self.assertEqual(mixed.status_code, 404, mixed.text)
        self.assertEqual((await self.client.get(f"{API}/cases/{self.case_id}/events")).json()["total"], 2)
        self.assertEqual((await self.client.get(f"{API}/cases/{self.other_case_id}/events")).json()["total"], 1)
        deleted = await self.client.request("DELETE", f"{API}/cases/{self.case_id}/events", json={"event_ids": [event["id"], second.json()["id"]]})
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["deleted"], 2)
        deleted_other = await self.client.delete(f"{API}/cases/{self.other_case_id}/events/{other.json()['id']}")
        self.assertEqual(deleted_other.status_code, 204, deleted_other.text)

        cleanup_event = await self.client.post(f"{API}/cases/{self.smoke_case_id}/events", json=self.payload(content="SMOKE-案件删除清理", reminder_enabled=True))
        self.assertEqual(cleanup_event.status_code, 201, cleanup_event.text)
        cleanup = await self.client.delete(f"{API}/testing/cases/{self.smoke_case_id}")
        self.assertEqual(cleanup.status_code, 204, cleanup.text)

        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(CaseEvent)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "case_reminder")), 0)
            self.assertIsNone(await db.get(BusinessRecord, self.smoke_case_id))
            actions = set((await db.scalars(select(WorkflowEvent.action).where(WorkflowEvent.record_id == self.case_id))).all())
            self.assertTrue({"新增案件事件", "修改案件事件", "批量删除案件事件"}.issubset(actions))

    async def test_permissions_and_archived_case_are_blocked(self) -> None:
        self.identity = VIEWER
        denied = await self.client.post(f"{API}/cases/{self.case_id}/events", json=self.payload())
        self.assertEqual(denied.status_code, 403, denied.text)
        self.identity = ADMIN
        archived = await self.client.post(f"{API}/cases/{self.archived_case_id}/events", json=self.payload())
        self.assertEqual(archived.status_code, 409, archived.text)


if __name__ == "__main__":
    unittest.main()

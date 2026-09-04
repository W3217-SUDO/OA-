"""Isolated API contracts for IPR warning rules, materialization and inbox sync."""
import unittest
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IprCaseWarning, Notification, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "codex-ipr-warning-admin", "role": "admin", "display_name": "CODEX IPR Warning", "department": "测试部"}


class IprWarningContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="test", is_active=True))
            self.case = BusinessRecord(module="ipr_case", serial_no="CODEX-IPR-WARNING-001", title="预警隔离案件", status="在办", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_kind": "专利", "case_type": "发明", "case_phase": "申请", "deadline": str(date.today() - timedelta(days=1))})
            db.add(self.case); await db.commit(); self.case_id = self.case.id
        async def override_db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr-warning.test")

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()

    async def test_rule_warning_notification_lifecycle_is_idempotent(self):
        blank = await self.client.post(f"{API}/ipr/warning-rules", json={"name": "  "})
        self.assertEqual(blank.status_code, 422, blank.text)
        invalid_null = await self.client.patch(f"{API}/ipr/warning-rules/999", json={"days_before": None})
        self.assertEqual(invalid_null.status_code, 422, invalid_null.text)
        created = await self.client.post(f"{API}/ipr/warning-rules", json={"name": "CODEX 逾期期限", "case_kind": "专利", "time_node": "case_deadline", "days_before": 0})
        self.assertEqual(created.status_code, 201, created.text); rule_id = created.json()["id"]
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/generate")).json()["created"], 1)
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/generate")).json()["created"], 0)
        listed = await self.client.get(f"{API}/ipr/warnings", params={"status": "未读"})
        self.assertEqual(listed.status_code, 200, listed.text); self.assertEqual(listed.json()["total"], 1)
        warning_id = listed.json()["items"][0]["id"]
        async with self.sessions() as db:
            warning = await db.get(IprCaseWarning, warning_id); notice = await db.get(Notification, warning.notification_id)
            self.assertEqual(notice.source_type, "ipr_warning"); self.assertEqual(notice.source_id, self.case_id); self.assertFalse(notice.is_read)
            notification_id = notice.id
        self.assertEqual((await self.client.post(f"{API}/notifications/{notification_id}/read")).status_code, 200)
        async with self.sessions() as db:
            self.assertEqual((await db.get(IprCaseWarning, warning_id)).status, "已读")
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/{warning_id}/read")).status_code, 200)
        async with self.sessions() as db:
            warning = await db.get(IprCaseWarning, warning_id); notice = await db.get(Notification, warning.notification_id)
            self.assertEqual(warning.status, "已读"); self.assertTrue(notice.is_read)
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/{warning_id}/process", json={"comment": "CODEX handled"})).status_code, 200)
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/{warning_id}/process", json={"comment": "must not overwrite"})).status_code, 200)
        async with self.sessions() as db:
            warning = await db.get(IprCaseWarning, warning_id); events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id, WorkflowEvent.action == "处理知识产权案件预警"))).all())
            self.assertEqual(warning.status, "已处理"); self.assertEqual(warning.process_comment, "CODEX handled"); self.assertEqual(len(events), 1)
        self.assertEqual((await self.client.delete(f"{API}/ipr/warning-rules/{rule_id}")).status_code, 204)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(IprCaseWarning, warning_id))
            self.assertEqual(len(list((await db.scalars(select(Notification).where(Notification.source_type == "ipr_warning"))).all())), 0)

    async def test_inactive_rule_and_terminal_case_do_not_materialize(self):
        inactive = await self.client.post(f"{API}/ipr/warning-rules", json={"name": "CODEX 停用规则", "case_kind": "专利", "is_active": False})
        self.assertEqual(inactive.status_code, 201, inactive.text)
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/generate")).json()["created"], 0)
        active = await self.client.post(f"{API}/ipr/warning-rules", json={"name": "CODEX 终态规则", "case_kind": "专利", "is_active": True})
        self.assertEqual(active.status_code, 201, active.text)
        async with self.sessions() as db:
            row = await db.get(BusinessRecord, self.case_id); row.status = "已结案"; await db.commit()
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/generate")).json()["created"], 0)

    async def test_unrelated_user_cannot_write_rules_or_handle_warning(self):
        rule = await self.client.post(f"{API}/ipr/warning-rules", json={"name": "CODEX 权限规则", "case_kind": "专利"})
        self.assertEqual(rule.status_code, 201, rule.text)
        await self.client.post(f"{API}/ipr/warnings/generate")
        warning_id = (await self.client.get(f"{API}/ipr/warnings")).json()["items"][0]["id"]
        other = {"username": "codex-ipr-warning-other", "role": "user", "display_name": "Other", "department": "其他部"}
        async with self.sessions() as db:
            db.add(User(username=other["username"], display_name=other["display_name"], department=other["department"], role="user", password_hash="test", is_active=True)); await db.commit()
        app.dependency_overrides[current_identity] = lambda: other
        self.assertEqual((await self.client.post(f"{API}/ipr/warning-rules", json={"name": "denied"})).status_code, 403)
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/{warning_id}/read")).status_code, 404)
        self.assertEqual((await self.client.post(f"{API}/ipr/warnings/{warning_id}/process", json={})).status_code, 404)

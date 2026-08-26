"""Court-info permission: direct persistence is independent from case approval."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
EDITOR = {"username": "court-editor", "role": "user", "display_name": "法院信息维护员", "department": "诉讼部"}
VIEWER = {"username": "court-viewer", "role": "user", "display_name": "法院信息查看员", "department": "诉讼部"}
ADMIN = {"username": "court-admin", "role": "admin", "display_name": "Court Admin", "department": "诉讼部"}


class CaseCourtInfoPermissionContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = EDITOR
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=EDITOR["username"], display_name=EDITOR["display_name"], department=EDITOR["department"], role="user", password_hash="x", is_active=True, profile={"permission_role_code": "COURT-EDITOR"}),
                User(username=VIEWER["username"], display_name=VIEWER["display_name"], department=VIEWER["department"], role="user", password_hash="x", is_active=True, profile={"permission_role_code": "COURT-VIEWER"}),
                JobRole(code="COURT-EDITOR", name="法院信息维护岗", permissions=["case-mine", "案件法院信息修改"], data_scope="全所数据", is_active=True),
                JobRole(code="COURT-VIEWER", name="法院信息查看岗", permissions=["case-mine"], data_scope="全所数据", is_active=True),
                BusinessRecord(
                    module="case", serial_no="CODEX-824-COURT-001", title="待审批法院信息案件", customer="测试客户",
                    status="一审准备开庭", owner="another-owner", department="诉讼部",
                    data={
                        "case_type": "民事案件", "case_creation_step": "completed",
                        "case_creation_approval_status": "待审批", "first_instance_court": "原一审法院",
                        "case_team_usernames": ["another-owner"],
                    },
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-824-COURT-ARCHIVED", title="归档法院信息案件", customer="测试客户",
                    status="已归档", owner="another-owner", department="诉讼部",
                    data={"case_type": "民事案件", "case_creation_approval_status": "待审批"},
                ),
            ])
            await db.flush()
            self.case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-824-COURT-001"))
            self.archived_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-824-COURT-ARCHIVED"))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://court-info.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    @staticmethod
    def payload() -> dict:
        return {
            "first_instance_court": "CODEX-824-一审法院",
            "first_instance_case_no": "(2026)沪01民初824号",
            "first_court_courtroom": "第一法庭",
            "second_court_name": "CODEX-824-二审法院",
            "second_court_case_no": "(2026)沪高民终824号",
            "execution_court_name": "CODEX-824-执行法院",
            "execution_court_case_no": "(2026)沪01执824号",
            "retrial_court_name": "CODEX-824-再审法院",
            "retrial_court_case_no": "(2026)沪再824号",
            "first_court_hearing_date": f"{date.today() + timedelta(days=3)} 09:45:00",
            "comment": "CODEX-824-直接修改法院信息",
        }

    async def test_authorized_user_sees_capability_and_saves_all_levels_without_approval_or_progress(self) -> None:
        capability = await self.client.get(f"{API}/cases/{self.case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertTrue(capability.json()["can_edit_court_info"])
        self.assertFalse(capability.json()["can_update_progress"])

        saved = await self.client.put(f"{API}/cases/{self.case_id}/court-info", json=self.payload())
        self.assertEqual(saved.status_code, 200, saved.text)
        body = saved.json()
        self.assertEqual(body["status"], "一审准备开庭")
        self.assertEqual(body["data"]["case_creation_approval_status"], "待审批")
        for key, value in self.payload().items():
            if key != "comment":
                self.assertEqual(body["data"][key], value)
        self.assertEqual(body["data"]["first_court_name"], self.payload()["first_instance_court"])
        self.assertEqual(body["data"]["second_instance_court"], self.payload()["second_court_name"])

        dashboard = await self.client.get(f"{API}/dashboard")
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        matching = [item for item in dashboard.json()["hearings"] if item["case_no"] == "CODEX-824-COURT-001"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["date"], str(date.today() + timedelta(days=3)))
        self.assertEqual(matching[0]["time"], "09:45")
        self.assertEqual(matching[0]["court"], "CODEX-824-一审法院")

        async with self.sessions() as db:
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))
            self.assertEqual(event.action, "修改法院信息")
            self.assertEqual(event.from_status, "一审准备开庭")
            self.assertEqual(event.to_status, "一审准备开庭")
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module.in_(["task", "reminder"]))), 0)

    async def test_denied_user_cannot_see_capability_or_bypass_endpoint(self) -> None:
        self.identity = VIEWER
        capability = await self.client.get(f"{API}/cases/{self.case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertFalse(capability.json()["can_edit_court_info"])
        denied = await self.client.put(f"{API}/cases/{self.case_id}/court-info", json=self.payload())
        self.assertEqual(denied.status_code, 403, denied.text)
        self.assertIn("案件操作", denied.text)

    async def test_archived_case_is_blocked_and_admin_keeps_the_capability(self) -> None:
        self.identity = ADMIN
        capability = await self.client.get(f"{API}/cases/{self.case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertTrue(capability.json()["can_edit_court_info"])
        archived = await self.client.put(f"{API}/cases/{self.archived_case_id}/court-info", json=self.payload())
        self.assertEqual(archived.status_code, 409, archived.text)
        self.assertIn("归档", archived.text)


if __name__ == "__main__":
    unittest.main()

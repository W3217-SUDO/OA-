"""8.13 row 4: basic information and phase changes are not approval-gated."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row4-admin", "role": "admin", "display_name": "Row4 Admin", "department": "诉讼部"}
VIEWER = {"username": "row4-viewer", "role": "user", "display_name": "Row4 Viewer", "department": "其他部门"}


class CaseBasicPhaseApprovalIndependenceRow4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = ADMIN
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
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True, profile={"position": "律师"}),
                User(username=VIEWER["username"], display_name=VIEWER["display_name"], department=VIEWER["department"], role="user", password_hash="x", is_active=True),
                BusinessRecord(module="customer", serial_no="ROW4-CUSTOMER", title="第4行客户", customer="", status="正常", owner=ADMIN["username"], department=ADMIN["department"], data={}),
                BusinessRecord(module="case", serial_no="ROW4-PENDING", title="第4行待审批案件", customer="第4行客户", status="一审准备开庭", owner=ADMIN["username"], department=ADMIN["department"], data=self._case_data()),
                BusinessRecord(module="case", serial_no="ROW4-ARCHIVED", title="第4行归档案件", customer="第4行客户", status="已归档", owner=ADMIN["username"], department=ADMIN["department"], data=self._case_data()),
                SystemParameter(category="case_phase", code="SECOND", name="二审", sort_order=1, is_active=True),
                SystemParameter(category="case_phase", code="EXECUTION", name="执行", sort_order=2, is_active=True),
            ])
            await db.flush()
            self.customer_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW4-CUSTOMER"))
            self.pending_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW4-PENDING"))
            self.archived_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "ROW4-ARCHIVED"))
            self.execution_phase_id = await db.scalar(select(SystemParameter.id).where(SystemParameter.code == "EXECUTION"))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row4.test")

    @staticmethod
    def _case_data() -> dict:
        return {
            "case_type": "民事案件",
            "case_creation_step": "completed",
            "case_creation_approval_status": "待审批",
            "handling_lawyers": [ADMIN["display_name"]],
            "handling_lawyer_usernames": [ADMIN["username"]],
            "case_team_usernames": [ADMIN["username"]],
            "cause_or_charge": "侵害商标权纠纷",
        }

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def _normal_payload(self) -> dict:
        return {
            "customer_record_id": self.customer_id,
            "title": "第4行待审批案件（已修改）",
            "case_phase": "二审",
            "cause_or_charge": "侵害商标权纠纷",
            "handling_lawyers": [ADMIN["username"]],
            "assistant": "",
            "business_owner": "",
            "investigator": "",
            "investigation_clue_ids": [],
            "right_type": "",
            "source_person": "",
            "comment": "row 4 pending approval basic edit",
        }

    async def test_pending_approval_allows_basic_and_phase_edits_but_archive_stays_locked(self) -> None:
        basic_response = await self.client.put(f"{API}/cases/{self.pending_id}/normal-basic", json=self._normal_payload())
        self.assertEqual(basic_response.status_code, 200, basic_response.text)
        self.assertEqual(basic_response.json()["status"], "二审")

        phase_response = await self.client.post(f"{API}/cases/phase-change", json={
            "case_nos": ["ROW4-PENDING"],
            "case_phase_id": self.execution_phase_id,
            "comment": "row 4 pending approval phase edit",
        })
        self.assertEqual(phase_response.status_code, 200, phase_response.text)
        self.assertEqual(phase_response.json()["items"][0]["status"], "执行")

        archived_response = await self.client.put(f"{API}/cases/{self.archived_id}/normal-basic", json=self._normal_payload())
        self.assertEqual(archived_response.status_code, 409, archived_response.text)
        self.assertIn("归档", archived_response.text)

    async def test_unrelated_user_cannot_bypass_case_visibility(self) -> None:
        self.identity = VIEWER
        response = await self.client.put(f"{API}/cases/{self.pending_id}/normal-basic", json=self._normal_payload())
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()

"""8.27 row 15: hearing-lawyer edits are independent from wizard markers."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
MANAGER = {
    "username": "row15-manager",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第15行案件负责人",
    "department": "诉讼部",
}
VIEWER = {
    "username": "row15-viewer",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第15行只读人员",
    "department": "诉讼部",
}
ADMIN = {
    "username": "row15-admin",
    "role": "admin",
    "role_ids": ["admin"],
    "display_name": "第15行系统管理员",
    "department": "管理部",
}


class CaseHearingLawyerCreationStepIndependenceRow15Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = MANAGER
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
                JobRole(
                    code="ROW15-MANAGER",
                    name="案件负责人",
                    permissions=["案件分配"],
                    data_scope="本人及共享数据",
                    is_active=True,
                ),
                User(
                    username=MANAGER["username"],
                    display_name=MANAGER["display_name"],
                    department=MANAGER["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={"position": "案件负责人", "permission_role": "案件负责人"},
                    is_active=True,
                ),
                User(
                    username=VIEWER["username"],
                    display_name=VIEWER["display_name"],
                    department=VIEWER["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={},
                    is_active=True,
                ),
                User(
                    username="row15-hearing-old",
                    display_name="第15行原开庭律师",
                    department="诉讼部",
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={},
                    is_active=True,
                ),
                User(
                    username="row15-hearing-new",
                    display_name="第15行新开庭律师",
                    department="调查取证部",
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={},
                    is_active=True,
                ),
                User(
                    username="row15-hearing-disabled",
                    display_name="第15行停用律师",
                    department="调查取证部",
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={},
                    is_active=False,
                ),
                self._case("CODEX-827-15-EDIT", MANAGER["username"], "文书准备"),
                self._case("CODEX-827-15-VIEWER", VIEWER["username"], "文书准备"),
                self._case("CODEX-827-15-HIDDEN", "unrelated-owner", "文书准备", department="其他部门"),
                self._case("CODEX-827-15-ARCHIVED", MANAGER["username"], "已归档"),
            ])
            await db.flush()
            self.edit_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-15-EDIT"))
            self.viewer_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-15-VIEWER"))
            self.hidden_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-15-HIDDEN"))
            self.archived_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-15-ARCHIVED"))
            await db.commit()

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row15.test")

    @staticmethod
    def _case(serial_no: str, owner: str, status: str, *, department: str = "诉讼部") -> BusinessRecord:
        return BusinessRecord(
            module="case",
            serial_no=serial_no,
            title=serial_no,
            customer="第15行客户",
            status=status,
            owner=owner,
            department=department,
            data={
                "case_type": "民事案件",
                "case_creation_step": "basic",
                "case_creation_approval_status": "",
                "hearing_lawyer": "第15行原开庭律师",
                "hearing_lawyer_username": "row15-hearing-old",
                "handling_lawyers": ["既有经办律师"],
                "handling_lawyer_usernames": ["existing-handler"],
                "assistant": "既有律师助理",
                "assistant_username": "existing-assistant",
                "case_team_usernames": ["existing-handler", "existing-assistant"],
            },
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_incomplete_case_can_update_only_hearing_lawyer_and_persist_audit(self) -> None:
        response = await self.client.put(
            f"{API}/cases/{self.edit_case_id}/hearing-lawyer",
            json={"hearing_lawyer": "row15-hearing-new", "comment": "第15行独立修改"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "文书准备")
        self.assertEqual(response.json()["data"]["case_creation_step"], "basic")
        self.assertEqual(response.json()["data"]["hearing_lawyer"], "第15行新开庭律师")
        self.assertEqual(response.json()["data"]["hearing_lawyer_username"], "row15-hearing-new")

        detail_response = await self.client.get(f"{API}/records/{self.edit_case_id}")
        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        self.assertEqual(detail_response.json()["data"]["hearing_lawyer"], "第15行新开庭律师")
        self.assertEqual(detail_response.json()["data"]["hearing_lawyer_display_name"], "第15行新开庭律师")

        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.edit_case_id)
            self.assertEqual(persisted.status, "文书准备")
            self.assertEqual(persisted.data["handling_lawyers"], ["既有经办律师"])
            self.assertEqual(persisted.data["assistant"], "既有律师助理")
            self.assertEqual(persisted.data["case_team_usernames"], ["existing-handler", "existing-assistant"])
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.edit_case_id))).all())
            self.assertEqual([event.action for event in events], ["修改开庭律师"])
            self.assertIn("第15行原开庭律师 → 第15行新开庭律师", events[0].comment)

    async def test_visible_non_manager_can_update_hearing_lawyer(self) -> None:
        self.identity = VIEWER
        capability = await self.client.get(f"{API}/cases/{self.viewer_case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertTrue(capability.json()["can_edit_hearing_lawyer"])
        response = await self.client.put(
            f"{API}/cases/{self.viewer_case_id}/hearing-lawyer",
            json={"hearing_lawyer": "row15-hearing-new"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["hearing_lawyer_username"], "row15-hearing-new")

    async def test_admin_can_update_any_visible_case_without_team_assignment_permission(self) -> None:
        self.identity = ADMIN
        capability = await self.client.get(f"{API}/cases/{self.edit_case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertTrue(capability.json()["can_edit_hearing_lawyer"])
        response = await self.client.put(
            f"{API}/cases/{self.edit_case_id}/hearing-lawyer",
            json={"hearing_lawyer": "row15-hearing-new", "comment": "管理员可见即修改"},
        )
        self.assertEqual(response.status_code, 200, response.text)

    async def test_non_visible_case_stays_inaccessible_without_writes(self) -> None:
        self.identity = VIEWER
        response = await self.client.put(
            f"{API}/cases/{self.hidden_case_id}/hearing-lawyer",
            json={"hearing_lawyer": "row15-hearing-new"},
        )
        self.assertEqual(response.status_code, 404, response.text)
        await self._assert_unchanged(self.hidden_case_id)

    async def test_disabled_person_is_rejected_without_writes(self) -> None:
        response = await self.client.put(
            f"{API}/cases/{self.edit_case_id}/hearing-lawyer",
            json={"hearing_lawyer": "row15-hearing-disabled"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        await self._assert_unchanged(self.edit_case_id)

    async def test_archive_lock_is_preserved_without_writes(self) -> None:
        response = await self.client.put(
            f"{API}/cases/{self.archived_case_id}/hearing-lawyer",
            json={"hearing_lawyer": "row15-hearing-new"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("归档", response.text)
        await self._assert_unchanged(self.archived_case_id)

    async def _assert_unchanged(self, case_id: int) -> None:
        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, case_id)
            self.assertEqual(persisted.data["hearing_lawyer"], "第15行原开庭律师")
            self.assertEqual(persisted.data["hearing_lawyer_username"], "row15-hearing-old")
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == case_id))
            self.assertIsNone(event)


if __name__ == "__main__":
    unittest.main()

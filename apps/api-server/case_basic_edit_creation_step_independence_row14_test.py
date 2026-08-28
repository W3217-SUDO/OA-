"""8.27 row 14: case-detail basic edits are independent from wizard markers."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
DOCUMENT_USER = {
    "username": "row14-document",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第14行文书",
    "department": "诉讼部",
}
NO_PERMISSION_USER = {
    "username": "row14-viewer",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第14行只读人员",
    "department": "诉讼部",
}


class CaseBasicEditCreationStepIndependenceRow14Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = DOCUMENT_USER
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
                    code="ROW14-DOCUMENT",
                    name="文书",
                    permissions=["案件承办"],
                    data_scope="本人及共享数据",
                    is_active=True,
                ),
                User(
                    username=DOCUMENT_USER["username"],
                    display_name=DOCUMENT_USER["display_name"],
                    department=DOCUMENT_USER["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={"position": "文书", "permission_role": "文书"},
                    is_active=True,
                ),
                User(
                    username=NO_PERMISSION_USER["username"],
                    display_name=NO_PERMISSION_USER["display_name"],
                    department=NO_PERMISSION_USER["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={},
                    is_active=True,
                ),
                BusinessRecord(
                    module="customer",
                    serial_no="CODEX-827-14-CUSTOMER",
                    title="第14行客户",
                    customer="",
                    status="正常",
                    owner=DOCUMENT_USER["username"],
                    department=DOCUMENT_USER["department"],
                    data={"shared_to": [NO_PERMISSION_USER["username"]]},
                ),
                BusinessRecord(
                    module="case",
                    serial_no="CODEX-827-14-DOCUMENT",
                    title="第14行文书案件",
                    customer="第14行客户",
                    status="文书准备",
                    owner=DOCUMENT_USER["username"],
                    department=DOCUMENT_USER["department"],
                    data=self._case_data(DOCUMENT_USER),
                ),
                BusinessRecord(
                    module="case",
                    serial_no="CODEX-827-14-NO-PERMISSION",
                    title="第14行无权限案件",
                    customer="第14行客户",
                    status="文书准备",
                    owner=NO_PERMISSION_USER["username"],
                    department=NO_PERMISSION_USER["department"],
                    data=self._case_data(NO_PERMISSION_USER),
                ),
                BusinessRecord(
                    module="case",
                    serial_no="CODEX-827-14-ARCHIVED",
                    title="第14行归档案件",
                    customer="第14行客户",
                    status="已归档",
                    owner=DOCUMENT_USER["username"],
                    department=DOCUMENT_USER["department"],
                    data=self._case_data(DOCUMENT_USER),
                ),
                SystemParameter(category="case_phase", code="DOCUMENT", name="文书准备", sort_order=1, is_active=True),
                SystemParameter(category="case_phase", code="FIRST", name="一审立案受理", sort_order=2, is_active=True),
            ])
            await db.flush()
            self.customer_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-14-CUSTOMER"))
            self.document_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-14-DOCUMENT"))
            self.no_permission_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-14-NO-PERMISSION"))
            self.archived_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-14-ARCHIVED"))
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row14.test")

    @staticmethod
    def _case_data(identity: dict) -> dict:
        return {
            "case_type": "民事案件",
            "case_creation_step": "basic",
            "case_creation_approval_status": "",
            "handling_lawyers": [identity["display_name"]],
            "handling_lawyer_usernames": [identity["username"]],
            "case_team_usernames": [identity["username"]],
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

    def _payload(self, title: str = "第14行文书案件（已修改）") -> dict:
        return {
            "customer_record_id": self.customer_id,
            "title": title,
            "case_phase": "一审立案受理",
            "cause_or_charge": "侵害商标权纠纷",
            "handling_lawyers": [DOCUMENT_USER["username"]],
            "assistant": "",
            "business_owner": "",
            "investigator": "",
            "investigation_clue_ids": [],
            "right_type": "",
            "source_person": "",
            "comment": "CODEX-827-14 文书修改案件基本信息",
        }

    async def test_document_role_can_edit_basic_with_legacy_basic_marker_and_persist(self) -> None:
        capability = await self.client.get(f"{API}/cases/{self.document_case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertTrue(capability.json()["can_edit_basic"])

        response = await self.client.put(f"{API}/cases/{self.document_case_id}/normal-basic", json=self._payload())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["title"], "第14行文书案件（已修改）")
        self.assertEqual(response.json()["status"], "一审立案受理")
        self.assertEqual(response.json()["data"]["case_creation_step"], "basic")

        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.document_case_id)
            self.assertEqual(persisted.title, "第14行文书案件（已修改）")
            self.assertEqual(persisted.status, "一审立案受理")
            self.assertEqual(persisted.data["case_creation_step"], "basic")
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.document_case_id))).all())
            self.assertEqual([event.action for event in events], ["修改普通案件基本信息"])

    async def test_visible_user_without_action_role_can_edit(self) -> None:
        self.identity = NO_PERMISSION_USER
        response = await self.client.put(f"{API}/cases/{self.no_permission_case_id}/normal-basic", json=self._payload("可见用户已修改"))
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.no_permission_case_id)
            self.assertEqual(persisted.title, "可见用户已修改")
            self.assertIsNotNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.no_permission_case_id)))

    async def test_archive_lock_still_rejects_without_writes(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.archived_case_id}/normal-basic", json=self._payload("不应写入"))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("归档", response.text)
        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.archived_case_id)
            self.assertEqual(persisted.title, "第14行归档案件")
            self.assertEqual(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.archived_case_id)), None)


if __name__ == "__main__":
    unittest.main()

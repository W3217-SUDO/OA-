"""8.27 row 16: legacy-equivalent litigant search and detail editing."""

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
EDITOR = {
    "username": "row16-editor",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第16行案件承办",
    "department": "诉讼部",
}
VIEWER = {
    "username": "row16-viewer",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第16行只读人员",
    "department": "诉讼部",
}


class CaseLitigantDetailRow16Test(unittest.IsolatedAsyncioTestCase):
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
                SystemParameter(
                    category="customer_type",
                    code="PARTY",
                    name="当事人",
                    sort_order=2,
                    is_active=True,
                ),
                JobRole(
                    code="ROW16-EDITOR",
                    name="案件承办",
                    permissions=["案件承办"],
                    data_scope="本人及共享数据",
                    is_active=True,
                ),
                User(
                    username=EDITOR["username"],
                    display_name=EDITOR["display_name"],
                    department=EDITOR["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={"position": "案件承办", "permission_role": "案件承办"},
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
                self._customer("CODEX-827-16-CUSTOMER-A", "第16行关键字甲公司", EDITOR["username"], "潜在"),
                self._customer("CODEX-827-16-CUSTOMER-B", "第16行公开乙当事人", VIEWER["username"], "公海"),
                self._customer("CODEX-827-16-CUSTOMER-HIDDEN", "第16行不可见丙公司", VIEWER["username"], "潜在"),
                self._case("CODEX-827-16-EDIT", EDITOR["username"], "文书准备"),
                self._case("CODEX-827-16-VIEWER", VIEWER["username"], "文书准备"),
                self._case("CODEX-827-16-ARCHIVED", EDITOR["username"], "已归档"),
            ])
            await db.flush()
            self.edit_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-16-EDIT"))
            self.viewer_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-16-VIEWER"))
            self.archived_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-16-ARCHIVED"))
            await db.commit()

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row16.test")

    @staticmethod
    def _customer(serial_no: str, title: str, owner: str, status: str) -> BusinessRecord:
        return BusinessRecord(
            module="customer",
            serial_no=serial_no,
            title=title,
            customer=title,
            status=status,
            owner=owner,
            department="诉讼部",
            data={"customer_type": "当事人", "customer_managers": [owner]},
        )

    @staticmethod
    def _case(serial_no: str, owner: str, status: str) -> BusinessRecord:
        return BusinessRecord(
            module="case",
            serial_no=serial_no,
            title=serial_no,
            customer="第16行客户",
            status=status,
            owner=owner,
            department="诉讼部",
            data={
                "case_type": "民事案件",
                "case_creation_step": "basic",
                "plaintiffs": ["旧原告"],
                "plaintiff_agents": ["旧原告代理人"],
                "defendants": ["旧被告"],
                "defendant_agents": [],
                "third_parties": [],
                "third_party_agents": [],
                "plaintiff": "旧原告",
                "opponent": "旧被告",
                "handling_lawyers": ["既有经办律师"],
                "case_team_usernames": [owner, "existing-handler"],
                "unrelated_marker": "必须保留",
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

    @staticmethod
    def _payload() -> dict:
        return {
            "plaintiffs": ["第16行关键字甲公司", "新增原告"],
            "plaintiff_agents": ["原告代理人甲"],
            "defendants": ["第16行公开乙当事人", "新增被告"],
            "defendant_agents": ["被告代理人乙"],
            "third_parties": ["新增第三人"],
            "third_party_agents": [],
            "comment": "CODEX-827-16 独立修改当事人",
        }

    async def test_keyword_candidates_follow_visibility_and_include_public_party(self) -> None:
        response = await self.client.get(f"{API}/case-litigant-candidates", params={"keyword": "第16行"})
        self.assertEqual(response.status_code, 200, response.text)
        titles = [item["title"] for item in response.json()["items"]]
        self.assertIn("第16行关键字甲公司", titles)
        self.assertIn("第16行公开乙当事人", titles)
        self.assertNotIn("第16行不可见丙公司", titles)

    async def test_detail_edit_preserves_wizard_status_team_and_unrelated_fields(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.edit_case_id}/litigants-detail", json=self._payload())
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["status"], "文书准备")
        self.assertEqual(result["data"]["case_creation_step"], "basic")
        self.assertEqual(result["data"]["plaintiffs"], self._payload()["plaintiffs"])
        self.assertEqual(result["data"]["defendants"], self._payload()["defendants"])

        async with self.sessions() as db:
            persisted = await db.get(BusinessRecord, self.edit_case_id)
            self.assertEqual(persisted.status, "文书准备")
            self.assertEqual(persisted.data["case_creation_step"], "basic")
            self.assertEqual(persisted.data["handling_lawyers"], ["既有经办律师"])
            self.assertEqual(persisted.data["case_team_usernames"], [EDITOR["username"], "existing-handler"])
            self.assertEqual(persisted.data["unrelated_marker"], "必须保留")
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.edit_case_id))).all())
            self.assertEqual([event.action for event in events], ["修改案件当事人"])
            self.assertEqual(events[0].comment, self._payload()["comment"])

    async def test_missing_permission_and_archive_lock_reject_without_writes(self) -> None:
        self.identity = VIEWER
        forbidden = await self.client.put(f"{API}/cases/{self.viewer_case_id}/litigants-detail", json=self._payload())
        self.assertEqual(forbidden.status_code, 403, forbidden.text)

        self.identity = EDITOR
        archived = await self.client.put(f"{API}/cases/{self.archived_case_id}/litigants-detail", json=self._payload())
        self.assertEqual(archived.status_code, 409, archived.text)
        self.assertIn("归档", archived.text)

        async with self.sessions() as db:
            viewer_case = await db.get(BusinessRecord, self.viewer_case_id)
            archived_case = await db.get(BusinessRecord, self.archived_case_id)
            self.assertEqual(viewer_case.data["plaintiffs"], ["旧原告"])
            self.assertEqual(archived_case.data["plaintiffs"], ["旧原告"])
            self.assertEqual((await db.scalars(select(WorkflowEvent))).all(), [])


if __name__ == "__main__":
    unittest.main()

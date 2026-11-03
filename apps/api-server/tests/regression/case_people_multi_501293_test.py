"""501293：调查员按关联线索每条一人（不去重）；案源人单选、旧值保留不报错；开庭律师可多人。"""

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
IDENTITY = {
    "username": "p293-handler",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "经办人293",
    "department": "诉讼部",
}


class CasePeopleMulti501293Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(JobRole(code="P293-HANDLER", name="案件经办", permissions=["案件承办"], data_scope="本人及共享数据", is_active=True))
            for username, name in ((IDENTITY["username"], IDENTITY["display_name"]), ("sugq", "苏贵全"), ("yuxd", "虞向东"), ("wengjie", "翁洁")):
                db.add(User(username=username, display_name=name, department="诉讼部", role="user", role_ids=["user"], password_hash="x",
                            profile={"position": "案件经办", "permission_role": "案件经办"}, is_active=True))
            db.add(BusinessRecord(module="customer", serial_no="P293-CUSTOMER", title="客户293", customer="", status="正常",
                                  owner=IDENTITY["username"], department="诉讼部", data={}))
            db.add(SystemParameter(category="case_phase", code="DOCUMENT", name="文书准备", sort_order=1, is_active=True))
            await db.flush()
            self.customer_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "P293-CUSTOMER"))
            self.clues = []
            for no, owner in (("M293A", "sugq"), ("M293B", "sugq"), ("M293C", "yuxd")):
                clue = BusinessRecord(module="clue", serial_no=no, title=no, customer="客户293", status="已取证", owner=owner, department="调查部", data={})
                db.add(clue)
                self.clues.append(clue)
            case = BusinessRecord(module="case", serial_no="P293-CASE", title="案件293", customer="客户293", status="文书准备",
                                  owner=IDENTITY["username"], department="诉讼部", data={
                                      "case_type": "民事争议", "cause_or_charge": "侵害商标权纠纷",
                                      "handling_lawyers": [IDENTITY["display_name"]], "handling_lawyer_usernames": [IDENTITY["username"]],
                                      "case_team_usernames": [IDENTITY["username"]],
                                      "investigator": "苏贵全,苏贵全,苏贵全", "investigator_username": "sugq,sugq,sugq",
                                      "business_owner": "离职员工",
                                  })
            db.add(case)
            await db.commit()
            self.case_id = case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://p293.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def _payload(self, **extra) -> dict:
        return {"customer_record_id": self.customer_id, "title": "案件293", "case_phase": "文书准备", "cause_or_charge": "侵害商标权纠纷",
                "handling_lawyers": [IDENTITY["username"]], "assistant": "", "business_owner": "", "investigator": "",
                "investigation_clue_ids": [], "right_type": "", "source_person": "", "comment": "", **extra}

    async def test_investigators_follow_clues_one_per_clue(self) -> None:
        from unittest.mock import AsyncMock, patch
        with patch("app.core.case_relations.validate_case_clues", AsyncMock()), patch("app.core.case_relations.sync_case_clues", AsyncMock()):
            response = await self.client.put(f"{API}/cases/{self.case_id}/normal-basic",
                                             json=self._payload(investigation_clue_ids=[clue.id for clue in self.clues], business_owner="离职员工"))
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["investigator_usernames"], ["sugq", "sugq", "yuxd"])
        self.assertEqual(data["investigator"], "苏贵全、苏贵全、虞向东")
        self.assertEqual(data["investigator_username"], "sugq,sugq,yuxd")
        self.assertEqual([row["clue_no"] for row in data["investigator_clues"]], ["M293A", "M293B", "M293C"])
        self.assertEqual(data["business_owner"], "离职员工")

    async def test_without_clues_legacy_investigator_kept_and_owner_single(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.case_id}/normal-basic", json=self._payload(business_owner="wengjie"))
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["investigator_username"], "sugq,sugq,sugq")
        self.assertEqual(data["business_owner"], "翁洁")
        self.assertEqual(data["business_owner_username"], "wengjie")

    async def test_new_unknown_owner_is_rejected(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.case_id}/normal-basic", json=self._payload(business_owner="手输的人"))
        self.assertEqual(response.status_code, 422, response.text)

    async def test_multiple_hearing_lawyers(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.case_id}/hearing-lawyer", json={"hearing_lawyers": ["yuxd", "sugq"], "comment": ""})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["hearing_lawyer_usernames"], ["yuxd", "sugq"])
        self.assertEqual(data["hearing_lawyer_username"], "yuxd")
        self.assertEqual(data["hearing_lawyer"], "虞向东、苏贵全")


if __name__ == "__main__":
    unittest.main()

"""8.27 row 17: legacy ordinary-case phases must not block basic edits."""

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
    "username": "row17-handler",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "第17行经办人",
    "department": "诉讼部",
}


class CaseBasicEditLegacyPhaseRow17Test(unittest.IsolatedAsyncioTestCase):
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
            db.add_all([
                JobRole(
                    code="ROW17-HANDLER",
                    name="案件经办",
                    permissions=["案件承办"],
                    data_scope="本人及共享数据",
                    is_active=True,
                ),
                User(
                    username=IDENTITY["username"],
                    display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"],
                    role="user",
                    role_ids=["user"],
                    password_hash="x",
                    profile={"position": "案件经办", "permission_role": "案件经办"},
                    is_active=True,
                ),
                BusinessRecord(
                    module="customer",
                    serial_no="CODEX-827-17-CUSTOMER",
                    title="第17行客户",
                    customer="",
                    status="正常",
                    owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={},
                ),
                SystemParameter(
                    category="case_phase",
                    code="DOCUMENT",
                    name="文书准备",
                    sort_order=1,
                    is_active=True,
                ),
            ])
            await db.flush()
            self.customer_id = await db.scalar(select(BusinessRecord.id).where(
                BusinessRecord.serial_no == "CODEX-827-17-CUSTOMER"
            ))
            for case_type, serial_no in (
                ("刑事案件", "CODEX-827-17-CRIMINAL"),
                ("行政案件及国家赔偿", "CODEX-827-17-ADMINISTRATIVE"),
            ):
                db.add(BusinessRecord(
                    module="case",
                    serial_no=serial_no,
                    title=f"{case_type}旧阶段案件",
                    customer="第17行客户",
                    status="待分配",
                    owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={
                        "case_type": case_type,
                        "case_creation_step": "basic",
                        "cause_or_charge": "测试案由",
                        "handling_lawyers": [IDENTITY["display_name"]],
                        "handling_lawyer_usernames": [IDENTITY["username"]],
                        "case_team_usernames": [IDENTITY["username"]],
                    },
                ))
            await db.commit()
            self.case_ids = {
                record.serial_no: record.id
                for record in (await db.scalars(select(BusinessRecord).where(
                    BusinessRecord.serial_no.in_(["CODEX-827-17-CRIMINAL", "CODEX-827-17-ADMINISTRATIVE"])
                ))).all()
            }
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row17.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def _payload(self, serial_no: str, phase: str = "待分配") -> dict:
        return {
            "customer_record_id": self.customer_id,
            "title": f"{serial_no}基本信息已修改",
            "case_phase": phase,
            "cause_or_charge": "测试案由已修改",
            "handling_lawyers": [IDENTITY["username"]],
            "assistant": "",
            "business_owner": "",
            "investigator": "",
            "investigation_clue_ids": [],
            "right_type": "",
            "source_person": "",
            "comment": "CODEX-827-17 修改基本信息",
        }

    async def test_unchanged_legacy_phase_allows_criminal_and_administrative_basic_edits(self) -> None:
        for serial_no, case_id in self.case_ids.items():
            with self.subTest(serial_no=serial_no):
                response = await self.client.put(
                    f"{API}/cases/{case_id}/normal-basic",
                    json=self._payload(serial_no),
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["status"], "待分配")
                self.assertEqual(response.json()["data"]["case_creation_step"], "basic")

        async with self.sessions() as db:
            records = (await db.scalars(select(BusinessRecord).where(
                BusinessRecord.id.in_(self.case_ids.values())
            ))).all()
            self.assertTrue(all(record.status == "待分配" for record in records))
            events = (await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id.in_(self.case_ids.values())
            ))).all()
            self.assertEqual(len(events), 2)
            self.assertTrue(all(event.from_status == "待分配" and event.to_status == "待分配" for event in events))

    async def test_changed_invalid_phase_is_still_rejected_atomically(self) -> None:
        case_id = self.case_ids["CODEX-827-17-CRIMINAL"]
        response = await self.client.put(
            f"{API}/cases/{case_id}/normal-basic",
            json=self._payload("CODEX-827-17-CRIMINAL", phase="不存在的阶段"),
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("案件阶段不是允许的办理阶段", response.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, case_id)
            self.assertEqual(record.status, "待分配")
            self.assertNotIn("已修改", record.title)
            self.assertIsNone(await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == case_id)))

    async def test_changed_active_phase_remains_supported(self) -> None:
        case_id = self.case_ids["CODEX-827-17-ADMINISTRATIVE"]
        response = await self.client.put(
            f"{API}/cases/{case_id}/normal-basic",
            json=self._payload("CODEX-827-17-ADMINISTRATIVE", phase="文书准备"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "文书准备")


if __name__ == "__main__":
    unittest.main()

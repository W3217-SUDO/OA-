"""Runtime contract for Legal CasePhaseTypeChange batch atomicity.

CodeGraph evidence:
- `codegraph explore "CasePhaseTypeChange"` surfaced
  `Areas/Legal/Controllers/CaseController.cs:1522-1544`: the old POST action
  delegates the full `caseNos` list to `CaseService.Instance.UpdateMultipleCase`
  and returns `PostResponse.IsSuccess=false` on `ApplicationException`.
- `codegraph explore "class CaseService"` plus `rg --glob "*.cs"
  "UpdateMultipleCase\\s*\\("` found no `CaseService` implementation in the
  archived Web source, only controller calls at Legal CaseController lines
  1138 and 1529 plus an IPR evidence-file flow.

The local FastAPI contract must therefore prove its own batch semantics:
preflight every selected case before writing, reject mixed inaccessible or
archived batches atomically, and audit every successful update.
"""

import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "phase-user",
    "role": "user",
    "display_name": "Phase User",
    "department": "Phase Department",
}


class CasePhaseChangeAtomicityContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.sessions() as db:
            db.add_all(
                [
                    User(
                        username=IDENTITY["username"],
                        display_name=IDENTITY["display_name"],
                        department=IDENTITY["department"],
                        role=IDENTITY["role"],
                        password_hash="x",
                        is_active=True,
                    ),
                    User(
                        username="phase-other",
                        display_name="Phase Other",
                        department="Other Department",
                        role="user",
                        password_hash="x",
                        is_active=True,
                    ),
                    RolePermission(
                        role="user",
                        display_name="Phase User",
                        data_scope="本人及共享数据",
                        menu_keys=["case", "@action:case.phase.update"],
                        field_keys=[],
                    ),
                ]
            )
            phase = SystemParameter(
                category="case_phase",
                code="SECOND",
                name="二审",
                sort_order=20,
                is_active=True,
            )
            db.add(phase)
            await db.flush()
            self.phase_id = phase.id
            db.add_all(
                [
                    self._case("PHASE-VALID-001", "文书准备"),
                    self._case("PHASE-VALID-002", "一审立案受理"),
                    self._case("PHASE-ARCHIVED-001", "已归档"),
                    self._case("PHASE-HIDDEN-001", "文书准备", owner="phase-other", department="Other Department"),
                ]
            )
            await db.commit()

        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://case-phase-atomicity.test",
        )

    def _case(
        self,
        serial_no: str,
        status: str,
        *,
        owner: str = IDENTITY["username"],
        department: str = IDENTITY["department"],
    ) -> BusinessRecord:
        return BusinessRecord(
            module="case",
            serial_no=serial_no,
            title=f"{serial_no} contract case",
            customer="Phase Customer",
            status=status,
            owner=owner,
            department=department,
            data={
                "case_type": "民事案件",
                "case_creation_step": "completed",
                "case_creation_approval_status": "已通过",
                "handling_lawyer_usernames": [owner],
                "case_team_usernames": [owner],
            },
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _record_snapshot(self, *serial_nos: str) -> dict[str, tuple[str, dict]]:
        async with self.sessions() as db:
            rows = list(
                (
                    await db.scalars(
                        select(BusinessRecord).where(BusinessRecord.serial_no.in_(serial_nos))
                    )
                ).all()
            )
            return {row.serial_no: (row.status, dict(row.data or {})) for row in rows}

    async def _event_count(self, *serial_nos: str) -> int:
        async with self.sessions() as db:
            record_ids = list(
                (
                    await db.scalars(
                        select(BusinessRecord.id).where(BusinessRecord.serial_no.in_(serial_nos))
                    )
                ).all()
            )
            return int(
                await db.scalar(select(func.count(WorkflowEvent.id)).where(WorkflowEvent.record_id.in_(record_ids)))
                or 0
            )

    async def test_mixed_inaccessible_case_rejects_whole_batch_without_mutation(self):
        before = await self._record_snapshot("PHASE-VALID-001", "PHASE-HIDDEN-001")

        response = await self.client.post(
            f"{API}/cases/phase-change",
            json={
                "case_nos": ["PHASE-VALID-001", "PHASE-HIDDEN-001"],
                "case_phase_id": self.phase_id,
                "comment": "must reject as one batch",
            },
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertIn("PHASE-HIDDEN-001", response.text)
        self.assertEqual(await self._record_snapshot("PHASE-VALID-001", "PHASE-HIDDEN-001"), before)
        self.assertEqual(await self._event_count("PHASE-VALID-001", "PHASE-HIDDEN-001"), 0)

    async def test_mixed_archived_case_rejects_whole_batch_without_mutation(self):
        before = await self._record_snapshot("PHASE-VALID-001", "PHASE-ARCHIVED-001")

        response = await self.client.post(
            f"{API}/cases/phase-change",
            json={
                "case_nos": ["PHASE-VALID-001", "PHASE-ARCHIVED-001"],
                "case_phase_id": self.phase_id,
                "comment": "archived case must stop all writes",
            },
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(await self._record_snapshot("PHASE-VALID-001", "PHASE-ARCHIVED-001"), before)
        self.assertEqual(await self._event_count("PHASE-VALID-001", "PHASE-ARCHIVED-001"), 0)

    async def test_valid_batch_updates_every_case_and_writes_one_audit_per_case(self):
        response = await self.client.post(
            f"{API}/cases/phase-change",
            json={
                "case_nos": ["PHASE-VALID-001", "PHASE-VALID-002"],
                "case_phase_id": self.phase_id,
                "comment": "valid batch",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["updated"], 2)
        self.assertEqual(payload["case_nos"], ["PHASE-VALID-001", "PHASE-VALID-002"])
        self.assertEqual(payload["phase"]["id"], self.phase_id)
        self.assertEqual(payload["phase"]["canonical_name"], "二审")
        self.assertEqual({item["serial_no"] for item in payload["items"]}, {"PHASE-VALID-001", "PHASE-VALID-002"})

        after = await self._record_snapshot("PHASE-VALID-001", "PHASE-VALID-002")
        self.assertEqual({status for status, _data in after.values()}, {"二审"})
        for _status, data in after.values():
            self.assertEqual(data["case_phase_id"], self.phase_id)
            self.assertEqual(data["case_phase_code"], "SECOND")
            self.assertEqual(data["case_phase_name"], "二审")
            self.assertIn("phase_changed_at", data)

        async with self.sessions() as db:
            events = list(
                (
                    await db.scalars(
                        select(WorkflowEvent)
                        .join(BusinessRecord, BusinessRecord.id == WorkflowEvent.record_id)
                        .where(BusinessRecord.serial_no.in_(["PHASE-VALID-001", "PHASE-VALID-002"]))
                    )
                ).all()
            )
        self.assertEqual(len(events), 2)
        self.assertEqual({event.action for event in events}, {"修改案件阶段"})
        self.assertEqual({event.to_status for event in events}, {"二审"})
        self.assertTrue(all(event.operator == IDENTITY["username"] for event in events))
        self.assertTrue(all("valid batch" in event.comment for event in events))


if __name__ == "__main__":
    unittest.main()

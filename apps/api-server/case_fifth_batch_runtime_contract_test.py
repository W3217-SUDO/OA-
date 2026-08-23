"""Executable Case API contracts against an isolated in-memory SQLite database.

The suite imports the real FastAPI application and replaces only its database
and identity dependencies.  It never calls a deployed service, reads an
environment variable, or creates rows in the development database.
"""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import ARCHIVE_REQUIRED_CATEGORIES, app
from app.models import BusinessRecord, FileAttachment, LegacyCase, SystemParameter, WorkflowEvent
from app.security import current_identity


TEST_IDENTITY = {
    "username": "runtime-admin",
    "role": "admin",
    "display_name": "Runtime Admin",
    "department": "Runtime Department",
}


class CaseApiRuntimeContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.previous_overrides = dict(app.dependency_overrides)

        async def override_get_db():
            async with self.session_factory() as session:
                yield session

        async def override_identity():
            return TEST_IDENTITY

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_identity] = override_identity
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://case-runtime.test",
        )
        await self._seed_database()

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def _seed_database(self) -> None:
        async with self.session_factory() as session:
            case = BusinessRecord(
                module="case",
                serial_no="CASE-RUNTIME-001",
                title="Runtime case",
                customer="Runtime customer",
                status="EXECUTING",
                owner=TEST_IDENTITY["username"],
                department=TEST_IDENTITY["department"],
                data={
                    "case_creation_step": "completed",
                    "case_type": "civil",
                    "case_team_usernames": [TEST_IDENTITY["username"]],
                },
            )
            session.add(case)
            session.add(
                SystemParameter(
                    category="case_file_type",
                    code="ROOT",
                    name="Root file",
                    extra={"parent_code": ""},
                    sort_order=1,
                    is_active=True,
                )
            )
            session.add(
                SystemParameter(
                    category="case_file_type",
                    code="CHILD",
                    name="Child file",
                    extra={"parent_code": "ROOT"},
                    sort_order=2,
                    is_active=True,
                )
            )
            session.add(
                SystemParameter(
                    category="court",
                    code="COURT-A",
                    name="Runtime Court",
                    extra={},
                    sort_order=1,
                    is_active=True,
                )
            )
            await session.flush()
            self.case_id = case.id

            for index in range(16):
                session.add(
                    BusinessRecord(
                        module="task",
                        serial_no=f"TASK-RUNTIME-{index:02d}",
                        title=f"Runtime task {index}",
                        customer=case.customer,
                        status="PENDING",
                        owner=TEST_IDENTITY["username"],
                        department=case.department,
                        data={"case_id": case.id, "case_no": case.serial_no},
                    )
                )
            session.add(
                BusinessRecord(
                    module="task",
                    serial_no="TASK-RUNTIME-UNRELATED",
                    title="Unrelated runtime task",
                    customer="Other customer",
                    status="PENDING",
                    owner=TEST_IDENTITY["username"],
                    department=case.department,
                    data={"case_id": 987654, "case_no": "CASE-OTHER"},
                )
            )
            await session.commit()

    async def _workflow_event_count(self) -> int:
        async with self.session_factory() as session:
            return len((await session.scalars(select(WorkflowEvent))).all())

    async def test_reference_options_are_loaded_from_isolated_database(self) -> None:
        response = await self.client.get("/api/v1/cases/reference-options")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["case_file_types"][:2], [
            {"value": "Root file", "label": "Root file", "code": "ROOT", "parent_code": ""},
            {"value": "Child file", "label": "Child file", "code": "CHILD", "parent_code": "ROOT"},
        ])
        self.assertEqual(payload["courts"], [{"value": "Runtime Court", "label": "Runtime Court", "code": "COURT-A"}])

    async def test_case_tasks_default_page_filters_linked_items_and_exposes_pagination(self) -> None:
        response = await self.client.get(f"/api/v1/cases/{self.case_id}/tasks")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["case"]["id"], self.case_id)
        self.assertEqual(payload["total"], 16)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 15)
        self.assertEqual(payload["pages"], 2)
        self.assertEqual(len(payload["items"]), 15)
        self.assertTrue(all(item["data"]["case_id"] == self.case_id for item in payload["items"]))
        first_page_serials = {item["serial_no"] for item in payload["items"]}
        self.assertNotIn("TASK-RUNTIME-UNRELATED", first_page_serials)

        second = await self.client.get(
            f"/api/v1/cases/{self.case_id}/tasks",
            params={"page": 2, "page_size": 15},
        )
        self.assertEqual(second.status_code, 200, second.text)
        second_payload = second.json()
        self.assertEqual(second_payload["case"]["id"], self.case_id)
        self.assertEqual(second_payload["total"], 16)
        self.assertEqual(second_payload["page"], 2)
        self.assertEqual(second_payload["page_size"], 15)
        self.assertEqual(second_payload["pages"], 2)
        self.assertEqual(len(second_payload["items"]), 1)
        self.assertTrue(all(item["data"]["case_id"] == self.case_id for item in second_payload["items"]))
        combined_serials = first_page_serials | {item["serial_no"] for item in second_payload["items"]}
        self.assertEqual(combined_serials, {f"TASK-RUNTIME-{index:02d}" for index in range(16)})

    async def test_archive_readiness_is_calculated_by_backend_facts(self) -> None:
        response = await self.client.get(f"/api/v1/cases/{self.case_id}/archive-readiness")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(set(payload["checks"]), {
            "case_closed",
            "fees_settled",
            "documents_complete",
            "finance_complete",
        })
        self.assertFalse(payload["checks"]["case_closed"])
        self.assertFalse(payload["checks"]["documents_complete"])

    async def test_normal_archive_review_requires_reviewer_archive_number(self) -> None:
        async with self.session_factory() as session:
            case = await session.get(BusinessRecord, self.case_id)
            case.status = "\u5f85\u5f52\u6863\u5ba1\u6838"
            case.data = {
                **(case.data or {}),
                "archive_type": "normal",
                "case_closed_at": "2026-08-23T10:00:00",
                "case_closed_by": TEST_IDENTITY["username"],
            }
            for index, category in enumerate(ARCHIVE_REQUIRED_CATEGORIES):
                session.add(FileAttachment(
                    record_id=self.case_id,
                    category=category,
                    original_name=f"archive-{index}.txt",
                    stored_name=f"archive-{index}.txt",
                    path=f"archive-{index}.txt",
                    uploader=TEST_IDENTITY["username"],
                ))
            await session.commit()

        missing = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": "approved"},
        )
        self.assertEqual(missing.status_code, 422, missing.text)

        archive_no = "2026-248"
        approved = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": "approved", "archive_no": archive_no},
        )
        self.assertEqual(approved.status_code, 200, approved.text)

        async with self.session_factory() as session:
            case = await session.get(BusinessRecord, self.case_id)
            legacy_case = await session.scalar(
                select(LegacyCase).where(LegacyCase.CaseNo == case.serial_no)
            )
        self.assertEqual(case.data["archive_no"], archive_no)
        self.assertEqual(legacy_case.FileNo, archive_no)
        self.assertEqual(legacy_case.ArchivedFileNo, archive_no)

    async def test_normal_archive_review_does_not_block_on_advisory_material_checks(self) -> None:
        async with self.session_factory() as session:
            case = await session.get(BusinessRecord, self.case_id)
            case.status = "\u5f85\u5f52\u6863\u5ba1\u6838"
            case.data = {**(case.data or {}), "archive_type": "normal"}
            await session.commit()

        approved = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": "materials reviewed manually", "archive_no": "2026-ADVISORY"},
        )
        self.assertEqual(approved.status_code, 200, approved.text)

    async def test_deficit_archive_persists_reason_and_legacy_projection(self) -> None:
        missing_reason = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive",
            json={"archive_type": "deficit", "comment": "", "submit": True},
        )
        self.assertEqual(missing_reason.status_code, 422, missing_reason.text)

        reason = "CODEX-818-R21-deficit-reason"
        response = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive",
            json={"archive_type": "deficit", "comment": reason, "submit": True},
        )

        self.assertEqual(response.status_code, 200, response.text)
        async with self.session_factory() as session:
            case = await session.get(BusinessRecord, self.case_id)
            legacy_case = await session.scalar(
                select(LegacyCase).where(LegacyCase.CaseNo == case.serial_no)
            )
            event = await session.scalar(
                select(WorkflowEvent)
                .where(
                    WorkflowEvent.record_id == self.case_id,
                    WorkflowEvent.action == "提交亏损归档内部审核",
                )
                .order_by(WorkflowEvent.id.desc())
            )

        self.assertEqual(case.status, "亏损内审")
        self.assertEqual(case.data["archive_type"], "deficit")
        self.assertEqual(case.data["archive_submit_comment"], reason)
        self.assertEqual(case.data["archive_status"], "待内部审核")
        self.assertEqual(case.data["case_phase_id"], 106016)
        self.assertIsNotNone(legacy_case)
        self.assertEqual(legacy_case.ArchiveStatus, 7)
        self.assertEqual(legacy_case.ArchiveTypeId, 2)
        self.assertEqual(legacy_case.ToAuditRemark, reason)
        self.assertIsNotNone(event)
        self.assertEqual(event.comment, reason)

        internal_comment = "无负责人；内部审核同意"
        internal_response = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": internal_comment},
        )
        self.assertEqual(internal_response.status_code, 200, internal_response.text)
        self.assertEqual(internal_response.json()["status"], "亏损审核")

        async with self.session_factory() as session:
            case = await session.get(BusinessRecord, self.case_id)
            legacy_case = await session.scalar(select(LegacyCase).where(LegacyCase.CaseNo == case.serial_no))
        self.assertEqual(case.data["archive_status"], "待审核")
        self.assertEqual(case.data["case_phase_id"], 106017)
        self.assertEqual(case.data["archive_internal_review_comment"], internal_comment)
        self.assertEqual(legacy_case.ArchiveStatus, 10)
        self.assertEqual(legacy_case.InternalAuditedRemark, internal_comment)

        final_comment = "亏损归档审核同意"
        final_response = await self.client.post(
            f"/api/v1/cases/{self.case_id}/archive/review",
            json={"approved": True, "comment": final_comment},
        )
        self.assertEqual(final_response.status_code, 200, final_response.text)
        self.assertEqual(final_response.json()["status"], "亏损归档")

        async with self.session_factory() as session:
            case = await session.get(BusinessRecord, self.case_id)
            legacy_case = await session.scalar(select(LegacyCase).where(LegacyCase.CaseNo == case.serial_no))
        self.assertEqual(case.data["archive_status"], "审核通过")
        self.assertEqual(case.data["case_phase_id"], 106018)
        self.assertEqual(case.data["archive_no"], "")
        self.assertEqual(legacy_case.ArchiveStatus, 20)
        self.assertEqual(legacy_case.AuditedRemark, final_comment)

    async def test_batch_update_preflights_every_case_before_writing(self) -> None:
        before = await self._workflow_event_count()
        response = await self.client.post(
            "/api/v1/cases/batch-update",
            json={
                "case_ids": [self.case_id, 999999],
                "case_stage": "stage-probe",
            },
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(await self._workflow_event_count(), before)

    async def test_merge_rejects_missing_source_without_writing(self) -> None:
        before = await self._workflow_event_count()
        response = await self.client.post(
            f"/api/v1/cases/{self.case_id}/merge",
            json={"source_case_no": "CASE-MISSING-999", "comment": "runtime probe"},
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(await self._workflow_event_count(), before)


if __name__ == "__main__":
    unittest.main()

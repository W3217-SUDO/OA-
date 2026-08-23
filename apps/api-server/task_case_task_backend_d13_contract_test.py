"""Runtime contracts for legacy task pages and case task completion (D13).

The fixture is an isolated SQLite database.  It exercises the old TaskController
PageId relation matrix, the CaseTaskController page contract, and Finished(caseIds)
preflight/transaction semantics without touching the development database.
CodeGraph evidence used for this matrix: Areas/TP/Controllers/TaskController.cs
(TaskList/TaskSearchList/Finished) and Areas/IPR/Controllers/CaseTaskController.cs
(CaseTaskList/Finished).
"""

from datetime import date, timedelta
import unittest

import httpx
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Notification, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "d13-user",
    "role": "user",
    "display_name": "D13 User",
    "department": "D13 Department",
}


class TaskCaseTaskD13Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.sql = []
        self._listener = lambda conn, cursor, statement, parameters, context, executemany: self.sql.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", self._listener)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="d13-user", display_name="D13 User", department="D13 Department", role="user", password_hash="x", is_active=True),
                User(username="d13-other", display_name="D13 Other", department="Other Department", role="user", password_hash="x", is_active=True),
                RolePermission(role="user", display_name="D13 User", data_scope="全所数据", menu_keys=["task", "case", "@action:case.progress.update"], field_keys=[]),
            ])
            base = date.today() + timedelta(days=30)
            rows = []
            for index in range(205):
                rows.append(BusinessRecord(
                    module="task", serial_no=f"D13-T-{index:03d}", title=f"Task {index}", owner="d13-user",
                    department="D13 Department", status="待接收", created_at=None,
                    data={"deadline": str(base - timedelta(days=index)), "initiator": "d13-user", "collaborators": []},
                ))
            # Cross-relation rows must be visible only through the matching relation.
            relation_deadline = base - timedelta(days=300)
            rows.append(BusinessRecord(module="task", serial_no="D13-INITIATED", title="Initiated", owner="d13-other", department="Other Department", status="待接收", data={"deadline": str(relation_deadline), "initiator": "d13-user", "collaborators": []}))
            rows.append(BusinessRecord(module="task", serial_no="D13-COLLAB", title="Collaborating", owner="d13-other", department="Other Department", status="待接收", data={"deadline": str(relation_deadline), "initiator": "d13-other", "collaborators": ["d13-user"]}))
            rows.append(BusinessRecord(module="task", serial_no="D13-INVESTIGATION-HIDDEN", title="Investigation child", owner="d13-user", department="D13 Department", status="待接收", data={"deadline": str(relation_deadline), "initiator": "d13-user", "collaborators": [], "source": "调查任务", "investigation_record_id": 999, "investigation_no": "DC-D13-001", "investigation_module": "investigation"}))
            rows.append(BusinessRecord(module="task", serial_no="D13-HIDDEN", title="Hidden", owner="d13-other", department="Other Department", status="待接收", data={"deadline": str(relation_deadline), "initiator": "d13-other", "collaborators": []}))
            db.add_all(rows)
            case = BusinessRecord(
                module="case", serial_no="D13-CASE-001", title="D13 Case", owner="d13-other", department="D13 Department",
                status="办理中", data={"case_team_usernames": ["d13-user"], "case_creation_step": "completed"},
            )
            db.add(case)
            await db.flush()
            linked = []
            for index in range(16):
                linked.append(BusinessRecord(
                    module="task", serial_no=f"D13-CASE-T-{index:02d}", title=f"Case task {index}", owner="d13-user",
                    department="D13 Department", status="处理中", data={
                        "deadline": str(date.today() + timedelta(days=16 - index)),
                        "case_id": case.id if index < 15 else None,
                        "case_no": case.serial_no if index == 15 else "",
                        "initiator": "d13-user", "collaborators": [],
                    },
                ))
            # A linked task belonging to another user is not a participant row.
            linked.append(BusinessRecord(
                module="task", serial_no="D13-CASE-HIDDEN", title="Hidden case task", owner="d13-other",
                department="Other Department", status="处理中", data={"case_id": case.id, "deadline": str(date.today() + timedelta(days=100)), "initiator": "d13-other", "collaborators": []},
            ))
            db.add_all(linked)
            await db.commit()
            self.case_id = case.id
            self.linked_ids = [row.id for row in linked[:16]]
            self.task_ids = [row.id for row in rows[:205]]
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://d13.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        event.remove(self.engine.sync_engine, "before_cursor_execute", self._listener)
        await self.engine.dispose()

    async def test_tasks_default_page_deadline_desc_and_sql_permission(self):
        response = await self.client.get(f"{API}/tasks")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 15)
        self.assertEqual(payload["total"], 223)
        self.assertEqual(payload["pages"], 15)
        self.assertEqual(len(payload["items"]), 15)
        self.assertEqual(payload["items"][0]["serial_no"], "D13-T-000")
        self.assertNotIn("D13-HIDDEN", {item["serial_no"] for item in payload["items"]})
        self.assertNotIn("D13-INVESTIGATION-HIDDEN", {item["serial_no"] for item in payload["items"]})
        self.assertTrue(any("deadline" in str(item) for item in payload["items"]))
        selects = [statement.lower() for statement in self.sql if "select" in statement.lower() and "business_records" in statement.lower()]
        self.assertTrue(any("owner" in statement and "module" in statement for statement in selects), selects)

    async def test_tasks_relation_matrix_has_no_cross_relation_leak(self):
        for relation, serial in (("initiated", "D13-INITIATED"), ("owned", "D13-T-000"), ("collaborating", "D13-COLLAB")):
            response = await self.client.get(f"{API}/tasks", params={"relation": relation, "serial_no": serial, "page_size": 15})
            self.assertEqual(response.status_code, 200, response.text)
            serials = {item["serial_no"] for item in response.json()["items"]}
            self.assertIn(serial, serials)
            self.assertNotIn("D13-HIDDEN", serials)

    async def test_tasks_page_boundary_and_scope_errors(self):
        page = await self.client.get(f"{API}/tasks", params={"page": 15, "page_size": 15})
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual(page.json()["pages"], 15)
        self.assertEqual(len(page.json()["items"]), 13)
        too_large = await self.client.get(f"{API}/tasks", params={"page_size": 201})
        self.assertEqual(too_large.status_code, 422, too_large.text)
        company = await self.client.get(f"{API}/tasks", params={"scope": "company", "serial_no": "D13-HIDDEN"})
        self.assertEqual(company.status_code, 200, company.text)
        self.assertEqual(company.json()["total"], 1)
        legacy = await self.client.get(f"{API}/tasks", params={"page_id": "9001001010", "serial_no": "D13-INITIATED"})
        self.assertEqual(legacy.status_code, 200, legacy.text)
        self.assertEqual(legacy.json()["total"], 1)
        unknown = await self.client.get(f"{API}/tasks", params={"page_id": "9999999999"})
        self.assertEqual(unknown.status_code, 422, unknown.text)

    async def test_case_tasks_default_15_deadline_desc_case_no_link_and_pages(self):
        response = await self.client.get(f"{API}/cases/{self.case_id}/tasks")
        self.assertEqual(response.status_code, 200, response.text)
        first = response.json()
        self.assertEqual(first["total"], 16)
        self.assertEqual(first["page"], 1)
        self.assertEqual(first["page_size"], 15)
        self.assertEqual(first["pages"], 2)
        self.assertEqual(len(first["items"]), 15)
        self.assertNotIn("D13-CASE-HIDDEN", {item["serial_no"] for item in first["items"]})
        second = (await self.client.get(f"{API}/cases/{self.case_id}/tasks", params={"page": 2, "page_size": 15})).json()
        self.assertEqual(len(second["items"]), 1)
        self.assertEqual(second["items"][0]["serial_no"], "D13-CASE-T-15")

    async def test_case_tasks_reject_non_participant_linked_rows(self):
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="D13-CASE-NOPART", title="No participant", owner="d13-other",
                department="Other Department", status="办理中", data={"case_team_usernames": ["d13-user"], "case_creation_step": "completed"},
            )
            db.add(case)
            await db.flush()
            db.add(BusinessRecord(
                module="task", serial_no="D13-NOPART-T", title="No participant task", owner="d13-other",
                department="Other Department", status="处理中", data={"case_id": case.id, "initiator": "d13-other", "collaborators": [], "deadline": str(date.today() + timedelta(days=2))},
            ))
            await db.commit()
            no_participant_case_id = case.id
        response = await self.client.get(f"{API}/cases/{no_participant_case_id}/tasks")
        self.assertEqual(response.status_code, 403, response.text)

    async def test_finished_case_ids_is_atomic_and_audited(self):
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="D13-FINISH-001", title="Finish", owner="d13-other", department="D13 Department", status="办理中", data={"handling_lawyer_usernames": ["d13-user"], "case_team_usernames": ["d13-user"], "case_creation_step": "completed"})
            db.add(case)
            await db.flush()
            db.add_all([
                BusinessRecord(module="task", serial_no="D13-F-1", title="Finish 1", owner="d13-user", department="D13 Department", status="处理中", data={"case_id": case.id, "initiator": "d13-user", "collaborators": ["d13-other"], "deadline": str(date.today() + timedelta(days=3))}),
                BusinessRecord(module="task", serial_no="D13-F-2", title="Finish 2", owner="d13-user", department="D13 Department", status="处理中", data={"case_id": case.id, "initiator": "d13-user", "collaborators": ["d13-other"], "deadline": str(date.today() + timedelta(days=4))}),
            ])
            await db.commit()
            finish_case_id = case.id
        response = await self.client.post(f"{API}/cases/tasks/finished", json={"case_ids": [finish_case_id], "comment": "完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["message"], "标记成功！")
        async with self.sessions() as db:
            tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.serial_no.in_(["D13-F-1", "D13-F-2"])))).all())
            self.assertEqual({task.status for task in tasks}, {"已完成"})
            self.assertEqual(await db.scalar(select(func.count(WorkflowEvent.id)).where(WorkflowEvent.record_id.in_([task.id for task in tasks]))), 2)
            self.assertGreaterEqual(await db.scalar(select(func.count(Notification.id)).where(Notification.source_type == "task")), 1)

    async def test_finished_case_ids_preflight_conflict_and_missing_are_atomic(self):
        blocked = await self.client.post(f"{API}/cases/tasks/finished", json={"case_ids": [self.case_id]})
        self.assertEqual(blocked.status_code, 403, blocked.text)
        async with self.sessions() as db:
            good = BusinessRecord(module="case", serial_no="D13-FINISH-002", title="Good", owner="d13-other", department="D13 Department", status="办理中", data={"handling_lawyer_usernames": ["d13-user"], "case_team_usernames": ["d13-user"], "case_creation_step": "completed"})
            bad = BusinessRecord(module="case", serial_no="D13-FINISH-003", title="Bad", owner="d13-other", department="D13 Department", status="办理中", data={"handling_lawyer_usernames": ["d13-user"], "case_team_usernames": ["d13-user"], "case_creation_step": "completed"})
            db.add_all([good, bad])
            await db.flush()
            good_task = BusinessRecord(module="task", serial_no="D13-F-3", title="Good", owner="d13-user", department="D13 Department", status="处理中", data={"case_id": good.id, "initiator": "d13-user", "collaborators": [], "deadline": str(date.today() + timedelta(days=3))})
            bad_task = BusinessRecord(module="task", serial_no="D13-F-4", title="Bad", owner="d13-user", department="D13 Department", status="已完成", data={"case_id": bad.id, "initiator": "d13-user", "collaborators": [], "deadline": str(date.today() + timedelta(days=3))})
            db.add_all([good_task, bad_task])
            await db.commit()
            good_id, bad_id, good_task_id = good.id, bad.id, good_task.id
        conflict = await self.client.post(f"{API}/cases/tasks/finished", json={"case_ids": [good_id, bad_id]})
        self.assertEqual(conflict.status_code, 409, conflict.text)
        missing = await self.client.post(f"{API}/cases/tasks/finished", json={"case_ids": [good_id, 999999]})
        self.assertEqual(missing.status_code, 404, missing.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, good_task_id)).status, "处理中")
            self.assertEqual(await db.scalar(select(func.count(WorkflowEvent.id)).where(WorkflowEvent.record_id == good_task_id)), 0)


if __name__ == "__main__":
    unittest.main()

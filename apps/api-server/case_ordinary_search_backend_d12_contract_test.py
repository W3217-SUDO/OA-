"""Runtime contract tests for the ordinary case search endpoint (D12).

The fixture is an isolated SQLite database.  It deliberately creates more
than one page of visible cases plus an invisible case so that filtering,
permission scope, sorting and phase counts are exercised independently of the
legacy UI preload limit.
"""

import unittest
from datetime import datetime, timedelta

import httpx
from fastapi import status
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "case-d12-user",
    "role": "user",
    "display_name": "D12 User",
    "department": "D12 Department",
}


class CaseOrdinarySearchD12Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sql_statements = []
        self._sql_listener = lambda conn, cursor, statement, parameters, context, executemany: self.sql_statements.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", self._sql_listener)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.sessions() as db:
            db.add_all([
                User(
                    username=IDENTITY["username"],
                    display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"],
                    role="user",
                    password_hash="test",
                    is_active=True,
                ),
                RolePermission(
                    role="user",
                    display_name="D12 User",
                    data_scope="本人及共享数据",
                    menu_keys=["case"],
                    field_keys=[],
                ),
            ])
            rows = []
            base_time = datetime(2026, 1, 1, 8, 0, 0)
            for index in range(205):
                status_value = "OPEN" if index % 2 == 0 else "CLOSED"
                rows.append(
                    BusinessRecord(
                        module="case",
                        serial_no=f"CASE-D12-{index:03d}",
                        title=f"Ordinary case {index}",
                        customer=f"Customer {index}",
                        status=status_value,
                        owner=IDENTITY["username"],
                        department=IDENTITY["department"],
                        created_at=base_time + timedelta(minutes=index),
                        updated_at=base_time + timedelta(minutes=index),
                        data={"case_type": "民事案件"},
                    )
                )
            db.add_all(rows)
            db.add(
                BusinessRecord(
                    module="case",
                    serial_no="CASE-D12-HIDDEN",
                    title="Invisible case",
                    customer="Other customer",
                    status="HIDDEN",
                    owner="other-user",
                    department="Other department",
                    data={"case_type": "民事案件"},
                )
            )
            await db.flush()
            special = rows[201]
            special.data = {
                "case_type": "民事案件",
                "plaintiffs": ["Plaintiff-201", "Plaintiff-201-B"],
                "prosecutor": "Prosecutor-201",
                "defendants": ["Defendant-201", "Defendant-201-B"],
                "evidence_org": "Evidence-201",
                "notary_nos": ["Notary-201", "Notary-201-B"],
                "clue_no": "CLUE-ROW4-201",
                "first_court_case_no": "COURT-ROW4-201",
                "hearing_lawyers": ["HearingLawyer-201", "HearingLawyer-201-B"],
                "investigators": ["Investigator-201", "Investigator-201-B"],
                "handling_lawyers": ["Handling-201", "Handling-201-B"],
                "court": "Court-201",
                "source_date": "2026-02-10",
                "hearing_date": "2026-03-20",
                "channel": "Channel-201",
                "warehouse": "Warehouse-201",
                "area": "Area-201",
                "location": "Location-201",
            }
            db.add(WorkflowEvent(
                record_id=special.id,
                action="ordinary-search-note",
                from_status="OPEN",
                to_status="OPEN",
                operator=IDENTITY["username"],
                comment="Log-201 evidence",
            ))
            await db.commit()

        self.sql_statements.clear()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://case-d12.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        event.remove(self.engine.sync_engine, "before_cursor_execute", self._sql_listener)
        await self.engine.dispose()

    async def _search(self, payload, expected=status.HTTP_200_OK):
        response = await self.client.post(f"{API}/cases/search", json=payload)
        self.assertEqual(response.status_code, expected, response.text)
        return response.json() if expected == status.HTTP_200_OK else response

    async def test_more_than_200_rows_permissions_paging_and_phase_counts(self):
        first = await self._search({"page": 1, "page_size": 7, "sort_order": "case_no_asc"})
        second = await self._search({"page": 2, "page_size": 7, "sort_order": "case_no_asc"})
        self.assertEqual(first["total"], 205)
        self.assertEqual(first["page"], 1)
        self.assertEqual(first["page_size"], 7)
        self.assertEqual(first["pages"], 30)
        self.assertEqual(len(first["items"]), 7)
        self.assertEqual(len(second["items"]), 7)
        self.assertEqual(first["items"][0]["serial_no"], "CASE-D12-000")
        self.assertEqual(second["items"][0]["serial_no"], "CASE-D12-007")
        self.assertNotIn("CASE-D12-HIDDEN", {item["serial_no"] for item in first["items"] + second["items"]})
        self.assertEqual(first["phase_counts"], second["phase_counts"])
        self.assertEqual(sum(first["phase_counts"].values()), 205)
        self.assertEqual(first["phase_counts"]["OPEN"], 103)
        self.assertEqual(first["phase_counts"]["CLOSED"], 102)
        selects = [sql.lower() for sql in self.sql_statements if "select" in sql.lower() and "business_records" in sql.lower()]
        self.assertTrue(any("owner" in sql and "module" in sql for sql in selects), selects)

    async def test_default_page_size_is_15_and_does_not_overfetch(self):
        result = await self._search({"sort_order": "case_no_asc"})
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["page_size"], 15)
        self.assertEqual(len(result["items"]), 15)
        self.assertEqual(result["total"], 205)

    async def test_all_ordinary_fields_date_bounds_and_log_content(self):
        payload = {
            "plaintiff": "Plaintiff-201",
            "prosecutor": "Prosecutor-201",
            "defendant": "Defendant-201",
            "evidence_org": "Evidence-201",
            "notary_no": "Notary-201",
            "hearing_lawyer": "HearingLawyer-201",
            "investigator": "Investigator-201",
            "handling_lawyer": "Handling-201",
            "court": "Court-201",
            "source_from": "2026-02-01",
            "source_to": "2026-02-28",
            "hearing_from": "2026-03-01",
            "hearing_to": "2026-03-31",
            "channel": "Channel-201",
            "warehouse": "Warehouse-201",
            "area": "Area-201",
            "location": "Location-201",
            "log_content": "Log-201",
        }
        result = await self._search(payload)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["serial_no"], "CASE-D12-201")
        bad_dates = await self._search({"source_from": "2026-03-01", "source_to": "2026-02-01"}, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("source", bad_dates.text)

    async def test_partial_keyword_matches_case_clue_notary_and_court_numbers(self):
        for keyword in ("D12-201", "ROW4-201", "Notary-201-B"):
            with self.subTest(keyword=keyword):
                result = await self._search({"keyword": keyword})
                self.assertEqual(result["total"], 1)
                self.assertEqual(result["items"][0]["serial_no"], "CASE-D12-201")

    async def test_server_sort_and_invalid_page_or_sort(self):
        result = await self._search({"page": 1, "page_size": 3, "sort_order": "case_no_desc"})
        serials = [item["serial_no"] for item in result["items"]]
        self.assertEqual(serials, ["CASE-D12-204", "CASE-D12-203", "CASE-D12-202"])
        await self._search({"page_size": 201}, status.HTTP_422_UNPROCESSABLE_ENTITY)
        await self._search({"sort_order": "not-a-sort"}, status.HTTP_422_UNPROCESSABLE_ENTITY)


if __name__ == "__main__":
    unittest.main()

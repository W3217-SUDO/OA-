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
from sqlalchemy import event, select
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

    async def test_pending_execution_accepts_200_and_keeps_scope(self):
        async with self.sessions() as db:
            rows = list((await db.scalars(select(BusinessRecord))).all())
            for row in rows:
                row.status = "一审待执行"
            await db.commit()
        first = await self.client.get(f"{API}/cases/pending-execution", params={"page_size": 200})
        second = await self.client.get(f"{API}/cases/pending-execution", params={"page_size": 200, "page": 2})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual((first.json()["total"], len(first.json()["items"]), len(second.json()["items"])), (205, 200, 5))
        items = first.json()["items"] + second.json()["items"]
        self.assertEqual(len({row["id"] for row in items}), 205)
        self.assertNotIn("CASE-D12-HIDDEN", {row["serial_no"] for row in items})
        invalid = await self.client.get(f"{API}/cases/pending-execution", params={"page_size": 201})
        self.assertEqual(invalid.status_code, 422)

    async def test_special_unclaimed_database_paging_and_filters_beyond_preload(self):
        async with self.sessions() as db:
            applied = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CASE-D12-000"))
            applied.data = {**applied.data, "commission_applied": True}
            target = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CASE-D12-001"))
            target.data = {**target.data, "court_case_no": "CODEX-court", "notary_no": "CODEX-notary",
                "hearing_lawyer": "CODEX-lawyer", "assistant": "CODEX-assistant", "investigator": "CODEX-investigator", "source_person": "CODEX-source"}
            await db.commit()
        params = {"kind": "unclaimed", "scope": "mine", "page_size": 200}
        first = await self.client.get(f"{API}/cases/special-records", params=params)
        self.assertEqual(first.status_code, 200, first.text)
        second = await self.client.get(f"{API}/cases/special-records", params={**params, "page": 2})
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual((first.json()["total"], len(first.json()["items"]), len(second.json()["items"])), (204, 200, 4))
        ids = [row["id"] for row in first.json()["items"] + second.json()["items"]]
        self.assertEqual(len(set(ids)), 204)
        filtered = await self.client.get(f"{API}/cases/special-records", params={**params,
            "serial_no": "D12-001", "customer": "Customer 1", "status": "CLOSED", "court_case_no": "CODEX-court",
            "notary_no": "CODEX-notary", "hearing_lawyer": "CODEX-lawyer", "assistant": "CODEX-assistant",
            "investigator": "CODEX-investigator", "source_person": "CODEX-source"})
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(filtered.json()["items"][0]["serial_no"], "CASE-D12-001")
        invalid = await self.client.get(f"{API}/cases/special-records", params={**params, "page_size": 201})
        self.assertEqual(invalid.status_code, 422)
        self.assertTrue(any("LIMIT" in sql and "OFFSET" in sql and "business_records" in sql for sql in self.sql_statements))

    async def test_special_refund_union_paging_filters_and_menu_scope(self):
        denied = await self.client.get(f"{API}/cases/special-records", params={"kind": "refund"})
        self.assertEqual(denied.status_code, 403, denied.text)
        async with self.sessions() as db:
            role = await db.scalar(select(RolePermission).where(RolePermission.role == "user"))
            role.menu_keys = ["case", "finance"]
            for index in range(205):
                db.add(BusinessRecord(module="finance" if index < 101 else "refund",
                    serial_no=f"CODEX-D-special-refund-{index}", title="退费申请", status="待审批",
                    owner=IDENTITY["username"], department=IDENTITY["department"], customer="CODEX-customer",
                    updated_at=datetime(2026, 1, 1) + timedelta(minutes=index),
                    data={"fee_type": "诉讼退费", "case_no": f"CODEX-CASE-{index}", "case_stage": "一审",
                        "court_case_no": "CODEX-court-no", "court": "CODEX-court", "payee": "CODEX-unit",
                        "refund_status": "待办理", "refund_amount": 25, "assistant": "CODEX-assistant",
                        "hearing_lawyer": "CODEX-lawyer", "paid_date": "2026-01-15"}))
            db.add(BusinessRecord(module="refund", serial_no="CODEX-D-special-hidden", title="退费", status="待审批",
                owner="other-user", department="Other department", data={"fee_type": "退费"}))
            await db.commit()
        params = {"kind": "refund", "page_size": 200}
        first = await self.client.get(f"{API}/cases/special-records", params=params)
        second = await self.client.get(f"{API}/cases/special-records", params={**params, "page": 2})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual((first.json()["total"], len(first.json()["items"]), len(second.json()["items"])), (205, 200, 5))
        self.assertEqual(len({row["id"] for row in first.json()["items"] + second.json()["items"]}), 205)
        filtered = await self.client.get(f"{API}/cases/special-records", params={**params,
            "serial_no": "CODEX-CASE-101", "customer": "CODEX-customer", "status": "一审", "court_case_no": "CODEX-court-no",
            "court": "CODEX-court", "payee": "CODEX-unit", "refund_status": "待办理", "refund_amount": "25",
            "assistant": "CODEX-assistant", "hearing_lawyer": "CODEX-lawyer", "fee_type": "诉讼退费",
            "paid_from": "2026-01-15", "paid_to": "2026-01-15"})
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(filtered.json()["items"][0]["serial_no"], "CODEX-D-special-refund-101")
        invalid = await self.client.get(f"{API}/cases/special-records", params={**params, "paid_from": "2026-02-01", "paid_to": "2026-01-01"})
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()

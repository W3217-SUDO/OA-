"""法院展示隔离错误、保留原值并保持民事导出契约。"""

import copy
import unittest

import httpx
import xlrd
from fastapi import FastAPI, HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.legal.case_export_projection import CIVIL_HEADERS, _court_name
from app.areas.legal.router import router
from app.core.contracts import _contract_customer_record_dicts
from app.database import Base, get_db
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


class CaseCourtDisplayTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.identity = {"username": "CODEXDOCCT", "role": "admin", "role_ids": ["admin"],
                         "department": "CODEXDOCCT", "display_name": "法院验证", "menu_keys": ["*"],
                         "action_keys": ["*"], "_actual_role_ids": ["admin"], "data_scope": "all"}
        async with self.sessions() as db:
            db.add(User(username="CODEXDOCCT", display_name="法院验证", password_hash="isolated-only",
                        department="CODEXDOCCT", role="admin"))
            db.add_all([
                SystemParameter(category="court", code="黔0201", name="六盘水钟山区人民法院", is_active=False),
                SystemParameter(category="court", code="皖1503", name="六安市裕安区人民法院"),
            ])
            self.records = [BusinessRecord(module="case", serial_no=f"CODEXDOCCT-{index}", title="法院展示",
                customer="", status="一审准备开庭", owner="CODEXDOCCT", department="CODEXDOCCT", data={
                    "case_type": "民事争议", "court": code, "first_court_name": code,
                    "first_court_case_no": f"（2026）{code}民初11035号", "second_court_name": "皖1503",
                    "execution_court_name": "六安市裕安区人民法院", "retrial_court_name": ""})
                for index, code in enumerate(["黔0201", "CODEXDOCCT-UNKNOWN"])]
            db.add_all(self.records)
            await db.commit()
            self.saved = copy.deepcopy(self.records[0].data)
        app = FastAPI()
        app.include_router(router)
        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            self.assertEqual(await connection.scalar(text("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='business_records'")), 0)
        await self.engine.dispose()

    async def test_api_detail_search_preserve_edit_values_and_unknown_is_local(self):
        response = await self.client.get(f"/api/v1/records/{self.records[0].id}")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        shell = await self.client.get(f"/api/v1/records/{self.records[0].id}/shell")
        self.assertEqual(shell.status_code, 200, shell.text)
        self.assertEqual(shell.json()["data"]["court_displays"], data["court_displays"])
        self.assertEqual(data["court_displays"]["first"]["name"], "六盘水钟山区人民法院")
        self.assertEqual(data["court_displays"]["second"]["name"], "六安市裕安区人民法院")
        self.assertEqual(data["court_displays"]["execution"]["status"], "resolved")
        self.assertEqual(data["court_displays"]["retrial"]["status"], "empty")
        for key in ("court", "first_court_name", "first_court_case_no", "second_court_name", "execution_court_name", "retrial_court_name"):
            self.assertEqual(data[key], self.saved[key])
        response = await self.client.post("/api/v1/cases/search", json={"scope": "company", "case_type": "民事争议"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 2)
        unknown = next(row for row in response.json()["items"] if row["id"] == self.records[1].id)
        state = unknown["data"]["court_displays"]["first"]
        self.assertEqual(state["status"], "unresolved")
        self.assertEqual(state["name"], "")
        self.assertEqual(state["raw"], "CODEXDOCCT-UNKNOWN")
        self.assertIn("无法解析", state["error"])
        async with self.sessions() as db:
            saved = await db.get(BusinessRecord, self.records[0].id)
            self.assertEqual(saved.data, self.saved)

    async def test_batch_queries_court_dictionary_once(self):
        statements = []
        def track(_connection, _cursor, statement, _parameters, _context, _many):
            if "system_parameters" in statement:
                statements.append(statement)
        event.listen(self.engine.sync_engine, "before_cursor_execute", track)
        try:
            async with self.sessions() as db:
                records = list((await db.scalars(select(BusinessRecord))).all())
                rows = await _contract_customer_record_dicts(records, None, db, self.identity)
                self.assertEqual(len(rows), 2)
            self.assertEqual(len(statements), 1)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", track)

    async def test_both_export_files_keep_23_columns_and_strict_error(self):
        for method, path, kwargs in [
            ("GET", f"/api/v1/cases/export/excel?ids={self.records[0].id}", {}),
            ("POST", "/api/v1/cases/export/excel", {"json": {"scope": "company", "case_type": "民事争议", "serial_no": "CODEXDOCCT-0", "page_size": 1}}),
        ]:
            response = await self.client.request(method, path, **kwargs)
            self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
            sheet = xlrd.open_workbook(file_contents=response.content).sheet_by_index(0)
            self.assertEqual(sheet.row_values(0), CIVIL_HEADERS)
            self.assertEqual((sheet.ncols, sheet.nrows), (23, 2))
            self.assertEqual(sheet.cell_value(1, 5), "六盘水钟山区人民法院")
            self.assertEqual(sheet.cell_value(1, 14), self.saved["first_court_case_no"])
        response = await self.client.get(f"/api/v1/cases/export/excel?ids={self.records[1].id}")
        self.assertEqual(response.status_code, 422)
        self.assertIn("CODEXDOCCT-UNKNOWN", response.json()["detail"])
        with self.assertRaises(HTTPException):
            _court_name("CODEXDOCCT-UNKNOWN", {}, "CODEXDOCCT-1")

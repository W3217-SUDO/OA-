"""Runtime contracts for legacy counsel advanced search conditions."""

import unittest
from datetime import date, datetime

import httpx
from fastapi import status
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, RolePermission, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "counsel-d10-admin", "role": "admin", "display_name": "顾问管理员", "department": "上海分所"}
USER = {"username": "counsel-d10-user", "role": "user", "display_name": "顾问员工", "department": "上海分所"}


class CounselAdvancedSearchD10Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sql_statements = []
        self._sql_listener = lambda conn, cursor, statement, parameters, context, executemany: self.sql_statements.append((statement, parameters))
        event.listen(self.engine.sync_engine, "before_cursor_execute", self._sql_listener)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="test", is_active=True),
                User(username=USER["username"], display_name=USER["display_name"], department=USER["department"], role="user", password_hash="test", is_active=True),
                RolePermission(role="admin", display_name="管理员", data_scope="公司", menu_keys=["case"], field_keys=[]),
                RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=["case"], field_keys=[]),
            ])
            rows = [
                BusinessRecord(
                    module="case", serial_no="COUNSEL-D10-A", title="顾问甲", customer="客户甲", status="进行中", owner=ADMIN["username"], department="上海分所",
                    data={"case_type": "法律顾问", "counsel_type": "常年", "counsel_start": "2025-01-01", "counsel_end": "2025-12-31", "handling_lawyers": ["alice"], "assistant": "助理甲", "assisted_response_user": "alice", "assisted_request_date": "2025-01-10", "assisted_response_date": "2025-02-01"},
                ),
                BusinessRecord(
                    module="case", serial_no="COUNSEL-D10-B", title="顾问乙", customer="客户乙", status="已结案", owner=ADMIN["username"], department="上海分所",
                    data={"case_type": "法律顾问", "counsel_type": "专项", "counsel_start": "2025-02-01", "counsel_end": "2025-06-30", "handling_lawyers": ["bob"], "assistant": "助理乙", "assisted_response_user": "bob", "assisted_request_date": "2025-04-10", "assisted_response_date": "2025-05-01"},
                ),
                BusinessRecord(
                    module="case", serial_no="COUNSEL-D10-C", title="顾问丙", customer="客户丙", status="进行中", owner=ADMIN["username"], department="上海分所",
                    data={"case_type": "法律顾问", "counsel_type": "专项", "counsel_start": "2025-03-01", "counsel_end": "2025-03-31", "handling_lawyers": ["carol"], "assistant": "助理丙", "assisted_response_user": "carol", "assisted_request_date": "2025-06-10", "assisted_response_date": ""},
                ),
            ]
            db.add_all(rows)
            await db.flush()
            db.add_all([
                BusinessRecord(module="finance", serial_no="FIN-D10-A", title="甲财务", customer="客户甲", status="已开票", owner=ADMIN["username"], department="上海分所", data={"case_id": rows[0].id, "case_no": rows[0].serial_no, "inform_date": "2025-01-05", "gained_date": "2025-03-01", "response_user": "alice", "bill_no": "B-001", "bill_status": "已开票", "bill_date": "2025-01-06", "fee_type_id": "F1"}),
                BusinessRecord(module="finance", serial_no="FIN-D10-B", title="乙财务", customer="客户乙", status="未开票", owner=ADMIN["username"], department="上海分所", data={"case_id": rows[1].id, "case_no": rows[1].serial_no, "inform_date": "2025-04-05", "gained_date": "2025-05-01", "response_user": "bob", "bill_no": "B-002", "bill_status": "未开票", "bill_date": "2025-04-06", "fee_type_id": "F2"}),
                BusinessRecord(module="finance", serial_no="FIN-D10-C", title="丙财务", customer="客户丙", status="待开票", owner=ADMIN["username"], department="上海分所", data={"case_id": rows[2].id, "case_no": rows[2].serial_no, "inform_date": "2025-06-05", "gained_date": "", "response_user": "carol", "bill_no": "B-003", "bill_status": "待开票", "bill_date": "2025-06-06", "fee_type_id": "F3"}),
            ])
            db.add_all([
                BusinessRecord(module="finance", serial_no=f"FIN-D10-UNRELATED-{index:03d}", title="无关财务", customer="其他客户", status="未开票", owner=ADMIN["username"], department="上海分所", data={"case_id": 900000 + index, "case_no": f"UNRELATED-{index:03d}", "bill_status": "未开票"})
                for index in range(200)
            ])
            db.add_all([
                FileAttachment(record_id=rows[0].id, category="证据材料", file_type_code="F1", original_name="甲文档.pdf", stored_name="d10-a.pdf", content_type="application/pdf", size=1, path="/tmp/d10-a.pdf", uploader="alice", document_date=date(2025, 1, 11), created_at=datetime(2025, 1, 11)),
                FileAttachment(record_id=rows[1].id, category="诉讼文书", file_type_code="F2", original_name="乙文档.pdf", stored_name="d10-b.pdf", content_type="application/pdf", size=1, path="/tmp/d10-b.pdf", uploader="bob", document_date=date(2025, 4, 11), created_at=datetime(2025, 4, 11)),
                FileAttachment(record_id=rows[2].id, category="调查文档", file_type_code="F3", original_name="丙文档.pdf", stored_name="d10-c.pdf", content_type="application/pdf", size=1, path="/tmp/d10-c.pdf", uploader="carol", document_date=date(2025, 6, 11), created_at=datetime(2025, 6, 11)),
            ])
            await db.commit()
            self.ids = {"A": rows[0].id, "B": rows[1].id, "C": rows[2].id}
        self.sql_statements.clear()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://counsel-d10.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        event.remove(self.engine.sync_engine, "before_cursor_execute", self._sql_listener)
        await self.engine.dispose()

    async def _search(self, payload):
        response = await self.client.post(f"{API}/cases/counsel/search", json=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        return response.json()

    async def test_assisted_user_include_exclude_and_union_logic(self):
        included = await self._search({"assisted_response_user": "alice"})
        self.assertEqual([item["serial_no"] for item in included["items"]], ["COUNSEL-D10-A"])
        excluded = await self._search({"assisted_response_user": "alice", "assisted_response_user_not": True})
        self.assertEqual({item["serial_no"] for item in excluded["items"]}, {"COUNSEL-D10-B", "COUNSEL-D10-C"})
        union = await self._search({"advanced_logic": "or", "assisted_response_user": "alice", "finance_bill_statuses": ["未开票"]})
        self.assertEqual({item["serial_no"] for item in union["items"]}, {"COUNSEL-D10-A", "COUNSEL-D10-B"})

    async def test_assisted_date_ranges_use_overlap_and_not_in(self):
        overlapped = await self._search({"assisted_request_date_from": "2025-01-05", "assisted_request_date_to": "2025-01-20"})
        self.assertEqual([item["serial_no"] for item in overlapped["items"]], ["COUNSEL-D10-A"])
        outside = await self._search({"assisted_request_date_from": "2025-01-05", "assisted_request_date_to": "2025-01-20", "assisted_request_date_not": True})
        self.assertEqual({item["serial_no"] for item in outside["items"]}, {"COUNSEL-D10-B", "COUNSEL-D10-C"})

    async def test_finance_fields_cover_dates_users_bill_status_and_fee_type(self):
        body = {"finance_inform_date_from": "2025-04-01", "finance_inform_date_to": "2025-04-30", "finance_response_user": "bob", "finance_bill_statuses": ["未开票"], "finance_fee_type_ids": ["F2"]}
        result = await self._search(body)
        self.assertEqual([item["serial_no"] for item in result["items"]], ["COUNSEL-D10-B"])
        finance_selects = [(sql.lower(), parameters) for sql, parameters in self.sql_statements if "select" in sql.lower() and "business_records" in sql.lower() and "module" in sql.lower()]
        linked_queries = [(sql, parameters) for sql, parameters in finance_selects if "json_extract" in sql and " in " in sql]
        self.assertTrue(linked_queries, finance_selects)
        linked_params = repr(linked_queries[-1][1]).lower()
        self.assertIn("case_id", linked_params)
        self.assertIn("case_no", linked_params)
        not_bill = await self._search({"finance_bill_no": "B-001", "finance_bill_no_not": True})
        self.assertEqual({item["serial_no"] for item in not_bill["items"]}, {"COUNSEL-D10-B", "COUNSEL-D10-C"})

    async def test_document_user_time_and_type_include_exclude(self):
        result = await self._search({"file_uploading_user": "bob", "file_uploading_time_from": "2025-04-01", "file_uploading_time_to": "2025-04-30", "file_type_ids": ["F2"]})
        self.assertEqual([item["serial_no"] for item in result["items"]], ["COUNSEL-D10-B"])
        not_type = await self._search({"file_type_ids": ["F1"], "file_type_not": True})
        self.assertEqual({item["serial_no"] for item in not_type["items"]}, {"COUNSEL-D10-B", "COUNSEL-D10-C"})

    async def test_invalid_range_and_paging_shape(self):
        invalid = await self.client.post(f"{API}/cases/counsel/search", json={"finance_bill_date_from": "2025-06-30", "finance_bill_date_to": "2025-06-01"})
        self.assertEqual(invalid.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        paged = await self._search({"page": 2, "page_size": 2})
        self.assertEqual((paged["total"], paged["page"], paged["page_size"], paged["pages"]), (3, 2, 2, 2))

    async def test_ordinary_search_filters_permissions_before_server_pagination(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(module="case", serial_no=f"ORD-D10-HIDDEN-{index:03d}", title="不可见普通案件", customer="客户", status="进行中", owner="other-user", department="上海分所", data={"case_type": "民事案件"})
                for index in range(100)
            ] + [
                BusinessRecord(module="case", serial_no=f"ORD-D10-VISIBLE-{index:03d}", title="可见普通案件", customer="客户", status="进行中", owner=USER["username"], department="上海分所", data={"case_type": "民事案件"})
                for index in range(5)
            ])
            await db.commit()
        app.dependency_overrides[current_identity] = lambda: USER
        first = await self.client.post(f"{API}/cases/search", json={"scope": "mine", "case_types": ["民事案件"], "page": 1, "page_size": 2})
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.text)
        self.assertEqual((first.json()["total"], first.json()["pages"]), (5, 3))
        self.assertEqual(len(first.json()["items"]), 2)
        self.assertTrue(all(item["owner"] == USER["username"] for item in first.json()["items"]))
        second = await self.client.post(f"{API}/cases/search", json={"scope": "mine", "case_types": ["民事案件"], "page": 3, "page_size": 2})
        self.assertEqual(len(second.json()["items"]), 1)


if __name__ == "__main__":
    unittest.main()

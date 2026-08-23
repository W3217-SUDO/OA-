"""Isolated runtime contracts for finance refund backend parity."""

import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractApprovalStep, FinanceTransaction, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "refund-admin", "role": "admin", "display_name": "退款管理员", "department": "上海分所"}
MANAGER = {"username": "refund-manager", "role": "manager", "display_name": "退款负责人", "department": "上海分所"}
USER = {"username": "refund-user", "role": "user", "display_name": "退款员工", "department": "上海分所"}
EXCEL_NS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def parse_excel_rows(response):
    """Parse the SpreadsheetML .xls response and return cell text rows."""
    assert "application/vnd.ms-excel" in response.headers.get("content-type", "")
    disposition = response.headers.get("content-disposition", "")
    assert ".xls" in disposition.lower()
    root = ElementTree.fromstring(response.content)
    rows = []
    for row in root.findall(f".//{EXCEL_NS}Row"):
        rows.append([cell.text or "" for cell in row.findall(f"{EXCEL_NS}Cell/{EXCEL_NS}Data")])
    return rows


class FinanceRefundBackendD7Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [User.__table__, RolePermission.__table__, BusinessRecord.__table__, WorkflowEvent.__table__, FinanceTransaction.__table__, ContractApprovalStep.__table__]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
        async with self.sessions() as db:
            db.add_all([
                User(username="refund-admin", display_name="退款管理员", department="上海分所", role="admin", password_hash="test", is_active=True),
                User(username="refund-manager", display_name="退款负责人", department="上海分所", role="manager", password_hash="test", is_active=True),
                User(username="refund-user", display_name="退款员工", department="上海分所", role="user", password_hash="test", is_active=True),
            ])
            fee = BusinessRecord(module="finance", serial_no="FEE-D7-001", title="D7 官方费用", customer="D7 客户", status="已付款", owner="refund-user", department="上海分所", data={"amount": 150, "fee_type": "官方费用", "case_no": "CASE-D7", "group_id": "lawfirm"})
            db.add(fee)
            await db.flush()
            refunds = [
                BusinessRecord(module="refund", serial_no="RF-D7-001", title="D7 退款一", customer="D7 客户", status="草稿", owner="refund-user", department="上海分所", data={"amount": 80, "case_no": "CASE-D7", "court": "上海法院", "original_payment_no": "PAY-D7-1", "expected_date": "2026-08-20", "fee_record_id": fee.id, "group_id": "lawfirm", "applicant": "退款申请人", "refund_account_name": "退款账户", "refund_bank": "测试银行", "refund_account": "6222000000000001", "remark": "可退款"}),
                BusinessRecord(module="refund", serial_no="RF-D7-002", title="D7 退款二", customer="D7 客户二", status="待审批", owner="refund-manager", department="上海分所", data={"amount": 40, "case_no": "CASE-D7-2", "court": "上海法院", "original_payment_no": "PAY-D7-2", "fee_record_id": fee.id, "group_id": "trad"}),
                BusinessRecord(module="refund", serial_no="RF-D7-003", title="D7 退款三", customer="D7 客户三", status="已退款", owner="refund-user", department="北京分所", data={"amount": 25, "case_no": "CASE-D7-3", "court": "北京法院", "original_payment_no": "PAY-D7-3", "group_id": "lawfirm", "actual_date": "2026-08-01", "refund_voucher_no": "V-D7-3"}),
            ]
            db.add_all(refunds)
            await db.flush()
            self.refund_ids = [item.id for item in refunds]
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://refund-d7.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_refund_list_defaults_fifteen_and_filters_scope_status_group(self):
        for index in range(4, 19):
            async with self.sessions() as db:
                db.add(BusinessRecord(module="refund", serial_no=f"RF-D7-{index:03d}", title=f"D7 退款{index}", customer="D7 客户", status="草稿", owner="refund-user", department="上海分所", data={"amount": index, "group_id": "lawfirm", "case_no": f"CASE-D7-{index}"}))
                await db.commit()
        response = await self.client.get(f"{API}/finance/refunds/query")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual((response.json()["page"], response.json()["page_size"]), (1, 15))
        self.assertEqual(response.json()["total"], 17)
        self.assertNotIn("RF-D7-003", {row["serial_no"] for row in response.json()["items"]})
        for page_size in (10, 15, 20, 50, 100, 200):
            bounded = await self.client.get(f"{API}/finance/refunds/query", params={"page_size": page_size})
            self.assertEqual(bounded.status_code, status.HTTP_200_OK)
            self.assertEqual(bounded.json()["page_size"], page_size)
        self.assertEqual((await self.client.get(f"{API}/finance/refunds/query", params={"page_size": 11})).status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        filtered = await self.client.get(f"{API}/finance/refunds/query", params={"status": "草稿", "group": "lawfirm", "scope": "company", "page_size": 10})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertTrue(all(row["status"] == "草稿" and row["data"].get("group_id") == "lawfirm" for row in filtered.json()["items"]))
        app.dependency_overrides[current_identity] = lambda: MANAGER
        mine = await self.client.get(f"{API}/finance/refunds/query", params={"scope": "mine"})
        self.assertEqual(mine.status_code, status.HTTP_200_OK)
        self.assertTrue(all(row["owner"] == "refund-manager" for row in mine.json()["items"]))
        app.dependency_overrides[current_identity] = lambda: ADMIN

    async def test_refund_full_export_applies_filter_and_business_columns(self):
        response = await self.client.get(f"{API}/finance/refunds/export", params={"status": "待审批", "group": "trad"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = parse_excel_rows(response)
        self.assertEqual(rows[0], ["申请编号", "案号", "客户", "法院", "原缴费票号", "退款金额", "状态", "预计到账", "实际到账", "退款凭证号"])
        self.assertEqual(len(rows), 2)
        self.assertIn("RF-D7-002", rows[1])
        self.assertNotIn("RF-D7-001", rows[1])
        self.assertNotIn("扩展数据", rows[0])

    async def test_refund_selected_export_is_scoped_to_ids(self):
        response = await self.client.get(f"{API}/finance/refunds/export-selected", params={"ids": ",".join(str(value) for value in self.refund_ids[:2])})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = parse_excel_rows(response)
        self.assertEqual({row[0] for row in rows[1:]}, {"RF-D7-001", "RF-D7-002"})
        self.assertNotIn("RF-D7-003", {row[0] for row in rows[1:]})
        missing = await self.client.get(f"{API}/finance/refunds/export-selected", params={"ids": "999999"})
        self.assertEqual(missing.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    async def test_refund_export_workbook_is_not_csv(self):
        response = await self.client.get(f"{API}/finance/refunds/export")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.lstrip().startswith(b"<?xml"))
        self.assertNotIn(b"text/csv", response.headers.get("content-type", "").encode())
        self.assertGreaterEqual(len(parse_excel_rows(response)), 2)

    async def test_refund_company_boundary_also_blocks_direct_mutations(self):
        selected = await self.client.get(
            f"{API}/finance/refunds/export-selected",
            params={"ids": str(self.refund_ids[2])},
        )
        self.assertEqual(selected.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        amount = await self.client.patch(
            f"{API}/finance/refunds/{self.refund_ids[2]}/amount",
            json={"amount": 1},
        )
        self.assertEqual(amount.status_code, status.HTTP_404_NOT_FOUND)
        progress = await self.client.post(
            f"{API}/finance/refunds/status",
            json={"ids": [self.refund_ids[2]], "status": "待审批"},
        )
        self.assertEqual(progress.status_code, status.HTTP_404_NOT_FOUND)

    async def test_refund_amount_update_validates_and_audits(self):
        response = await self.client.patch(f"{API}/finance/refunds/{self.refund_ids[0]}/amount", json={"amount": 120, "comment": "调整退款金额"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["amount"], 120)
        invalid = await self.client.patch(f"{API}/finance/refunds/{self.refund_ids[0]}/amount", json={"amount": 0})
        self.assertEqual(invalid.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        locked = await self.client.patch(f"{API}/finance/refunds/{self.refund_ids[1]}/amount", json={"amount": 10})
        self.assertEqual(locked.status_code, status.HTTP_409_CONFLICT)
        async with self.sessions() as db:
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.refund_ids[0], WorkflowEvent.action == "修改退款金额"))
        self.assertIsNotNone(event)

    async def test_refund_batch_status_preflight_is_atomic(self):
        response = await self.client.post(f"{API}/finance/refunds/status", json={"ids": self.refund_ids[:2], "status": "退款办理中", "comment": "批量办理"})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        async with self.sessions() as db:
            rows = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "refund", BusinessRecord.id.in_(self.refund_ids[:2])))).all())
        self.assertEqual({row.status for row in rows}, {"草稿", "待审批"})
        ok = await self.client.post(f"{API}/finance/refunds/status", json={"ids": [self.refund_ids[0]], "status": "待审批", "comment": "批量提交"})
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

    async def test_refund_flow_permissions_and_actual_receipt_are_audited(self):
        app.dependency_overrides[current_identity] = lambda: USER
        forbidden = await self.client.post(f"{API}/finance/refunds/{self.refund_ids[1]}/review", json={"approved": True, "comment": "越权"})
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        app.dependency_overrides[current_identity] = lambda: ADMIN
        denied = await self.client.post(f"{API}/finance/refunds/{self.refund_ids[0]}/review", json={"approved": True, "comment": "越权"})
        self.assertEqual(denied.status_code, status.HTTP_409_CONFLICT)
        submitted = await self.client.post(f"{API}/finance/refunds/{self.refund_ids[0]}/submit", json={"comment": "提交"})
        self.assertEqual(submitted.status_code, status.HTTP_200_OK)
        app.dependency_overrides[current_identity] = lambda: MANAGER
        reviewed = await self.client.post(f"{API}/finance/refunds/{self.refund_ids[0]}/review", json={"approved": True, "comment": "审核通过"})
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        completed = await self.client.post(f"{API}/finance/refunds/{self.refund_ids[0]}/complete", json={"actual_date": "2026-08-03", "voucher_no": "V-D7-1", "comment": "到账"})
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.assertEqual(completed.json()["status"], "已退款")
        async with self.sessions() as db:
            tx = await db.scalar(select(FinanceTransaction).where(FinanceTransaction.finance_record_id == self.refund_ids[0], FinanceTransaction.transaction_type == "退费"))
        self.assertIsNotNone(tx)


if __name__ == "__main__":
    unittest.main()

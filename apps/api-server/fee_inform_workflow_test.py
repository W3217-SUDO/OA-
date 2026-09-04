"""Isolated fee-notice lifecycle: independent notice, receipt, bill and guards."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "fee-inform-admin", "role": "admin", "display_name": "费用通知管理员", "department": "财务部"}
OTHER = {"username": "fee-inform-other", "role": "auditor", "display_name": "无权用户", "department": "财务部"}


class FeeInformWorkflowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.upload_dir = tempfile.TemporaryDirectory()
        self.previous_upload_root = main_module.UPLOAD_ROOT
        main_module.UPLOAD_ROOT = Path(self.upload_dir.name)
        async with self.sessions() as db:
            db.add_all([User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True), User(username=OTHER["username"], display_name=OTHER["display_name"], department=OTHER["department"], role="user", password_hash="x", is_active=True)])
            customer = BusinessRecord(module="customer", serial_no="CODEX-FEE-INFORM-C", title="通知客户", customer="通知客户", status="active", owner=ADMIN["username"], department=ADMIN["department"])
            contract = BusinessRecord(module="contract", serial_no="CODEX-FEE-INFORM-CT", title="通知合同", customer=customer.title, status="approved", owner=ADMIN["username"], department=ADMIN["department"])
            db.add_all([customer, contract]); await db.flush()
            case = BusinessRecord(module="case", serial_no="CODEX-FEE-INFORM-CASE", title="通知案件", customer=customer.title, status="进行中", owner=ADMIN["username"], department=ADMIN["department"])
            other_case = BusinessRecord(module="case", serial_no="CODEX-FEE-INFORM-OTHER", title="异案", customer=customer.title, status="进行中", owner=ADMIN["username"], department=ADMIN["department"])
            db.add_all([case, other_case]); await db.flush()
            def fee(serial: str, case_id: int) -> BusinessRecord:
                return BusinessRecord(module="finance", serial_no=serial, title="案件费用", customer=customer.title, status="草稿", owner=ADMIN["username"], department=ADMIN["department"], data={"amount": 100, "fee_type": "官方费用", "case_id": case_id, "case_no": case.serial_no if case_id == case.id else other_case.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no})
            first, second, third, cross = fee("CODEX-FEE-INFORM-1", case.id), fee("CODEX-FEE-INFORM-2", case.id), fee("CODEX-FEE-INFORM-3", case.id), fee("CODEX-FEE-INFORM-X", other_case.id)
            db.add_all([first, second, third, cross]); await db.commit()
            self.fee_id, self.link_ids, self.cross_id = first.id, [second.id, third.id], cross.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fee-inform.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides)
        main_module.UPLOAD_ROOT = self.previous_upload_root; self.upload_dir.cleanup(); await self.engine.dispose()

    async def test_notice_arrival_bill_unlock_and_guards(self) -> None:
        created = await self.client.post(f"{API}/finance/fees/{self.fee_id}/informs", json={"inform_date": "2026-09-05"})
        self.assertEqual(created.status_code, 201, created.text); notice_id = created.json()["id"]
        self.assertNotEqual(notice_id, self.fee_id)
        self.assertEqual((await self.client.post(f"{API}/finance/fees/{self.fee_id}/informs", json={"inform_date": "2026-09-05"})).status_code, 409)
        forged = await self.client.post(f"{API}/records", json={"module": "finance_fee_inform", "serial_no": "CODEX-FORGED", "title": "伪造通知"})
        self.assertEqual(forged.status_code, 422, forged.text)
        app.dependency_overrides[current_identity] = lambda: OTHER
        denied = await self.client.post(f"{API}/finance/fee-informs/{notice_id}/arrival", json={"receivable_amount": 100, "received_amount": 100, "received_date": "2026-09-05"})
        self.assertEqual(denied.status_code, 403, denied.text)
        app.dependency_overrides[current_identity] = lambda: ADMIN
        mismatch = await self.client.post(f"{API}/finance/fee-informs/{notice_id}/arrival", json={"receivable_amount": 100, "received_amount": 99, "received_date": "2026-09-05"})
        self.assertEqual(mismatch.status_code, 422, mismatch.text)
        arrived = await self.client.post(f"{API}/finance/fee-informs/{notice_id}/arrival", json={"receivable_amount": 100, "received_amount": 100, "received_date": "2026-09-05"})
        self.assertEqual(arrived.status_code, 200, arrived.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id); receipt = await db.scalar(__import__("sqlalchemy").select(IncomingPayment))
            self.assertEqual(fee.data["received_amount"], 100); self.assertEqual(fee.data["incoming_payment_id"], receipt.id)
        repeated = await self.client.post(f"{API}/finance/fee-informs/{notice_id}/arrival", json={"receivable_amount": 100, "received_amount": 100, "received_date": "2026-09-05"})
        self.assertEqual(repeated.status_code, 409, repeated.text)
        bill = await self.client.post(f"{API}/finance/fee-informs/{notice_id}/bill", data={"bill_no": "CODEX-BILL", "bill_amount": "100", "bill_date": "2026-09-05"}, files={"file": ("receipt.pdf", b"%PDF-test", "application/pdf")})
        self.assertEqual(bill.status_code, 201, bill.text)
        downloaded = await self.client.get(f"{API}/finance/fee-informs/{notice_id}/bill/download")
        self.assertEqual(downloaded.status_code, 200); self.assertEqual(downloaded.content, b"%PDF-test")
        self.assertEqual((await self.client.post(f"{API}/finance/fee-informs/{notice_id}/unlock")).status_code, 200)
        replacement = await self.client.post(f"{API}/finance/fee-informs/{notice_id}/bill", data={"bill_no": "CODEX-BILL-2", "bill_amount": "100", "bill_date": "2026-09-05"}, files={"file": ("receipt.pdf", b"%PDF-replacement", "application/pdf")})
        self.assertEqual(replacement.status_code, 201, replacement.text)
        self.assertEqual((await self.client.post(f"{API}/finance/fee-informs/{notice_id}/links", json={"fee_ids": self.link_ids})).status_code, 200)
        self.assertEqual((await self.client.post(f"{API}/finance/fee-informs/{notice_id}/links", json={"fee_ids": [self.link_ids[0], self.link_ids[0]]})).status_code, 422)
        self.assertEqual((await self.client.post(f"{API}/finance/fee-informs/{notice_id}/links", json={"fee_ids": [self.link_ids[0], self.cross_id]})).status_code, 409)


if __name__ == "__main__":
    unittest.main()

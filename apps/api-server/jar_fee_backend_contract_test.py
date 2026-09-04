import tempfile
import unittest
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
import app.main as main_module
from app.models import BusinessRecord, FileAttachment, JarFeeAuditLog, RolePermission, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "jar-admin", "role": "admin", "display_name": "JAR Admin", "department": "Finance"}


class JarFeeBackendContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name=ADMIN["display_name"], department="Finance", role="admin", password_hash="x", is_active=True))
            contract = BusinessRecord(module="contract", serial_no="CODEX-JAR-CONTRACT", title="JAR contract", customer="JAR customer", status="审批通过", owner=ADMIN["username"], department="Finance", data={})
            db.add(contract); await db.commit(); await db.refresh(contract); self.contract_id = contract.id
        async def override_db():
            async with self.sessions() as db:
                yield db
        self.identity = dict(ADMIN)
        self.previous = dict(app.dependency_overrides); app.dependency_overrides[get_db] = override_db; app.dependency_overrides[current_identity] = lambda: self.identity
        self.upload_dir = tempfile.TemporaryDirectory(); self.previous_upload_root = main_module.UPLOAD_ROOT; main_module.UPLOAD_ROOT = Path(self.upload_dir.name)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://jar.test")

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous); main_module.UPLOAD_ROOT = self.previous_upload_root; self.upload_dir.cleanup(); await self.engine.dispose()

    def payload(self):
        return {"contract_id": self.contract_id, "title": "CODEX-JAR-FEE", "amount": 100, "official_fee_amount": 20, "agency_fee_amount": 30, "other_fee_amount": 10, "handler": "display-only", "bank_voucher_no": "CODEX-VOUCHER"}

    async def test_crud_status_files_audit_and_cleanup(self):
        invalid = self.payload(); invalid["other_fee_amount"] = 60
        response = await self.client.post(f"{API}/finance/jar-fees", json=invalid); self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.post(f"{API}/finance/jar-fees", json=self.payload()); self.assertEqual(response.status_code, 201, response.text)
        jar = response.json(); self.assertEqual(jar["owner"], ADMIN["username"]); self.assertEqual(jar["status"], "待确认")
        jar_id = jar["id"]
        response = await self.client.post(f"{API}/records", json={"module": "jar_fee", "serial_no": "CODEX-BYPASS", "title": "bypass", "status": "待确认", "owner": ADMIN["username"], "department": "Finance", "data": {}}); self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.get(f"{API}/finance/jar-fees?contract_id="); self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["items"][0]["capabilities"]["can_update"])
        response = await self.client.post(f"{API}/attachments", data={"record_id": str(jar_id)}, files={"file": ("bypass.pdf", b"x", "application/pdf")}); self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.post(f"{API}/finance/jar-fees/{jar_id}/files", files={"file": ("CODEX-JAR.pdf", b"file", "application/pdf")}); self.assertEqual(response.status_code, 201, response.text)
        attachment_id = response.json()["id"]
        response = await self.client.post(f"{API}/finance/jar-fees/{jar_id}/status", json={"status": "已确认"}); self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.put(f"{API}/finance/jar-fees/{jar_id}", json=self.payload()); self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.post(f"{API}/finance/jar-fees/{jar_id}/status", json={"status": "已入账"}); self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.post(f"{API}/finance/jar-fees/{jar_id}/status", json={"status": "已作废"}); self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.get(f"{API}/finance/jar-fees/{jar_id}/files/{attachment_id}/download"); self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.get(f"{API}/finance/jar-fees/export"); self.assertEqual(response.status_code, 200, response.text); self.assertIn("银行单据号", response.content.decode("utf-8-sig"))
        async with self.sessions() as db:
            logs = list((await db.scalars(select(JarFeeAuditLog).where(JarFeeAuditLog.jar_fee_record_id == jar_id))).all()); self.assertGreaterEqual(len(logs), 3)

    async def test_non_finance_jar_permission_is_denied(self):
        self.identity = {"username": "jar-user", "role": "user", "permission_role": "NoJar", "display_name": "JAR User", "department": "Finance"}
        async with self.sessions() as db:
            db.add(User(username="jar-user", display_name="JAR User", department="Finance", role="user", password_hash="x", is_active=True, profile={"permission_overrides": {"menu_keys": []}})); await db.commit()
        response = await self.client.get(f"{API}/finance/jar-fees")
        self.assertEqual(response.status_code, 403, response.text)

    async def test_draft_update_file_delete_and_record_delete_keep_audit(self):
        response = await self.client.post(f"{API}/finance/jar-fees", json=self.payload()); self.assertEqual(response.status_code, 201, response.text)
        jar_id = response.json()["id"]; serial_no = response.json()["serial_no"]
        changed = self.payload(); changed["title"] = "CODEX-JAR-UPDATED"; changed["amount"] = 120
        response = await self.client.put(f"{API}/finance/jar-fees/{jar_id}", json=changed); self.assertEqual(response.status_code, 200, response.text); self.assertEqual(response.json()["title"], "CODEX-JAR-UPDATED")
        response = await self.client.get(f"{API}/finance/jar-fees/{jar_id}"); self.assertEqual(response.status_code, 200, response.text); self.assertEqual(response.json()["amount"], 120)
        response = await self.client.post(f"{API}/finance/jar-fees/{jar_id}/files", files={"file": ("CODEX-CLEAN.pdf", b"temporary", "application/pdf")}); self.assertEqual(response.status_code, 201, response.text)
        attachment_id = response.json()["id"]
        async with self.sessions() as db:
            attachment = await db.get(FileAttachment, attachment_id); path = Path(attachment.path)
        response = await self.client.delete(f"{API}/finance/jar-fees/{jar_id}/files/{attachment_id}"); self.assertEqual(response.status_code, 204, response.text); self.assertFalse(path.exists())
        response = await self.client.delete(f"{API}/finance/jar-fees/{jar_id}"); self.assertEqual(response.status_code, 204, response.text)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(BusinessRecord, jar_id)); self.assertIsNotNone(await db.scalar(select(JarFeeAuditLog.id).where(JarFeeAuditLog.jar_fee_serial_no == serial_no, JarFeeAuditLog.action == "删除交案费")))

    async def test_scoped_user_cannot_read_other_fee_and_amounts_are_masked(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="jar-user", display_name="JAR User", department="Finance", role="user", password_hash="x", is_active=True),
                RolePermission(role="user", display_name="User", data_scope="本人及共享数据", menu_keys=["finance-jar"], field_keys=[]),
                BusinessRecord(module="jar_fee", serial_no="CODEX-JAR-OWN", title="own", customer="JAR customer", status="待确认", owner="jar-user", department="Finance", data={"amount": 9, "official_fee_amount": 2, "agency_fee_amount": 3, "other_fee_amount": 1}),
                BusinessRecord(module="jar_fee", serial_no="CODEX-JAR-OTHER", title="other", customer="JAR customer", status="待确认", owner="jar-admin", department="Finance", data={"amount": 9}),
            ]); await db.commit()
        self.identity = {"username": "jar-user", "role": "user", "display_name": "JAR User", "department": "Finance"}
        response = await self.client.get(f"{API}/finance/jar-fees"); self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["items"]; self.assertEqual(len(items), 1); self.assertIsNone(items[0]["amount"]); self.assertIsNone(items[0]["official_fee_amount"])
        for key in ("amount", "official_fee_amount", "agency_fee_amount", "other_fee_amount"): self.assertNotIn(key, items[0]["data"])
        async with self.sessions() as db:
            other_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-JAR-OTHER"))
        response = await self.client.get(f"{API}/finance/jar-fees/{other_id}"); self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()

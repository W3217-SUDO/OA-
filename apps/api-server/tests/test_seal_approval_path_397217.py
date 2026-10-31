"""BUG20261031002 第④⑤步：合同审批与用印合并，按部门审批路径（本部门负责人 → 所里审批人 → 行政用印）。"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.hr import router as hr_router
from app.areas.legal import seals as seal_router
from app.core import soft_delete
from app.core.dependencies import current_identity, get_db
from app.core.documents import _seal_authorization_context
from app.core.permissions import _seal_application_capabilities
from app.core.seal_approval import (
    FIRM_APPROVER_MISSING, approval_path_preview, contract_attachment_fingerprint, contract_unchanged_since_approval,
    save_seal_approval_settings,
)
from app.database import Base
from app.models import BusinessRecord, Department, FileAttachment, User

ADMIN = {"username": "sealadmin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "管理员", "department": "诉讼一部", "action_keys": ["*"]}


def person(username, department="诉讼一部"):
    return {"username": username, "role": "staff", "role_ids": [], "_actual_role_ids": [], "display_name": username,
            "department": department, "action_keys": []}


class SealApprovalPathTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            for username in ("sealadmin", "head", "firm", "partner", "clerk", "stamper", "other"):
                db.add(User(username=username, display_name=username, password_hash="isolated-only", department="诉讼一部",
                            role="admin" if username == "sealadmin" else "staff"))
            db.add(Department(code="SS1", name="诉讼一部", manager="head"))
            db.add(Department(code="SS2", name="诉讼二部", manager=""))
            await db.commit()
        self.identity = dict(ADMIN)
        app = FastAPI()
        app.include_router(hr_router.router)
        app.include_router(seal_router.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(self.identity)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _settings(self, **value):
        async with self.sessions() as db:
            await save_seal_approval_settings(value, "sealadmin", db)
            await db.commit()

    async def test_path_needs_firm_approver_and_skips_missing_head_or_self(self):
        async with self.sessions() as db:
            self.assertEqual((await approval_path_preview("诉讼一部", "clerk", db))["error"], FIRM_APPROVER_MISSING)
        await self._settings(firm_approver="firm")
        async with self.sessions() as db:
            self.assertEqual((await approval_path_preview("诉讼一部", "clerk", db))["path"], ["head", "firm"])
            self.assertEqual((await approval_path_preview("诉讼一部", "head", db))["path"], ["firm"])
            self.assertEqual((await approval_path_preview("诉讼二部", "clerk", db))["path"], ["firm"])

    async def test_department_can_replace_a_step(self):
        async with self.sessions() as db:
            dept_id = await db.scalar(select(Department.id).where(Department.name == "诉讼一部"))
        await self._settings(firm_approver="firm", department_paths={str(dept_id): ["partner", ""]})
        async with self.sessions() as db:
            self.assertEqual((await approval_path_preview("诉讼一部", "clerk", db))["path"], ["partner", "firm"])

    async def test_settings_api_admin_only_and_rejects_unknown_people(self):
        response = await self.client.put("/api/v1/hr/seal-approval-settings", json={"firm_approver": "nobody"})
        self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.put("/api/v1/hr/seal-approval-settings", json={"firm_approver": "firm", "stamp_users": ["stamper"]})
        self.assertEqual(response.status_code, 200, response.text)
        rows = {row["department"]: row for row in response.json()["departments"]}
        self.assertEqual((rows["诉讼一部"]["first"], rows["诉讼一部"]["second"]), ("head", "firm"))
        self.identity = person("clerk")
        self.assertEqual((await self.client.get("/api/v1/hr/seal-approval-settings")).status_code, 403)
        preview = await self.client.get("/api/v1/seals/approval-path")
        self.assertEqual(preview.json()["path"], ["head", "firm"])

    async def test_standalone_seal_goes_through_each_step_then_to_stamp(self):
        await self._settings(firm_approver="firm")
        async with self.sessions() as db:
            seal = BusinessRecord(module="seal", serial_no="P1", title="单独用印", owner="clerk", department="诉讼一部", status="草稿", data={})
            db.add(seal); await db.flush()
            db.add(FileAttachment(record_id=seal.id, category="用印文件", original_name="a.pdf", stored_name="a.pdf", path="/tmp/a.pdf", size=1, uploader="clerk"))
            await db.commit()
            seal_id = seal.id
        submitted = await self.client.post(f"/api/v1/seals/applications/{seal_id}/submit", json={"comment": ""})
        self.assertEqual(submitted.status_code, 200, submitted.text)
        async with self.sessions() as db:
            seal = await db.get(BusinessRecord, seal_id)
            self.assertEqual((seal.status, seal.data["approver"]), ("待审批", "head"))
            capabilities = await _seal_application_capabilities(seal, person("firm"), db)
            self.assertFalse(capabilities["approve"])
        self.identity = person("head")
        first = await self.client.post(f"/api/v1/seals/applications/{seal_id}/approve", json={"approved": True, "comment": "同意"})
        self.assertEqual(first.status_code, 200, first.text)
        async with self.sessions() as db:
            seal = await db.get(BusinessRecord, seal_id)
            self.assertEqual((seal.status, seal.data["approver"]), ("待审批", "firm"))
        self.identity = person("firm")
        second = await self.client.post(f"/api/v1/seals/applications/{seal_id}/approve", json={"approved": True, "comment": "同意"})
        self.assertEqual(second.status_code, 200, second.text)
        async with self.sessions() as db:
            seal = await db.get(BusinessRecord, seal_id)
            self.assertEqual(seal.status, "待用印")
            self.assertEqual([step["status"] for step in seal.data["approval_steps"]], ["已通过", "已通过"])

    async def test_configured_stamp_users_are_the_only_stampers(self):
        async with self.sessions() as db:
            self.assertTrue((await _seal_authorization_context(dict(ADMIN), db))["stamp"])
        await self._settings(firm_approver="firm", stamp_users=["stamper"])
        async with self.sessions() as db:
            self.assertFalse((await _seal_authorization_context(dict(ADMIN), db))["stamp"])
            self.assertTrue((await _seal_authorization_context(person("stamper"), db))["stamp"])

    async def test_contract_unchanged_since_approval_by_attachment_fingerprint(self):
        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="HT1", title="合同", owner="clerk", department="诉讼一部", status="审批通过", data={})
            db.add(contract); await db.flush()
            db.add(FileAttachment(record_id=contract.id, category="合同附件", original_name="c.pdf", stored_name="c.pdf", path="/tmp/c.pdf", size=2, uploader="clerk"))
            await db.flush()
            contract.data = {"approved_attachment_fingerprint": await contract_attachment_fingerprint(contract.id, db)}
            self.assertTrue(await contract_unchanged_since_approval(contract, db))
            db.add(FileAttachment(record_id=contract.id, category="合同附件", original_name="d.pdf", stored_name="d.pdf", path="/tmp/d.pdf", size=3, uploader="clerk"))
            await db.flush()
            self.assertFalse(await contract_unchanged_since_approval(contract, db))


if __name__ == "__main__":
    unittest.main()

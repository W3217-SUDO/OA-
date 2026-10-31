"""BUG20261030012（范文玲 2026-10-30）：合同变更后走合同审批；审批中不影响合同其他操作；去掉“通过/驳回合同变更”。"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.contract import router as contract_router
from app.core import soft_delete
from app.core.dependencies import current_identity, get_db
from app.core.permissions import _require_contract_attachment_write_access
from app.database import Base
from app.models import BusinessRecord, ContractApprovalStep, SystemConfig, User

ADMIN = {"username": "CODEXCCADMIN", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "变更测试管理员", "department": "CODEXCC", "action_keys": ["*"]}
API = "/api/v1/contracts"


class ContractChangeReapprovalTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name="变更测试管理员", password_hash="isolated-only", department="CODEXCC", role="admin"))
            db.add(User(username="codexapprover", display_name="审批人甲", password_hash="isolated-only", department="CODEXCC", role="staff",
                        profile={"contract_approval_enabled": True}))
            db.add(BusinessRecord(module="hr", serial_no="HR-CC-1", title="审批人甲", owner="codexapprover", department="CODEXCC", status="在职", data={"username": "codexapprover"}))
            for serial, status in (("HT-CC-APPROVED", "审批通过"), ("HT-CC-PENDING", "审批中")):
                db.add(BusinessRecord(module="contract", serial_no=serial, title=serial, customer="客户", owner=ADMIN["username"],
                                      department="CODEXCC", status=status, data={"amount": 100, "type": "其他", "current_approver": "codexapprover"}))
            await db.commit()
        app = FastAPI()
        app.include_router(contract_router.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ADMIN)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _contract(self, serial):
        async with self.sessions() as db:
            return await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == serial))

    async def test_approved_contract_change_goes_back_to_approval(self):
        contract = await self._contract("HT-CC-APPROVED")
        # BUG20261031002：合同变更走部门审批路径；所里审批人没设置时不能提交。
        missing = await self.client.post(f"{API}/{contract.id}/changes", json={"change_type": "金额调整", "reason": "调整金额", "amount": 200})
        self.assertEqual(missing.status_code, 422, missing.text)
        async with self.sessions() as db:
            db.add(SystemConfig(key="seal_approval_settings", label="用印审批设置", value={"firm_approver": "codexapprover"}))
            await db.commit()
        changed = await self.client.post(f"{API}/{contract.id}/changes", json={
            "change_type": "金额调整", "reason": "调整金额", "amount": 200})
        self.assertEqual(changed.status_code, 201, changed.text)
        self.assertTrue(changed.json()["resubmitted_for_approval"])
        contract = await self._contract("HT-CC-APPROVED")
        self.assertEqual((contract.status, contract.data["amount"], contract.data["current_approver"]), ("审批中", 200, "codexapprover"))
        async with self.sessions() as db:
            steps = (await db.scalars(select(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id))).all()
            self.assertEqual([(s.approver, s.status) for s in steps], [("codexapprover", "待审批")])
            # 审批中不挡附件。
            await _require_contract_attachment_write_access(contract, dict(ADMIN), db)

    async def test_pending_contract_change_updates_same_approval(self):
        contract = await self._contract("HT-CC-PENDING")
        changed = await self.client.post(f"{API}/{contract.id}/changes", json={"change_type": "金额调整", "reason": "调整金额", "amount": 300})
        self.assertEqual(changed.status_code, 201, changed.text)
        self.assertFalse(changed.json()["resubmitted_for_approval"])
        contract = await self._contract("HT-CC-PENDING")
        self.assertEqual((contract.status, contract.data["amount"]), ("审批中", 300))

    async def test_change_review_endpoint_removed(self):
        contract = await self._contract("HT-CC-PENDING")
        response = await self.client.post(f"{API}/{contract.id}/changes/review", json={"approved": True})
        self.assertEqual(response.status_code, 410)


if __name__ == "__main__":
    unittest.main()

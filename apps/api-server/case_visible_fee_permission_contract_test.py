import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "fee-admin", "role": "admin", "display_name": "费用管理员", "department": "总部"}
VIEWER = {"username": "fee-viewer", "role": "user", "display_name": "可见案件用户", "department": "诉讼部"}
OUTSIDER = {"username": "fee-outsider", "role": "user", "display_name": "不可见案件用户", "department": "知产部"}


class CaseVisibleFeePermissionContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=item["username"], display_name=item["display_name"], department=item["department"], role=item["role"], password_hash="x", is_active=True)
                for item in (ADMIN, VIEWER, OUTSIDER)
            ])
            case = BusinessRecord(
                module="case",
                serial_no="CODEX-VISIBLE-FEE-CASE",
                title="可见案件费用权限测试",
                customer="测试客户",
                status="待立案审批",
                owner="case-owner",
                department=VIEWER["department"],
                data={
                    "case_type": "民事争议",
                    "case_creation_step": "completed",
                    "shared_to": [VIEWER["username"]],
                },
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)
            self.case_id = case.id
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-VISIBLE-FEE-CONTRACT",
                title="可见案件律所合同", customer=case.customer, status="审批通过",
                owner=VIEWER["username"], department=VIEWER["department"], data={"contract_body": "律所"},
            )
            db.add(contract); await db.commit(); await db.refresh(contract)
            self.contract_id = contract.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.identity = VIEWER
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://visible-fee.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    def fee_payload(self) -> dict:
        return {
            "title": "CODEX 可见案件测试费用",
            "customer": "测试客户",
            "amount": 1.0,
            "fee_type": "官方费用",
            "expense_scope": "律所",
            "expense_subtype": "诉讼费",
            "case_no": "CODEX-VISIBLE-FEE-CASE",
            "case_record_id": self.case_id,
            "contract_record_id": self.contract_id,
            "handler": self.identity["username"],
        }

    async def test_visible_non_manager_gets_capability_and_can_create_fee(self) -> None:
        capability = await self.client.get(f"{API}/cases/{self.case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        enabled = capability.json()
        for key in (
            "can_write", "can_generate_document", "can_upload_attachment",
            "can_delete_attachment", "can_create_reminder", "can_delete_reminder",
            "can_create_log", "can_update_progress", "can_change_phase",
            "can_manage_hearing", "can_create_case_task", "can_duplicate_case",
            "can_merge_case", "can_assign_team", "can_edit_hearing_lawyer",
            "can_edit_basic", "can_edit_court_info", "can_close_case",
            "can_archive", "can_create_finance",
        ):
            self.assertTrue(enabled[key], key)

        response = await self.client.post(f"{API}/finance/fees", json=self.fee_payload())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["case_id"], self.case_id)

    async def test_admin_gets_capability_without_case_team_assignment(self) -> None:
        self.identity = ADMIN
        capability = await self.client.get(f"{API}/cases/{self.case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 200, capability.text)
        self.assertTrue(capability.json()["can_create_finance"])

    async def test_invisible_case_stays_inaccessible(self) -> None:
        self.identity = OUTSIDER
        capability = await self.client.get(f"{API}/cases/{self.case_id}/action-capabilities")
        self.assertEqual(capability.status_code, 404, capability.text)

        response = await self.client.post(f"{API}/finance/fees", json=self.fee_payload())
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()

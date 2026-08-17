import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _user_permission_payload, dashboard, list_records
from app.models import BusinessRecord, ContractApprovalStep, JobRole, RolePermission, User


class JobRoleApprovalMenuContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                User.__table__, RolePermission.__table__, JobRole.__table__, BusinessRecord.__table__,
                ContractApprovalStep.__table__,
            ]))
        async with self.sessions() as db:
            db.add(RolePermission(
                role="user", display_name="普通用户", menu_keys=[], field_keys=[], data_scope="本人及共享数据",
            ))
            db.add(JobRole(
                code="CODEX-ASSISTANT", name="验收律师助理", permissions=["合同审批", "用印审批"], field_keys=[], is_active=True,
            ))
            db.add(User(
                username="codex_approval_assistant", display_name="验收律师助理", department="诉讼部",
                role="user", role_ids=["user"], password_hash="x", is_active=True,
                profile={"permission_role": "验收律师助理", "contract_approval_enabled": True},
            ))
            db.add(BusinessRecord(
                module="hr", serial_no="CODEX-HR-APPROVAL-ASSISTANT", title="验收律师助理",
                status="在职", owner="codex_approval_assistant", department="诉讼部",
                data={"username": "codex_approval_assistant"},
            ))
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-ASSIGNED-APPROVAL", title="指派审批合同",
                status="审批中", owner="contract_owner", department="其他部门",
                data={"current_approver": "codex_approval_assistant"},
            )
            db.add(contract)
            await db.flush()
            db.add(ContractApprovalStep(
                contract_record_id=contract.id, step_order=1,
                approver="codex_approval_assistant", status="待审批",
            ))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_legacy_approval_actions_grant_only_their_approval_workspaces(self):
        async with self.sessions() as db:
            user = await db.get(User, 1)
            payload = await _user_permission_payload(user, db)

        menu_keys = set(payload["menu_keys"])
        self.assertTrue(payload["can_approve_contract"])
        self.assertIn("contract-audit", menu_keys)
        self.assertIn("contract-audit-pending", menu_keys)
        self.assertIn("seal-audit", menu_keys)
        self.assertIn("seal-audit-pending", menu_keys)
        self.assertNotIn("contract-new", menu_keys)
        self.assertNotIn("contract-company", menu_keys)
        self.assertNotIn("seal-admin", menu_keys)

    async def test_dashboard_personal_contract_count_uses_assigned_approval_step(self):
        async with self.sessions() as db:
            payload = await dashboard(
                {"username": "codex_approval_assistant", "role": "user", "role_ids": ["user"]},
                db,
            )

        contract_todo = next(row for row in payload["todos"] if row[0] == "待审批合同")
        self.assertEqual(contract_todo[1], 1)
        self.assertEqual(contract_todo[2], 1)

    async def test_pending_contract_list_uses_assigned_approval_step(self):
        async with self.sessions() as db:
            other_contract = BusinessRecord(
                module="contract", serial_no="CODEX-OTHER-APPROVAL", title="其他审批人的合同",
                status="审批中", owner="contract_owner", department="其他部门",
                data={"current_approver": "other_approver"},
            )
            db.add(other_contract)
            await db.flush()
            db.add(ContractApprovalStep(
                contract_record_id=other_contract.id, step_order=1,
                approver="other_approver", status="待审批",
            ))
            await db.commit()

            payload = await list_records(
                module="contract", keyword="", record_status="", scope="audit", statuses="审批中",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="", pending_approver_only=True, page=1, page_size=20,
                identity={"username": "codex_approval_assistant", "role": "user", "role_ids": ["user"]},
                db=db,
            )

        self.assertEqual(payload["total"], 1)
        self.assertEqual([item["serial_no"] for item in payload["items"]], ["CODEX-ASSIGNED-APPROVAL"])


if __name__ == "__main__":
    unittest.main()

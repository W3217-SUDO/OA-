"""Focused contract tests for explicit approval authority."""

from __future__ import annotations

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.main import (
    CONTRACT_APPROVAL_ACTION_CODE,
    _can_act_on_contract_approval_step,
    _contract_customer_record_dict,
    _contract_customer_projection_context,
)
from app.models import BusinessRecord, ContractApprovalStep, JobRole, RolePermission, User


class ContractApprovalAuthorityContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = [
            BusinessRecord.__table__,
            ContractApprovalStep.__table__,
            JobRole.__table__,
            RolePermission.__table__,
            User.__table__,
        ]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.db = sessions()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        await self.engine.dispose()

    async def test_admin_is_not_an_implicit_substitute_for_the_assigned_approver(self) -> None:
        step = ContractApprovalStep(contract_record_id=1, step_order=1, approver="assigned", status="待审批")
        admin = {"username": "admin", "role": "admin"}

        self.assertFalse(await _can_act_on_contract_approval_step(step, admin, "", self.db))
        self.assertTrue(
            await _can_act_on_contract_approval_step(
                step,
                admin,
                CONTRACT_APPROVAL_ACTION_CODE,
                self.db,
            )
        )

    async def test_assigned_approver_still_needs_contract_approval_permission(self) -> None:
        step = ContractApprovalStep(contract_record_id=1, step_order=1, approver="assigned", status="待审批")
        identity = {"username": "assigned", "role": "user"}
        self.db.add_all([
            JobRole(code="NO-APPROVAL", name="无审批权限岗", permissions=[]),
            User(
                username="assigned", password_hash="unused", display_name="审批人员",
                department="上海分所", role="user", profile={"permission_role": "无审批权限岗"}, is_active=True,
            ),
        ])
        await self.db.commit()
        self.assertFalse(await _can_act_on_contract_approval_step(step, identity, "", self.db))

    async def test_assigned_approver_with_contract_action_can_approve(self) -> None:
        step = ContractApprovalStep(contract_record_id=1, step_order=1, approver="assigned", status="待审批")
        identity = {"username": "assigned", "role": "user"}
        self.db.add_all([
            JobRole(code="CONTRACT-APPROVER", name="合同审批岗", permissions=["合同审批"]),
            User(
                username="assigned", password_hash="unused", display_name="审批人员",
                department="上海分所", role="user", profile={"permission_role": "合同审批岗"}, is_active=True,
            ),
        ])
        await self.db.commit()
        self.assertTrue(await _can_act_on_contract_approval_step(step, identity, "", self.db))

    async def test_contract_projection_uses_bound_customer_and_live_approval_step(self) -> None:
        self.db.add_all([
            JobRole(code="PROJECTION-APPROVER", name="投影审批岗", permissions=["合同审批"]),
            User(
                username="assigned", password_hash="unused", display_name="审批人员",
                department="上海分所", role="user", profile={"permission_role": "投影审批岗"}, is_active=True,
            ),
        ])
        customer = BusinessRecord(
            module="customer", serial_no="KH-CODEX-PROJECTION", title="投影客户",
            customer="", status="我的客户", owner="assigned", department="上海分所",
            data={"customer_managers": ["assigned"]},
        )
        self.db.add(customer)
        await self.db.flush()
        contract = BusinessRecord(
            module="contract", serial_no="HT-CODEX-PROJECTION", title="投影合同",
            customer=customer.title, status="审批中", owner="assigned", department="上海分所",
            data={"customer_id": customer.id, "customer_no": customer.serial_no, "signed_at": "2026-08-24"},
        )
        self.db.add(contract)
        await self.db.flush()
        self.db.add(ContractApprovalStep(
            contract_record_id=contract.id, step_order=1, approver="assigned", status="待审批",
        ))
        await self.db.commit()

        projected = await _contract_customer_record_dict(
            contract,
            None,
            self.db,
            identity={"username": "assigned", "role": "user"},
        )
        self.assertEqual(projected["customer_id"], customer.id)
        self.assertEqual(projected["customer_no"], customer.serial_no)
        self.assertEqual(projected["signed_at"], "2026-08-24")
        self.assertEqual(projected["current_approver"], "assigned")
        self.assertEqual(projected["data"]["customer_manager_display_names"], ["审批人员"])
        self.assertTrue(projected["approval_capabilities"]["can_approve_current"])
        self.assertTrue(projected["data"]["approval_capabilities"]["can_approve_current"])

    async def test_legacy_customer_name_projection_uses_nfkc_and_collapsed_whitespace(self) -> None:
        customer = BusinessRecord(
            module="customer", serial_no="KH-NFKC", title="ACME 客户",
            customer="", status="我的客户", owner="assigned", department="上海分所", data={},
        )
        contract = BusinessRecord(
            module="contract", serial_no="HT-NFKC", title="历史合同",
            customer="ＡＣＭＥ   客户", status="审批通过", owner="assigned", department="上海分所", data={},
        )
        self.db.add_all([customer, contract])
        await self.db.commit()

        context = await _contract_customer_projection_context([contract], self.db)
        self.assertEqual(context["customers_by_name"]["acme 客户"][0].id, customer.id)


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _record_scope_conditions
from app.models import BusinessRecord, ContractApprovalStep, RolePermission, User


class ContractPendingApproverScopeContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                User.__table__, RolePermission.__table__, BusinessRecord.__table__, ContractApprovalStep.__table__,
            ]))
        async with self.sessions() as db:
            db.add_all([
                User(username="owner", display_name="合同发起人", department="甲部门", role="user", password_hash="x"),
                User(username="approver", display_name="律师助理二", department="乙部门", role="user", password_hash="x"),
                User(username="outsider", display_name="其他人员", department="乙部门", role="user", password_hash="x"),
                RolePermission(role="user", display_name="普通用户", menu_keys=[], field_keys=[], data_scope="本人及共享数据"),
            ])
            contract = BusinessRecord(module="contract", serial_no="CODEX-APPROVAL-SCOPE", title="审批范围测试", customer="测试客户", status="审批中", owner="owner", department="甲部门", data={"current_approver": "approver"})
            db.add(contract)
            await db.flush()
            db.add(ContractApprovalStep(contract_record_id=contract.id, step_order=1, approver="approver", status="待审批"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_only_current_pending_approver_can_query_contract_outside_ordinary_scope(self):
        async with self.sessions() as db:
            for username, expected in (("approver", 1), ("outsider", 0)):
                conditions = await _record_scope_conditions({"username": username, "role": "user"}, db)
                rows = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "contract", *conditions))).all())
                self.assertEqual(len(rows), expected, username)


if __name__ == "__main__":
    unittest.main()

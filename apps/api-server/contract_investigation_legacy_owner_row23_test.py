"""9.1 row 23: migrated contract business owners can create investigations."""

from __future__ import annotations

from datetime import date
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import ContractInvestigationInput, create_contract_investigation
from app.models import BusinessRecord, SystemConfig, User


class ContractInvestigationLegacyOwnerRow23Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="Fwl", display_name="范文林", department="调查部", role="user", password_hash="x", is_active=True),
                User(username="other", display_name="其他人员", department="其他部", role="user", password_hash="x", is_active=True),
                User(username="supervisor", display_name="调查主管", department="调查部", role="manager", password_hash="x", is_active=True),
                SystemConfig(
                    key="investigation_assignment", label="调查任务分配人", group="业务配置",
                    value={"supervisor_username": "supervisor"}, updated_by="row23-test",
                ),
            ])
            contract = BusinessRecord(
                module="contract", serial_no="SHHT2673411", title="测试客户8.3合同11", customer="测试客户8.3",
                status="审批通过", owner="legacy-import", department="调查部",
                data={
                    "source_person": "范文林", "migration_source": "legacy",
                    "shared_to": ["Fwl", "other"],
                },
            )
            db.add(contract)
            await db.commit()
            self.contract_id = contract.id

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    def payload(self, title: str) -> ContractInvestigationInput:
        return ContractInvestigationInput(
            title=title, owner="supervisor", right_type="商标",
            authorized_from=date(2026, 9, 1), authorized_to=date(2026, 10, 1),
            authorization_scope="全国", description="来源合同 SHHT2673411",
        )

    async def test_display_name_business_owner_can_create_from_migrated_contract(self) -> None:
        async with self.sessions() as db:
            result = await create_contract_investigation(
                self.contract_id, self.payload("测试客户8.3合同11调查任务"),
                {"username": "Fwl", "role": "user", "display_name": "范文林"}, db,
            )
        self.assertEqual(result["data"]["publisher"], "Fwl")
        self.assertEqual(result["data"]["contract_no"], "SHHT2673411")
        self.assertEqual(result["owner"], "supervisor")

    async def test_unrelated_user_remains_forbidden(self) -> None:
        async with self.sessions() as db:
            with self.assertRaisesRegex(Exception, "只有负责人"):
                await create_contract_investigation(
                    self.contract_id, self.payload("无关人员任务"),
                    {"username": "other", "role": "user", "display_name": "其他人员"}, db,
                )


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import CONTRACT_APPROVED_STATUS, _upgrade_schema, app
from app.models import BusinessRecord, ContractApprovalStep, LegacyContract, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "contract-status-admin",
    "role": "admin",
    "display_name": "Contract Status Admin",
    "department": "Contract Department",
}


class ContractApprovedStatusMigrationTest(unittest.TestCase):
    def test_historical_approved_and_performing_contracts_are_canonicalized(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
            connection.execute(BusinessRecord.__table__.insert(), [
                {
                    "module": "contract", "serial_no": "STATUS-OLD-APPROVED", "title": "Old approved",
                    "customer": "Customer", "status": "已通过", "owner": "admin", "department": "Dept",
                    "description": "", "data": {},
                },
                {
                    "module": "contract", "serial_no": "STATUS-OLD-PERFORMING", "title": "Old performing",
                    "customer": "Customer", "status": "履行中", "owner": "admin", "department": "Dept",
                    "description": "", "data": {},
                },
                {
                    "module": "contract", "serial_no": "STATUS-COMPLETED", "title": "Completed",
                    "customer": "Customer", "status": "已完成", "owner": "admin", "department": "Dept",
                    "description": "", "data": {},
                },
            ])
            connection.execute(LegacyContract.__table__.insert().values(ContractId=1, ContractStatus=70))

            _upgrade_schema(connection)
            _upgrade_schema(connection)

            rows = connection.execute(
                select(BusinessRecord.serial_no, BusinessRecord.status).order_by(BusinessRecord.serial_no)
            ).all()
            legacy_status = connection.execute(select(LegacyContract.ContractStatus)).scalar_one()
            migration_count = connection.exec_driver_sql(
                "SELECT COUNT(*) FROM schema_migrations WHERE key = 'contract_approved_status_v1'"
            ).scalar_one()

        self.assertEqual(dict(rows), {
            "STATUS-COMPLETED": "已完成",
            "STATUS-OLD-APPROVED": CONTRACT_APPROVED_STATUS,
            "STATUS-OLD-PERFORMING": CONTRACT_APPROVED_STATUS,
        })
        self.assertEqual(legacy_status, 20)
        self.assertEqual(migration_count, 1)


class ContractApprovedStatusRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", role_ids=["admin"],
                password_hash="x", is_active=True,
            ))
            contract = BusinessRecord(
                module="contract", serial_no="STATUS-RUNTIME-APPROVAL", title="Runtime approval",
                customer="Customer", status="审批中", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"current_approver": IDENTITY["username"]},
            )
            db.add(contract)
            await db.flush()
            db.add(ContractApprovalStep(
                contract_record_id=contract.id, step_order=1,
                approver=IDENTITY["username"], status="待审批",
            ))
            await db.commit()
            self.contract_id = contract.id

        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://contract-status.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_final_contract_approval_writes_canonical_status(self):
        with patch("app.main._sync_legacy_contract_audit", new=AsyncMock()):
            response = await self.client.post(
                f"{API}/contracts/{self.contract_id}/approve",
                json={"approved": True, "comment": "approve"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], CONTRACT_APPROVED_STATUS)
        async with self.sessions() as db:
            contract = await db.get(BusinessRecord, self.contract_id)
            step = await db.scalar(select(ContractApprovalStep).where(
                ContractApprovalStep.contract_record_id == self.contract_id
            ))
            event = await db.scalar(select(WorkflowEvent).where(
                WorkflowEvent.record_id == self.contract_id,
                WorkflowEvent.action == "合同审批完成",
            ))

        self.assertEqual(contract.status, CONTRACT_APPROVED_STATUS)
        self.assertEqual(step.status, "已通过")
        self.assertEqual(event.to_status, CONTRACT_APPROVED_STATUS)


if __name__ == "__main__":
    unittest.main()

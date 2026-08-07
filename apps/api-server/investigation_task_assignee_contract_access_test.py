import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.main import (
    InvestigationTaskInput,
    _ensure_record_visible,
    create_investigation_task,
)
from app.models import BusinessRecord, User


class InvestigationTaskAssigneeContractAccessTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_assignee_can_create_subtask_from_assigned_survey_with_bound_contract(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", department="总部", password_hash="x", role="admin"),
                User(username="fwl", display_name="范文玲", department="调查部", password_hash="x", role="user"),
            ])
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-ASSIGNEE", title="管理员合同",
                customer="CODEX 客户", status="已通过", owner="admin", department="总部", data={},
            )
            db.add(contract)
            await db.flush()
            survey = BusinessRecord(
                module="investigation", serial_no="DC-CODEX-ASSIGNEE", title="范文玲调查任务",
                customer="CODEX 客户", status="待分配", owner="fwl", department="调查部",
                data={"contract_id": contract.id, "contract_no": contract.serial_no},
            )
            db.add(survey)
            await db.commit()

            result = await create_investigation_task(
                survey.id,
                InvestigationTaskInput(title="范文玲子任务", owner="fwl", deadline=date.today()),
                {"username": "fwl", "role": "user"},
                db,
            )

        self.assertEqual(result["owner"], "fwl")
        self.assertEqual(result["data"]["investigation_record_id"], survey.id)
        self.assertEqual(result["data"]["contract_id"], contract.id)

        async with self.sessions() as db:
            with self.assertRaises(HTTPException):
                await _ensure_record_visible(
                    contract.id, {"username": "fwl", "role": "user"}, db
                )


if __name__ == "__main__":
    unittest.main()

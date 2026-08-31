"""Row 12: collected clues may create cases from contracts under approval."""

import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import BatchClueCaseInput, batch_create_cases_from_clues
from app.models import BusinessRecord, User


IDENTITY = {"username": "admin", "role": "admin"}


class InvestigationClueCaseContractStatusRow12Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _source_clue(self, db: AsyncSession, *, contract_status: str):
        suffix = contract_status
        contract = BusinessRecord(
            module="contract", serial_no=f"HT-CODEX-813-R12-{suffix}",
            title=f"第12行{suffix}合同", customer="第12行客户", status=contract_status,
            owner="admin", department="上海", data={},
        )
        db.add(contract)
        await db.flush()
        task = BusinessRecord(
            module="task", serial_no=f"RW-CODEX-813-R12-{suffix}",
            title="第12行来源调查任务", customer=contract.customer, status="已完成",
            owner="admin", department=contract.department,
            data={"contract_id": contract.id, "contract_no": contract.serial_no, "contract_name": contract.title},
        )
        db.add(task)
        await db.flush()
        clue = BusinessRecord(
            module="clue", serial_no=f"XS-CODEX-813-R12-{suffix}", title="第12行已取证线索",
            customer=contract.customer, status="已取证", owner="admin", department=contract.department,
            data={"source_task_id": task.id, "cause_or_charge": "商标侵权"},
        )
        db.add(clue)
        await db.commit()
        return contract, clue

    async def test_approval_in_progress_contract_creates_case_and_carries_contract_customer(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", department="上海", password_hash="x", role="admin", is_active=True),
                User(username="fwl", display_name="范文林", department="上海", password_hash="x", role="user", is_active=True),
            ])
            contract, clue = await self._source_clue(db, contract_status="审批中")
            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(
                    clue_ids=[clue.id], case_type="民事案件",
                    handling_lawyer="admin", assistant="fwl",
                ), IDENTITY, db,
            )
            case = await db.get(BusinessRecord, result["created_ids"][0])

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(case.customer, contract.customer)
        self.assertEqual(case.data["contract_id"], contract.id)
        self.assertEqual(case.data["contract_no"], contract.serial_no)

    async def test_draft_contract_remains_rejected_without_creating_case(self):
        async with self.sessions() as db:
            _, clue = await self._source_clue(db, contract_status="草稿")
            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(clue_ids=[clue.id], case_type="民事案件"), IDENTITY, db,
            )
            cases = list((await db.scalars(
                select(BusinessRecord).where(BusinessRecord.module == "case")
            )).all())

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertIn("状态不支持", result["errors"][0]["error"])
        self.assertEqual(cases, [])


if __name__ == "__main__":
    unittest.main()

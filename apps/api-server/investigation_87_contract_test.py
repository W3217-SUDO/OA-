"""8.7 Excel regressions: collection details and source-task case conversion."""

import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    BatchClueCaseInput,
    ClueCollectionInput,
    ClueSourceContractBindingInput,
    batch_create_cases_from_clues,
    bind_clue_source_contract,
    register_clue_collection,
)
from app.models import BusinessRecord


IDENTITY = {"username": "admin", "role": "admin"}


class Investigation87ContractTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_collection_keeps_all_legacy_registration_fields(self):
        async with self.sessions() as db:
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-87-COLLECT", title="取证线索", customer="CODEX客户",
                status="待取证", owner="admin", department="上海", data={},
            )
            db.add(clue)
            await db.commit()
            result = await register_clue_collection(
                clue.id,
                ClueCollectionInput(
                    collected_at=date.today(), notary_institution="上海市东方公证处",
                    notarization_no="(2026)沪东证字001号", invoice_no="INV-CODEX-87",
                    storage_location="档案室 A-01", evidence_status="已入库",
                ),
                IDENTITY, db,
            )

        self.assertEqual(result["status"], "已取证")
        self.assertEqual(result["data"]["notarization_no"], "(2026)沪东证字001号")
        self.assertEqual(result["data"]["invoice_no"], "INV-CODEX-87")
        self.assertEqual(result["data"]["storage_location"], "档案室 A-01")
        self.assertEqual(result["data"]["evidence_status"], "已入库")

    async def test_case_uses_contract_from_source_task_and_enters_pending_assignment(self):
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-87", title="CODEX调查合同", customer="CODEX客户",
                status="已通过", owner="admin", department="上海", data={},
            )
            db.add(contract)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no="RW-CODEX-87", title="来源调查任务", customer="CODEX客户",
                status="已完成", owner="admin", department="上海",
                data={"investigation_record_id": 1, "contract_no": contract.serial_no, "contract_name": contract.title},
            )
            db.add(task)
            await db.flush()
            clue = BusinessRecord(
                module="clue", serial_no="XS-CODEX-87", title="自动转案线索", customer="CODEX客户",
                status="已取证", owner="admin", department="上海",
                data={"source_task_id": task.id, "client_position": "原告", "cause_or_charge": "商标侵权"},
            )
            db.add(clue)
            await db.commit()
            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(clue_ids=[clue.id], case_type="民事案件", court="上海市浦东新区人民法院"),
                IDENTITY, db,
            )
            case = await db.get(BusinessRecord, result["created_ids"][0])

        self.assertEqual(result["created"], 1)
        self.assertEqual(case.status, "新案待分配")
        self.assertEqual(case.data["contract_id"], contract.id)
        self.assertEqual(case.data["contract_no"], "HT-CODEX-87")
        self.assertEqual(case.data["clue_no"], "XS-CODEX-87")
        self.assertEqual(case.data["client_position"], "原告")
        self.assertEqual(case.data["cause_or_charge"], "商标侵权")

    async def test_legacy_clue_binding_repairs_source_task_and_customer_before_case_generation(self):
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-87-REPAIR", title="CODEX修复合同", customer="CODEX正确客户",
                status="已通过", owner="admin", department="上海", data={},
            )
            db.add(contract)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no="RW-CODEX-87-REPAIR", title="历史来源任务", customer="历史错误客户",
                status="已完成", owner="admin", department="上海", data={"investigation_record_id": 1},
            )
            db.add(task)
            await db.flush()
            clue = BusinessRecord(
                module="clue", serial_no="XS-CODEX-87-REPAIR", title="历史已取证线索", customer="历史错误客户",
                status="已取证", owner="admin", department="上海", data={"source_task_id": task.id},
            )
            db.add(clue)
            await db.commit()
            result = await bind_clue_source_contract(
                clue.id, ClueSourceContractBindingInput(contract_record_id=contract.id), IDENTITY, db,
            )
            await db.refresh(task)
            await db.refresh(clue)

        self.assertEqual(result["contract"]["serial_no"], "HT-CODEX-87-REPAIR")
        self.assertEqual(task.customer, "CODEX正确客户")
        self.assertEqual(task.data["contract_id"], contract.id)
        self.assertEqual(clue.customer, "CODEX正确客户")
        self.assertEqual(clue.data["contract_no"], "HT-CODEX-87-REPAIR")


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.tasks import _apply_case_automatic_task_rules, _apply_task_auto_completion
from app.database import Base
from app.models import BusinessRecord, Department, SystemParameter, User


class LegacyTaskServiceParityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="lawyer", display_name="律师", department="诉讼部", role="user", password_hash="x", is_active=True),
                User(username="assistant", display_name="助理", department="诉讼部", role="user", password_hash="x", is_active=True),
                User(username="manager", display_name="负责人", department="诉讼部", role="manager", password_hash="x", is_active=True),
                User(username="departed", display_name="离职员工", department="诉讼部", role="user", password_hash="x", is_active=False),
                User(username="gz-officer", display_name="公证交接人", department="广州分所", role="user", password_hash="x", is_active=True),
                Department(code="LIT", name="诉讼部", manager="manager", is_active=True),
                SystemParameter(category="task_officer", code="TaskOfficer_Gzs", name="gz-officer", is_active=True),
            ])
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_notary_jobs_and_handoff_are_backfilled_once(self) -> None:
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="CASE-NOTARY", title="case", customer="客户", status="等待审核公证书", owner="lawyer", department="诉讼部", data={"handling_lawyer_usernames": ["lawyer"], "assistant_usernames": ["assistant"], "notary_certificate_ready": True})
            db.add(case); await db.flush()
            db.add(BusinessRecord(module="notary", serial_no="NOTARY-1", title="notary", customer="客户", status="待审核", owner="assistant", department="诉讼部", data={"case_id": case.id, "case_no": case.serial_no, "evidence_status": "未入库"}))
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 9)), 3)
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 9)), 0)
            titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "task"))).all())
        self.assertEqual(titles, {"审核公证书", "证物入库", "交接公证书"})

    async def test_departed_owner_transfers_and_completed_goods_task_updates_evidence(self) -> None:
        async with self.sessions() as db:
            evidence = BusinessRecord(module="warehouse", serial_no="E-1", title="证物", customer="客户", status="in", owner="assistant", department="诉讼部", data={"evidence_status": "已入库"})
            db.add(evidence); await db.flush()
            db.add_all([
                BusinessRecord(module="task", serial_no="T-1", title="未完成任务", customer="客户", status="处理中", owner="departed", department="诉讼部", data={"deadline": "2026-10-01"}),
                BusinessRecord(module="task", serial_no="T-2", title="系统自动任务-拿证物", customer="客户", status="已完成", owner="assistant", department="诉讼部", data={"auto_task_type": "take_evidence:1", "warehouse_evidence_ids": [evidence.id]}),
            ])
            await db.commit()
            self.assertTrue(await _apply_task_auto_completion(db))
            transfer = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "T-1"))
            await db.refresh(evidence)
        self.assertEqual(transfer.owner, "manager")
        self.assertEqual(evidence.data["evidence_status"], "已出库")


if __name__ == "__main__":
    unittest.main()

"""9.4 rows 5-9: legacy case automatic-task rules."""

import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.tasks import _apply_case_automatic_task_rules, _ensure_phase_automatic_tasks
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, User


class CaseAutomaticTasks94Rows59Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for username, display_name in (("lawyer", "经办律师"), ("assistant", "律师助理"), ("archive-owner", "梁晨宇")):
                db.add(User(username=username, display_name=display_name, department="诉讼部", role="user", password_hash="x", is_active=True))
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def create_case(self, serial_no: str, status: str, changed_on: date) -> int:
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no=serial_no, title=serial_no, customer="客户", status=status,
                owner="lawyer", department="诉讼部", data={
                    "handling_lawyer_usernames": ["lawyer"], "handling_lawyers": ["经办律师"],
                    "assistant_usernames": ["assistant"], "assistants": ["律师助理"],
                    "phase_changed_at": datetime.combine(changed_on, datetime.min.time()).isoformat(),
                },
            )
            db.add(case); await db.commit(); await db.refresh(case)
            return case.id

    async def tasks(self, case_id: int) -> list[BusinessRecord]:
        async with self.sessions() as db:
            return list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "task", BusinessRecord.data["case_id"].as_integer() == case_id,
            ).order_by(BusinessRecord.id))).all())

    async def test_immediate_phase_rules_match_legacy_people_and_deadlines(self) -> None:
        closed_id = await self.create_case("R6", "一审和解结案", date(2026, 9, 7))
        mediation_id = await self.create_case("R7", "一审和解中", date(2026, 9, 7))
        async with self.sessions() as db:
            closed = await db.get(BusinessRecord, closed_id)
            mediation = await db.get(BusinessRecord, mediation_id)
            await _ensure_phase_automatic_tasks(closed, db, previous_status="文书准备", today=date(2026, 9, 7))
            await _ensure_phase_automatic_tasks(mediation, db, previous_status="文书准备", today=date(2026, 9, 7))
            await _ensure_phase_automatic_tasks(mediation, db, previous_status="文书准备", today=date(2026, 9, 7))
            await db.commit()
        closed_task = (await self.tasks(closed_id))[0]
        mediation_tasks = await self.tasks(mediation_id)
        self.assertEqual((closed_task.title, closed_task.owner), ("结算归档一审和解结案", "archive-owner"))
        self.assertEqual((closed_task.data or {})["legacy_task_type_id"], 101024)
        self.assertEqual((date.fromisoformat(closed_task.data["deadline"]) - date(2026, 9, 7)).days, 50)
        self.assertEqual(len(mediation_tasks), 1)
        self.assertEqual((mediation_tasks[0].title, mediation_tasks[0].owner), ("跟进和解—提醒任务", "lawyer"))
        self.assertEqual(mediation_tasks[0].data["deadline"], "2027-03-07")

    async def test_closed_archive_rejects_missing_configured_owner_without_fallback(self) -> None:
        async with self.sessions() as db:
            archive_owner = await db.scalar(select(User).where(User.username == "archive-owner"))
            archive_owner.is_active = False
            await db.commit()
        case_id = await self.create_case("R6-FALLBACK", "一审和解结案", date(2026, 9, 8))
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            with self.assertRaisesRegex(Exception, "梁晨宇"):
                await _ensure_phase_automatic_tasks(case, db, previous_status="文书准备", today=date(2026, 9, 8))
            await db.rollback()
        self.assertEqual(await self.tasks(case_id), [])

    async def test_scheduler_does_not_backfill_immediate_phase_rules(self) -> None:
        document_id = await self.create_case("R3-HISTORY", "文书准备", date(2026, 9, 8))
        closed_id = await self.create_case("R6-HISTORY", "一审和解结案", date(2026, 9, 8))
        async with self.sessions() as db:
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 8)), 0)
        self.assertEqual(await self.tasks(document_id), [])
        self.assertEqual(await self.tasks(closed_id), [])

    async def test_delayed_phase_rules_observe_boundaries_and_are_idempotent(self) -> None:
        closed_id = await self.create_case("R5", "一审和解结案", date(2026, 7, 19))
        filing_id = await self.create_case("R9", "提交立案", date(2026, 8, 18))
        async with self.sessions() as db:
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 6)), 0)
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 7)), 2)
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 7)), 0)
        closed = next(task for task in await self.tasks(closed_id) if task.title == "归档结算—提醒任务")
        filing = (await self.tasks(filing_id))[0]
        self.assertEqual((closed.title, closed.owner, closed.data["collaborators"]), ("归档结算—提醒任务", "assistant", ["assistant"]))
        self.assertEqual((filing.title, filing.owner, filing.data["legacy_task_type_id"]), ("跟进立案", "assistant", 1010131))
        self.assertEqual((date.fromisoformat(filing.data["deadline"]) - date(2026, 9, 7)).days, 220)

    async def test_payment_rule_is_case_scoped_and_recovers_after_people_are_added(self) -> None:
        case_id = await self.create_case("R8", "执行立案", date(2026, 8, 1))
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            case.data = {**(case.data or {}), "assistant_usernames": [], "assistants": []}
            db.add(IncomingPayment(
                receipt_no="HK-R8-A", received_date=date(2026, 8, 7), amount=100, payer_name="客户",
                status="已分配", claimed_customer="客户", allocated_amount=100,
                allocations=[{"case_id": case_id, "case_no": "R8", "amount": 100}], operator="finance",
            ))
            db.add(IncomingPayment(
                receipt_no="HK-R8-B", received_date=date(2026, 8, 8), amount=200, payer_name="客户",
                status="已分配", claimed_customer="客户", allocated_amount=200,
                allocations=[{"case_id": case_id, "case_no": "R8", "amount": 200}], operator="finance",
            ))
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 7)), 0)
            case = await db.get(BusinessRecord, case_id)
            case.data = {**(case.data or {}), "assistant_usernames": ["assistant"], "assistants": ["律师助理"]}
            await db.commit()
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 7)), 1)
            self.assertEqual(await _apply_case_automatic_task_rules(db, today=date(2026, 9, 7)), 0)
        task = (await self.tasks(case_id))[0]
        self.assertEqual((task.title, task.owner, task.data["legacy_task_type_id"]), ("结算归档任务", "assistant", 1001003))
        self.assertEqual(task.data["trigger_source_id"], f"case:{case_id}:payment_received_30d")
        self.assertEqual(task.data["trigger_at"], "2026-09-06")

    def test_both_phase_entry_points_and_scheduler_are_wired(self) -> None:
        root = Path(__file__).parent
        legal = (root / "app/areas/legal/router.py").read_text(encoding="utf-8")
        system = (root / "app/core/system.py").read_text(encoding="utf-8")
        self.assertEqual(legal.count("await _ensure_phase_automatic_tasks("), 2)
        normal_basic = legal[legal.index("async def update_normal_case_basic"):legal.index("async def update_arbitration_case_basic")]
        self.assertIn("await _ensure_document_preparation_task(case_record, db", normal_basic)
        self.assertIn("await _apply_case_automatic_task_rules(db)", system)


if __name__ == "__main__":
    unittest.main()

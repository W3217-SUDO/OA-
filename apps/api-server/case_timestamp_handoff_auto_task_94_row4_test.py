"""9.4 row 4: timestamp-evidence file handoff task automation."""

import unittest
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.tasks import _ensure_timestamp_evidence_handoff_task
from app.database import Base
from app.models import (
    BusinessRecord,
    LegacyInvestigationClue,
    LegacyInvestigationClueEvidence,
    Notification,
    User,
    WorkflowEvent,
)


ASSISTANT = {
    "username": "row4-assistant",
    "display_name": "律师助理",
    "department": "诉讼部",
}
OWNER = {
    "username": "row4-owner",
    "display_name": "范应根",
    "department": "调查部",
}


class TimestampHandoffAutoTask94Row4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for identity in (ASSISTANT, OWNER):
                db.add(User(
                    username=identity["username"],
                    display_name=identity["display_name"],
                    department=identity["department"],
                    role="user",
                    password_hash="x",
                    is_active=True,
                ))
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def create_case(self, serial_no: str, *, data: dict, status: str = "文书准备") -> int:
        async with self.sessions() as db:
            record = BusinessRecord(
                module="case",
                serial_no=serial_no,
                title=f"{serial_no} 案件",
                customer="测试客户",
                status=status,
                owner=ASSISTANT["username"],
                department="诉讼部",
                data={
                    "assistant": ASSISTANT["display_name"],
                    "assistant_username": ASSISTANT["username"],
                    **data,
                },
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record.id

    async def timestamp_tasks(self, case_id: int) -> list[BusinessRecord]:
        async with self.sessions() as db:
            return list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "task",
                BusinessRecord.data["case_id"].as_integer() == case_id,
                BusinessRecord.data["auto_task_type"].as_string() == "timestamp_evidence_handoff",
            ))).all())

    async def test_creates_exact_task_once(self) -> None:
        case_id = await self.create_case(
            "CODEX-94-R4-TIMESTAMP",
            data={"source_is_timestamp_evidence": True, "source_evidence_method": "timestamp"},
        )
        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, case_id)
            first = await _ensure_timestamp_evidence_handoff_task(
                case_record, db, system_operator="row4-system",
            )
            second = await _ensure_timestamp_evidence_handoff_task(
                case_record, db, system_operator="row4-system",
            )
            await db.commit()
            self.assertEqual(first.id, second.id)

        tasks = await self.timestamp_tasks(case_id)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        data = task.data or {}
        self.assertEqual((task.title, task.status), ("交接时间戳文件", "待接收"))
        self.assertEqual(task.owner, OWNER["username"])
        self.assertEqual(task.description, "CODEX-94-R4-TIMESTAMP,交接时间戳文件.")
        self.assertEqual(data["initiator"], ASSISTANT["username"])
        self.assertEqual(data["collaborators"], [])
        self.assertEqual(data["creation_mode"], "自动")
        self.assertEqual(data["task_type"], "自动任务")
        self.assertEqual(data["source"], "案件任务")
        self.assertEqual(data["case_no"], "CODEX-94-R4-TIMESTAMP")
        self.assertEqual((date.fromisoformat(data["deadline"]) - date.fromisoformat(data["start_at"])).days, 7)
        self.assertEqual(data["end_at"], data["deadline"])

        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, case_id)
            events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == task.id,
            ))).all())
            notices = list((await db.scalars(select(Notification).where(
                Notification.source_type == "task", Notification.source_id == task.id,
            ))).all())
        self.assertEqual((case_record.data or {})["timestamp_evidence_handoff_task_id"], task.id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].operator, ASSISTANT["username"])
        self.assertEqual(
            events[0].comment,
            "律师助理新建任务给负责人(范应根)，协作人(无)，附言：\n\n"
            "CODEX-94-R4-TIMESTAMP,交接时间戳文件.",
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].recipient, OWNER["username"])

    async def test_all_conditions_are_required(self) -> None:
        ordinary_id = await self.create_case(
            "CODEX-94-R4-ORDINARY", data={"source_notary_institution": "公证处"},
        )
        wrong_phase_id = await self.create_case(
            "CODEX-94-R4-PHASE",
            status="新案待分配",
            data={"source_is_timestamp_evidence": True},
        )
        no_assistant_id = await self.create_case(
            "CODEX-94-R4-NOASSIST", data={"source_is_timestamp_evidence": True},
        )
        async with self.sessions() as db:
            no_assistant = await db.get(BusinessRecord, no_assistant_id)
            no_assistant.data = {"source_is_timestamp_evidence": True}
            for case_id in (ordinary_id, wrong_phase_id, no_assistant_id):
                case_record = await db.get(BusinessRecord, case_id)
                result = await _ensure_timestamp_evidence_handoff_task(
                    case_record, db, system_operator="row4-system",
                )
                self.assertIsNone(result)
            await db.commit()
        for case_id in (ordinary_id, wrong_phase_id, no_assistant_id):
            self.assertEqual(await self.timestamp_tasks(case_id), [])

    async def test_historical_clue_guid_relation_is_supported(self) -> None:
        case_id = await self.create_case(
            "CODEX-94-R4-LEGACY", data={"clue_no": "CODEX-CLUE-LEGACY"},
        )
        async with self.sessions() as db:
            db.add(LegacyInvestigationClue(
                ClueId=940004,
                ClueNo="CODEX-CLUE-LEGACY",
                ClueGuid="codex-row4-legacy-guid",
                IsActived="T",
            ))
            db.add(LegacyInvestigationClueEvidence(
                EvidenceId=940004,
                EvidenceGuid="codex-row4-evidence-guid",
                ClueGuid="codex-row4-legacy-guid",
                NotaryOrganization="时间戳取证",
                IsActived="T",
            ))
            await db.flush()
            case_record = await db.get(BusinessRecord, case_id)
            task = await _ensure_timestamp_evidence_handoff_task(
                case_record, db, system_operator="row4-system",
            )
            await db.commit()
            self.assertIsNotNone(task)
        self.assertEqual(len(await self.timestamp_tasks(case_id)), 1)

    async def test_missing_fixed_owner_fails_without_partial_task(self) -> None:
        case_id = await self.create_case(
            "CODEX-94-R4-NOOWNER", data={"source_is_timestamp_evidence": True},
        )
        async with self.sessions() as db:
            owner = await db.scalar(select(User).where(User.username == OWNER["username"]))
            owner.is_active = False
            await db.commit()
        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, case_id)
            with self.assertRaisesRegex(Exception, "范应根"):
                await _ensure_timestamp_evidence_handoff_task(
                    case_record, db, system_operator="row4-system",
                )
            await db.rollback()
        self.assertEqual(await self.timestamp_tasks(case_id), [])

    def test_collection_projection_and_both_case_triggers_are_wired(self) -> None:
        root = Path(__file__).parent
        collection_source = (root / "app/core/investigation.py").read_text(encoding="utf-8")
        conversion_source = (root / "app/areas/investigation/router.py").read_text(encoding="utf-8")
        legal_source = (root / "app/areas/legal/router.py").read_text(encoding="utf-8")
        self.assertIn('"evidence_method": "timestamp" if timestamp_evidence else "notarial"', collection_source)
        self.assertIn('"source_is_timestamp_evidence": timestamp_evidence', conversion_source)
        self.assertEqual(legal_source.count("await _ensure_timestamp_evidence_handoff_task("), 2)


if __name__ == "__main__":
    unittest.main()

"""8.31 row 9: collected-clue conversion keeps cause and case-team fields."""

from __future__ import annotations

import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import BatchClueCaseInput, batch_create_cases_from_clues
from app.models import BusinessRecord, User, WorkflowEvent


IDENTITY = {"username": "admin", "role": "admin", "display_name": "陶威", "department": "调查部"}


class InvestigationClueCaseFieldsRow9Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_conversion_persists_display_names_and_stable_usernames(self) -> None:
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="陶威", department="调查部", role="admin", password_hash="x", is_active=True),
                User(username="fwl", display_name="范文林", department="调查部", role="user", password_hash="x", is_active=True),
            ])
            clue = BusinessRecord(
                module="clue",
                serial_no="CODEX-831-R9-CLUE",
                title="第9行已取证线索",
                customer="第9行客户",
                status="已取证",
                owner="admin",
                department="调查部",
                data={},
            )
            db.add(clue)
            await db.commit()

            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(
                    clue_ids=[clue.id],
                    case_type="民事案件",
                    client_position="原告",
                    cause_or_charge="侵害商标权纠纷",
                    case_phase="等待公证书",
                    handling_lawyer="admin",
                    assistant="fwl",
                ),
                IDENTITY,
                db,
            )
            case_record = await db.get(BusinessRecord, result["created_ids"][0])
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == case_record.id))).all())

        self.assertEqual(result["created"], 1)
        self.assertEqual(case_record.data["cause_or_charge"], "侵害商标权纠纷")
        self.assertEqual(case_record.data["cause_of_action"], "侵害商标权纠纷")
        self.assertEqual(case_record.data["handling_lawyers"], ["陶威"])
        self.assertEqual(case_record.data["handling_lawyer_usernames"], ["admin"])
        self.assertEqual(case_record.data["assistant"], "范文林")
        self.assertEqual(case_record.data["assistant_username"], "fwl")
        self.assertEqual(case_record.data["case_team_usernames"], ["admin", "fwl"])
        self.assertEqual(len(events), 1)
        self.assertIn("案由 侵害商标权纠纷", events[0].comment)
        self.assertIn("经办律师 陶威", events[0].comment)
        self.assertIn("律师助理 范文林", events[0].comment)

    async def test_conversion_rejects_blank_case_fields_without_creating_dirty_case(self) -> None:
        async with self.sessions() as db:
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-831-R9-BLANK", title="空字段线索",
                customer="第9行客户", status="已取证", owner="admin", department="调查部", data={},
            )
            db.add(clue)
            await db.commit()

            result = await batch_create_cases_from_clues(
                BatchClueCaseInput(clue_ids=[clue.id]), IDENTITY, db,
            )
            cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case"))).all())

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertIn("案由、经办律师、律师助理", result["errors"][0]["error"])
        self.assertEqual(cases, [])


if __name__ == "__main__":
    unittest.main()

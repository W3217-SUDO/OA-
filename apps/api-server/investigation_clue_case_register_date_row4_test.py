"""9.1 row 4: converting a collected clue sets the case register date."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import BatchClueCaseInput, _backfill_clue_generated_case_register_dates, batch_create_cases_from_clues
from app.models import BusinessRecord, User, WorkflowEvent


IDENTITY = {"username": "admin", "role": "admin", "display_name": "陶威", "department": "调查部"}


class InvestigationClueCaseRegisterDateRow4Test(unittest.IsolatedAsyncioTestCase):
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

    async def test_conversion_uses_generation_date_as_case_register_date(self) -> None:
        generated_on = date(2026, 9, 1)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="陶威", department="调查部", role="admin", password_hash="x", is_active=True),
                User(username="fwl", display_name="范文林", department="调查部", role="user", password_hash="x", is_active=True),
            ])
            clue = BusinessRecord(
                module="clue",
                serial_no="CODEX-901-R4-CLUE",
                title="第4行已取证线索",
                customer="第4行客户",
                status="已取证",
                owner="admin",
                department="调查部",
                data={},
            )
            db.add(clue)
            await db.commit()

            with patch("app.main.date") as mocked_date:
                mocked_date.today.return_value = generated_on
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

        self.assertEqual(result["created"], 1)
        self.assertEqual(case_record.data["case_register_date"], "2026-09-01")
        self.assertEqual(case_record.data["filing_date"], "2026-09-01")

    async def test_historical_original_record_uses_generation_event_business_date(self) -> None:
        async with self.sessions() as db:
            case_record = BusinessRecord(
                id=47150,
                module="case",
                serial_no="SHMS2600438",
                title="测试555侵害商标权纠纷11",
                customer="测试555",
                status="等待公证书",
                owner="fwl",
                department="调查取证部",
                data={"batch_converted": True, "clue_no": "M26085930"},
                created_at=datetime(2026, 8, 31, 16, 30, tzinfo=timezone.utc),
            )
            db.add(case_record)
            db.add(WorkflowEvent(
                record_id=47150,
                action="线索生成案件",
                to_status="等待公证书",
                operator="admin",
                created_at=datetime(2026, 9, 1, 7, 51, 6, tzinfo=timezone.utc),
            ))
            await db.commit()

            self.assertEqual(await _backfill_clue_generated_case_register_dates(db), 1)
            await db.commit()
            await db.refresh(case_record)

        self.assertEqual(case_record.data["case_register_date"], "2026-09-01")
        self.assertEqual(case_record.data["filing_date"], "2026-09-01")

    async def test_existing_filing_date_is_preserved_and_fills_missing_register_date(self) -> None:
        async with self.sessions() as db:
            case_record = BusinessRecord(
                module="case",
                serial_no="SHMS-ROW4-EXISTING-FILING",
                title="已有兼容立案日期",
                customer="第4行客户",
                status="等待公证书",
                owner="fwl",
                department="调查取证部",
                data={"batch_converted": True, "filing_date": "2026-08-30"},
                created_at=datetime(2026, 9, 1, 7, 51, 6, tzinfo=timezone.utc),
            )
            db.add(case_record)
            await db.commit()

            self.assertEqual(await _backfill_clue_generated_case_register_dates(db), 1)
            await db.commit()
            await db.refresh(case_record)

        self.assertEqual(case_record.data["filing_date"], "2026-08-30")
        self.assertEqual(case_record.data["case_register_date"], "2026-08-30")


if __name__ == "__main__":
    unittest.main()

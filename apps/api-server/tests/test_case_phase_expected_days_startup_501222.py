"""501222：重启时重置模板阶段不能丢掉“预期停留天数”。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import SystemParameter


class CasePhaseExpectedDaysStartupTest(unittest.IsolatedAsyncioTestCase):
    async def test_startup_keeps_admin_expected_days_on_template_phases(self):
        from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
        from app.core.startup_data import initialize_startup_data
        from app.core.startup_migrations import migrate_startup_schema

        with tempfile.TemporaryDirectory() as directory:
            engine = create_async_engine(f"sqlite+aiosqlite:///{Path(directory) / 'phase.db'}")
            try:
                await migrate_startup_schema(engine, _upgrade_schema)
                sessions = async_sessionmaker(engine, expire_on_commit=False)

                async def template(code: str) -> SystemParameter:
                    async with sessions() as db:
                        return await db.scalar(select(SystemParameter).where(SystemParameter.category == "case_phase", SystemParameter.code == code))

                with patch.object(settings, "seed_demo_data", False), patch.object(settings, "initial_admin_password", "Phase501222Startup!"):
                    await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)
                    self.assertEqual((await template("WAIT_NOTARY")).extra.get("expected_days"), 30, "模板阶段按初始天数补上")
                    async with sessions() as db:
                        row = await db.scalar(select(SystemParameter).where(SystemParameter.category == "case_phase", SystemParameter.code == "WAIT_NOTARY"))
                        row.extra = {**row.extra, "expected_days": "45"}
                        await db.commit()
                    await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)
                    self.assertEqual((await template("WAIT_NOTARY")).extra.get("expected_days"), "45", "管理员改过的天数重启后保留")
                    self.assertEqual((await template("WAIT_NOTARY")).extra.get("sort_order"), 10, "其余模板字段照常重置")
            finally:
                await engine.dispose()


if __name__ == "__main__":
    unittest.main()

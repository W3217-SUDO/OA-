"""BUG20261105026（思法汇成 11-05）：“知识产权中心”改名“知产非诉”，只改显示名，菜单 key 不变；管理员手工改过的不动。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.main  # noqa: F401  注册全部模型
from app.config import settings
from app.models import SystemMenu


class IprMenuRename501636Test(unittest.IsolatedAsyncioTestCase):
    async def run_startup(self, label: str, updated_by: str) -> str:
        from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
        from app.core.startup_data import initialize_startup_data
        from app.core.startup_migrations import migrate_startup_schema
        with tempfile.TemporaryDirectory() as directory:
            engine = create_async_engine(f"sqlite+aiosqlite:///{Path(directory) / 'r636.db'}")
            try:
                await migrate_startup_schema(engine, _upgrade_schema)
                sessions = async_sessionmaker(engine, expire_on_commit=False)
                async with sessions() as db:
                    db.add(SystemMenu(key="ipr", parent_key="", label=label, icon="file-text", sort_order=67, is_visible=True, updated_by=updated_by))
                    await db.commit()
                with patch.object(settings, "seed_demo_data", False), patch.object(settings, "initial_admin_password", "R636Startup123!"):
                    await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)
                async with sessions() as db:
                    return (await db.scalar(select(SystemMenu).where(SystemMenu.key == "ipr"))).label
            finally:
                await engine.dispose()

    async def test_system_menu_renamed(self):
        self.assertEqual(await self.run_startup("知识产权中心", "system"), "知产非诉")

    async def test_admin_edited_label_kept(self):
        self.assertEqual(await self.run_startup("知产中心", "admin"), "知产中心")

"""BUG20261031001（思法汇成 2026-10-31）：页面上显示人员用姓名，不直接显示登录账号。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.personal_agent.confirmation_history import _with_operator_names
from app.database import Base
from app.models import User


class ConfirmationOperatorNameTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add(User(username="codexname", display_name="姓名测试员", password_hash="isolated-only", department="CODEX", role="staff"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_operator_account_is_shown_as_name(self):
        items = [{"operator": "codexname"}, {"operator": None}]
        async with self.sessions() as db:
            await _with_operator_names(items, db)
        self.assertEqual(items[0]["operator_display_name"], "姓名测试员")
        self.assertIsNone(items[1]["operator_display_name"])


if __name__ == "__main__":
    unittest.main()

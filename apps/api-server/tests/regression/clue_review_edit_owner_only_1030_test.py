"""BUG20261030014：待审批、待客户审核的线索只有提交线索的调查员本人能改，审批人（含管理员）不能改。"""
import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import RecordUpdate, update_investigation_record
from app.models import BusinessRecord, User
from tests.personnel_role_fixture import bind_system_role_pages


class ClueReviewEditOwnerOnlyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", department="上海", password_hash="x", role="admin"),
                User(username="codex-inv", display_name="调查员", department="上海", password_hash="x", role="user"),
            ])
            self.ids = {}
            for status in ("待审批", "待客户审核", "待取证"):
                clue = BusinessRecord(module="clue", serial_no=f"CODEX-1030-014-{status}", title="", customer="CODEX客户",
                                      status=status, owner="codex-inv", department="上海", data={"publisher": "codex-inv", "shop_name": "原店铺"})
                db.add(clue)
                await db.flush()
                self.ids[status] = clue.id
            await db.commit()
        await bind_system_role_pages(self.sessions)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def edit(self, status, identity):
        async with self.sessions() as db:
            return await update_investigation_record(self.ids[status], RecordUpdate(data={"shop_name": "改后店铺"}), identity, db)

    async def test_reviewer_cannot_edit_pending_clues(self):
        for status in ("待审批", "待客户审核"):
            with self.assertRaises(HTTPException) as raised:
                await self.edit(status, {"username": "admin", "role": "admin"})
            self.assertEqual(raised.exception.status_code, 403, status)
            self.assertIn("只有提交线索的调查员本人", raised.exception.detail)

    async def test_submitter_can_still_edit(self):
        for status in ("待审批", "待客户审核"):
            updated = await self.edit(status, {"username": "codex-inv", "role": "user"})
            self.assertEqual(updated["data"]["shop_name"], "改后店铺", status)

    async def test_collection_stage_unchanged_for_admin(self):
        updated = await self.edit("待取证", {"username": "admin", "role": "admin"})
        self.assertEqual(updated["data"]["shop_name"], "改后店铺")


if __name__ == "__main__":
    unittest.main()

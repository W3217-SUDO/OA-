"""迁移案件的调查员、律师助理等账号字段可能是多人串（"fanyg,zhangwf"），每个人都算“我的案件”（分支2 按人对数发现）。"""
import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.permissions import _case_mine_scope_condition
from app.database import Base
from app.models import BusinessRecord


class CaseMineMultiPersonTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            rows = [
                (1, {"investigator_username": "fanyg,zhangwf"}),
                (2, {"assistant_username": "sugq、YUJD"}),
                (3, {"court_lawyer": "hehs； wangchanghong"}),
                (4, {"assistant_username": "fanygx"}),
            ]
            for case_id, data in rows:
                db.add(BusinessRecord(id=case_id, module="case", serial_no=f"AJ{case_id}", title="案件", status="文书准备",
                                      owner="someone-else", data={**data, "case_team_usernames": ["someone-else"]}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def mine(self, username):
        async with self.sessions() as db:
            condition = await _case_mine_scope_condition({"username": username}, db)
            return set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.module == "case", condition))).all())

    async def test_each_person_in_a_list_matches(self):
        self.assertEqual(await self.mine("fanyg"), {1})
        self.assertEqual(await self.mine("zhangwf"), {1})
        self.assertEqual(await self.mine("yujd"), {2})
        self.assertEqual(await self.mine("sugq"), {2})
        self.assertEqual(await self.mine("wangchanghong"), {3})
        # 只按整个账号比，不做包含匹配。
        self.assertEqual(await self.mine("fany"), set())
        self.assertEqual(await self.mine("fanygx"), {4})


if __name__ == "__main__":
    unittest.main()

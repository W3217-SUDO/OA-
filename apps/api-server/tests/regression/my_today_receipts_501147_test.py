"""501147：今日收文只列与本人有关案件的收文，不查出别人的案件；管理员也只看自己的案件。"""

import unittest
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.aws.my_today_receipts import list_my_today_receipts
from app.database import Base
from app.models import BusinessRecord


class MyTodayReceiptsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        today = date.today().isoformat()
        async with self.sessions() as db:
            mine = BusinessRecord(module="case", serial_no="AJ-MINE", title="我的案件", owner="boss", data={"handling_lawyer_usernames": ["lawyer"]})
            hearing = BusinessRecord(module="case", serial_no="AJ-HEAR", title="我开庭", owner="boss", data={"hearing_lawyer": "lawyer"})
            other = BusinessRecord(module="case", serial_no="AJ-OTHER", title="别人的案件", owner="boss", data={"handling_lawyer_usernames": ["someone"]})
            db.add_all([mine, hearing, other]); await db.flush()
            db.add_all([
                BusinessRecord(module="document", serial_no="SW1", title="传票.pdf", data={"direction": "收文", "uploaded_at": today, "case_id": mine.id}),
                BusinessRecord(module="document", serial_no="SW2", title="受理通知书.pdf", data={"direction": "收文", "uploaded_at": today, "case_ids": [hearing.id]}),
                BusinessRecord(module="document", serial_no="SW3", title="别人的传票.pdf", data={"direction": "收文", "uploaded_at": today, "case_id": other.id}),
                BusinessRecord(module="document", serial_no="SW4", title="昨天的.pdf", data={"direction": "收文", "uploaded_at": "2000-01-01", "case_id": mine.id}),
                BusinessRecord(module="document", serial_no="FW1", title="发文.pdf", data={"direction": "发文", "uploaded_at": today, "case_id": mine.id}),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _list(self, identity):
        async with self.sessions() as db:
            return await list_my_today_receipts(day=None, identity=identity, db=db)

    async def test_only_my_cases_today(self):
        result = await self._list({"username": "lawyer", "role": "user"})
        self.assertEqual(sorted(item["serial_no"] for item in result["items"]), ["SW1", "SW2"])

    async def test_admin_does_not_see_company_wide(self):
        result = await self._list({"username": "admin", "role": "admin", "role_ids": ["admin"]})
        self.assertEqual(result["items"], [], "管理员也只看与自己有关的案件")
        owner = await self._list({"username": "boss", "role": "user"})
        self.assertEqual(sorted(item["serial_no"] for item in owner["items"]), ["SW1", "SW2", "SW3"], "案件负责人看自己负责的全部案件")


if __name__ == "__main__":
    unittest.main()

"""BUG20261102013：案件任务只能发给本案人员；删除案件前不能还有费用和未完成任务。"""
import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.case_task_members import case_member_usernames, require_case_deletable, require_case_task_members
from app.database import Base
from app.models import BusinessRecord, User


class CaseTaskMemberTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            self.case = BusinessRecord(module="case", serial_no="GDMS1", title="案", owner="liff", data={
                "hearing_lawyer_username": "tgn", "handling_lawyer_usernames": ["shenjf"], "assistant_username": "qmy",
                "legacy_participants": [{"staff_name": "heteng"}], "customer_manager": "a，b"})
            db.add_all([self.case, User(username="other", display_name="外人", password_hash="x", role="user")])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def test_members_cover_registered_roles(self):
        self.assertTrue({"liff", "tgn", "shenjf", "qmy", "heteng", "a", "b"} <= case_member_usernames(self.case))

    async def test_outsider_cannot_get_case_task(self):
        async with self.sessions() as db:
            await require_case_task_members(["tgn", "qmy"], db, case_records=[self.case])
            with self.assertRaises(HTTPException) as caught:
                await require_case_task_members(["tgn", "other"], db, case_records=[self.case])
            self.assertEqual(caught.exception.status_code, 422)
            self.assertIn("外人", caught.exception.detail)
            self.assertIn("事务性任务", caught.exception.detail)
            # 转交等按任务上的案件判断；没关联案件的任务（事务性任务）不限制。
            with self.assertRaises(HTTPException):
                await require_case_task_members(["other"], db, task_data={"case_id": self.case.id})
            await require_case_task_members(["other"], db, task_data={})

    async def test_case_with_fee_or_open_task_cannot_be_deleted(self):
        async with self.sessions() as db:
            await require_case_deletable(self.case, db)
            db.add_all([
                BusinessRecord(module="finance", serial_no="FY1", title="", status="草稿", data={"case_id": self.case.id}),
                BusinessRecord(module="finance", serial_no="FY2", title="", status="已作废", data={"case_no": "GDMS1"}),
                BusinessRecord(module="task", serial_no="T1", title="", status="处理中", data={"case_no": "GDMS1"}),
                BusinessRecord(module="task", serial_no="T2", title="", status="已停止", data={"case_id": self.case.id}),
            ])
            await db.commit()
            with self.assertRaises(HTTPException) as caught:
                await require_case_deletable(self.case, db)
            detail = caught.exception.detail
            self.assertIn("FY1", detail); self.assertNotIn("FY2", detail)
            self.assertIn("T1", detail); self.assertNotIn("T2", detail)


if __name__ == "__main__":
    unittest.main()

"""BUG20261030016：线索审批连点不再重复审批，第二次提交提示已审批。"""
import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import ClueReviewInput, customer_review_investigation_clue, review_investigation_clue
from app.models import BusinessRecord, User, WorkflowEvent
from tests.personnel_role_fixture import bind_system_role_pages

ADMIN = {"username": "admin", "role": "admin"}


class ClueReviewNoDuplicateTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理员", department="上海", password_hash="x", role="admin"))
            self.ids = {}
            for key, extra in (("internal", {}), ("customer", {"customer_review": True})):
                clue = BusinessRecord(module="clue", serial_no=f"CODEX-1030-016-{key}", title="", customer="CODEX客户",
                                      status="待审批", owner="admin", department="上海", data={"shop_name": "店铺", **extra})
                db.add(clue)
                await db.flush()
                self.ids[key] = clue.id
            await db.commit()
        await bind_system_role_pages(self.sessions)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def call(self, endpoint, key):
        async with self.sessions() as db:
            return await endpoint(self.ids[key], ClueReviewInput(approved=True, comment="同意审批"), ADMIN, db)

    async def actions(self, key):
        async with self.sessions() as db:
            return list((await db.scalars(select(WorkflowEvent.action).where(WorkflowEvent.record_id == self.ids[key]))).all())

    async def test_second_internal_approval_is_refused(self):
        self.assertEqual((await self.call(review_investigation_clue, "internal"))["status"], "待取证")
        with self.assertRaises(HTTPException) as raised:
            await self.call(review_investigation_clue, "internal")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("请勿重复提交", raised.exception.detail)
        self.assertEqual((await self.actions("internal")).count("线索审批通过"), 1)

    async def test_second_customer_approval_is_refused(self):
        self.assertEqual((await self.call(review_investigation_clue, "customer"))["status"], "待客户审核")
        with self.assertRaises(HTTPException) as raised:
            await self.call(review_investigation_clue, "customer")
        self.assertIn("请勿重复提交", raised.exception.detail)
        self.assertEqual((await self.call(customer_review_investigation_clue, "customer"))["status"], "待取证")
        with self.assertRaises(HTTPException) as raised:
            await self.call(customer_review_investigation_clue, "customer")
        self.assertIn("请勿重复提交", raised.exception.detail)
        self.assertEqual((await self.actions("customer")).count("客户审核通过"), 1)


if __name__ == "__main__":
    unittest.main()

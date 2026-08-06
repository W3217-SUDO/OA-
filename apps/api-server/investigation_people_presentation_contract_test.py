"""Regression coverage for investigation customer-manager and reviewer presentation."""

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _contract_customer_record_dict
from app.models import BusinessRecord, User


class InvestigationPeoplePresentationContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_investigation_projection_uses_display_names_without_changing_authorization_data(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="manager-a", display_name="张三", department="上海", role="user", password_hash="x"),
                User(username="manager-b", display_name="李四", department="上海", role="user", password_hash="x"),
                User(username="reviewer-a", display_name="王五", department="上海", role="user", password_hash="x"),
                User(username="customer-reviewer", display_name="fwl", department="上海", role="user", password_hash="x"),
            ])
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-INV-PEOPLE-001", title="线索", customer="CODEX客户",
                status="待客户审核", owner="manager-a", department="上海", data={
                "customer_managers": ["manager-a", "manager-b"],
                    "reviewer": "reviewer-a", "customer_reviewer": "customer-reviewer",
                    "investigator": "manager-a", "source_owner": "manager-b", "assigner": "reviewer-a",
                },
            )
            db.add(clue)
            await db.commit()
            result = await _contract_customer_record_dict(clue, None, db)

        self.assertEqual(result["data"]["customer_manager_display_name"], "张三、李四")
        self.assertEqual(result["data"]["customer_manager"], "张三、李四（审核人：fwl）")
        self.assertEqual(result["data"]["reviewer_display_name"], "王五")
        self.assertEqual(result["data"]["customer_reviewer_display_name"], "fwl")
        self.assertEqual(result["owner_display_name"], "张三")
        self.assertEqual(result["data"]["investigator_display_name"], "张三")
        self.assertEqual(result["data"]["source_owner_display_name"], "李四")
        self.assertEqual(result["data"]["assigner_display_name"], "王五")
        self.assertEqual(clue.data["customer_managers"], ["manager-a", "manager-b"])
        self.assertEqual(clue.data["reviewer"], "reviewer-a")


if __name__ == "__main__":
    unittest.main()

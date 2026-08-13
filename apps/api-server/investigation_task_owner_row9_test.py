import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import list_records
from app.models import BusinessRecord, User


class InvestigationTaskOwnerRow9Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_non_admin_assigned_view_only_returns_own_investigation_subtasks(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="fwl", display_name="范文玲", department="调查部", password_hash="x", role="manager"),
                User(username="lawyer2", display_name="律师助理2", department="调查部", password_hash="x", role="user"),
                User(username="admin", display_name="管理员", department="管理部", password_hash="x", role="admin"),
                BusinessRecord(
                    module="task", serial_no="RW-ROW9-FWL", title="范文玲调查子任务",
                    customer="CODEX客户", status="待接收", owner="fwl", department="调查部",
                    data={"investigation_record_id": 9001, "initiator": "admin"},
                ),
                BusinessRecord(
                    module="task", serial_no="RW-ROW9-LAWYER2", title="律师助理2调查子任务",
                    customer="CODEX客户", status="待接收", owner="lawyer2", department="调查部",
                    data={"investigation_record_id": 9001, "initiator": "fwl", "assigner": "fwl"},
                ),
                BusinessRecord(
                    module="task", serial_no="RW-ROW9-PLAIN", title="范文玲普通任务",
                    customer="CODEX客户", status="待接收", owner="fwl", department="调查部",
                    data={"initiator": "admin"},
                ),
            ])
            await db.commit()

            mine = await list_records(
                module="task", keyword="", record_status="", scope="all", statuses="",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="assigned", page=1, page_size=100,
                identity={"username": "fwl", "role": "manager"}, db=db,
            )
            published = await list_records(
                module="task", keyword="", record_status="", scope="all", statuses="",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="published", page=1, page_size=100,
                identity={"username": "fwl", "role": "manager"}, db=db,
            )
            admin = await list_records(
                module="task", keyword="", record_status="", scope="all", statuses="",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="assigned", page=1, page_size=100,
                identity={"username": "admin", "role": "admin"}, db=db,
            )

        self.assertEqual({item["serial_no"] for item in mine["items"]}, {"RW-ROW9-FWL"})
        self.assertEqual({item["serial_no"] for item in published["items"]}, {"RW-ROW9-LAWYER2"})
        self.assertEqual(
            {item["serial_no"] for item in admin["items"]},
            {"RW-ROW9-FWL", "RW-ROW9-LAWYER2"},
        )


if __name__ == "__main__":
    unittest.main()

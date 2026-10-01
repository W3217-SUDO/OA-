import unittest
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import InvestigationTaskInput, create_investigation_task
from app.models import BusinessRecord, User


class InvestigationSubtaskRegionRow8Test(unittest.IsolatedAsyncioTestCase):
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

    async def test_explicit_subtask_region_overrides_parent_region(self):
        today = date.today()
        parent_end = today + timedelta(days=60)
        task_start = today + timedelta(days=1)
        task_end = today + timedelta(days=30)
        async with self.sessions() as db:
            db.add_all(
                [
                    User(
                        username="admin",
                        display_name="管理员",
                        department="总部",
                        password_hash="x",
                        role="admin",
                    ),
                    User(
                        username="investigator",
                        display_name="调查员甲",
                        department="调查部",
                        password_hash="x",
                        role="user",
                    ),
                ]
            )
            contract = BusinessRecord(
                module="contract",
                serial_no="HT-CODEX-813-R8",
                title="区域调查合同",
                customer="CODEX-813-R8 客户",
                status="审批通过",
                owner="admin",
                department="总部",
                data={},
            )
            db.add(contract)
            await db.flush()
            investigation = BusinessRecord(
                module="investigation",
                serial_no="DC-CODEX-813-R8",
                title="全国调查父任务",
                customer="CODEX-813-R8 客户",
                status="待分配",
                owner="admin",
                department="总部",
                data={
                    "contract_id": contract.id,
                    "contract_no": contract.serial_no,
                    "region": "全国",
                    "authorization_scope": "全国",
                    "authorized_from": today.isoformat(),
                    "authorized_to": parent_end.isoformat(),
                },
            )
            db.add(investigation)
            await db.commit()

            created = await create_investigation_task(
                investigation.id,
                InvestigationTaskInput(
                    title="上海调查子任务",
                    owner="investigator",
                    deadline=task_end,
                    start_date=task_start,
                    end_date=task_end,
                    province="上海市",
                    city="市辖区",
                    district="浦东新区",
                    authorization_scope="上海市、浦东新区",
                ),
                {"username": "admin", "role": "admin"},
                db,
            )

        self.assertEqual(created["data"]["region"], "上海市 市辖区 浦东新区")
        self.assertEqual(created["data"]["authorization_scope"], "上海市 市辖区 浦东新区")
        self.assertEqual(created["data"]["investigation_regions"], [["上海市", "市辖区"]])
        self.assertEqual(created["data"]["province"], "上海市")
        self.assertEqual(created["data"]["city"], "市辖区")
        self.assertEqual(created["data"]["district"], "浦东新区")
        self.assertEqual(created["data"]["authorized_from"], today.isoformat())
        self.assertEqual(created["data"]["authorized_to"], parent_end.isoformat())
        self.assertEqual(created["data"]["start_date"], task_start.isoformat())
        self.assertEqual(created["data"]["end_date"], task_end.isoformat())


if __name__ == "__main__":
    unittest.main()

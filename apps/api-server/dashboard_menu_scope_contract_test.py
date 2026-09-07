import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard
from app.models import RolePermission, User


IDENTITY = {
    "username": "contract-only-user",
    "role": "user",
    "role_ids": ["user"],
    "display_name": "合同用户",
    "department": "测试部",
}


class DashboardMenuScopeContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_dashboard_does_not_fail_when_finance_menu_is_not_granted(self):
        async with self.sessions() as db:
            db.add_all([
                User(
                    username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"], role="user", role_ids=["user"],
                    password_hash="test", is_active=True,
                ),
                RolePermission(
                    role="user", display_name="合同用户", data_scope="本人及共享数据",
                    menu_keys=["contract"], field_keys=[],
                ),
            ])
            await db.commit()

            result = await dashboard(IDENTITY, db)

        metrics = {item["key"]: item["value"] for item in result["metrics"]}
        self.assertEqual(metrics["refund-pending"], "0件")
        self.assertEqual(metrics["official-fee-unpaid"], "0件")
        self.assertEqual(metrics["official-fee-unreceived"], "0.00元")


if __name__ == "__main__":
    unittest.main()

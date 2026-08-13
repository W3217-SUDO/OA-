import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import list_system_parameter_options
from app.models import SystemParameter


IDENTITY = {"username": "admin", "role": "admin"}


class NotaryOfficeOptionsContractTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_only_active_notary_offices_are_returned(self):
        async with self.sessions() as db:
            db.add_all([
                SystemParameter(
                    category="notary_office", code="ACTIVE", name="Active Office",
                    is_active=True, sort_order=1,
                ),
                SystemParameter(
                    category="notary_office", code="DISABLED", name="Disabled Office",
                    is_active=False, sort_order=2,
                ),
            ])
            await db.commit()
            result = await list_system_parameter_options(
                "notary_office", IDENTITY, db,
            )

        self.assertEqual([item["name"] for item in result["items"]], ["Active Office"])

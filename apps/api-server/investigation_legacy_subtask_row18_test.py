import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import InvestigationTaskInput, create_investigation_task
from app.models import BusinessRecord, User


class InvestigationLegacySubtaskRow18Test(unittest.IsolatedAsyncioTestCase):
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

    async def _add_users(self, db):
        db.add_all([
            User(username="admin", display_name="管理员", department="总部", password_hash="x", role="admin"),
            User(username="investigator", display_name="调查员", department="调查部", password_hash="x", role="user"),
        ])

    def _payload(self):
        return InvestigationTaskInput(
            title="历史调查子任务",
            owner="investigator",
            deadline=date(2026, 9, 12),
            start_date=date(2026, 8, 13),
            end_date=date(2026, 9, 12),
            province="上海市",
            city="市辖区",
            district="浦东新区",
        )

    async def test_legacy_investigation_without_contract_can_create_subtask(self):
        async with self.sessions() as db:
            await self._add_users(db)
            source = BusinessRecord(
                module="investigation", serial_no="RW2413300774776",
                title="旧系统迁移调查", customer="测试9.23", status="待分配",
                owner="admin", department="总部",
                data={
                    "migration_source": "8091-local-PRD_CRM_GD_20200211",
                    "legacy_investigation_id": 1330,
                    "authorized_from": "2024-10-15",
                    "authorized_to": "2026-10-31",
                    "authorization_scope": "区域",
                },
            )
            db.add(source)
            await db.commit()

            created = await create_investigation_task(
                source.id, self._payload(), {"username": "admin", "role": "admin"}, db
            )

        self.assertEqual(created["data"]["investigation_record_id"], source.id)
        self.assertIsNone(created["data"]["contract_record_id"])
        self.assertEqual(created["data"]["contract_no"], "")
        self.assertEqual(created["data"]["region"], "上海市 市辖区 浦东新区")

    async def test_current_expired_investigation_is_rejected(self):
        async with self.sessions() as db:
            await self._add_users(db)
            source = BusinessRecord(
                module="investigation", serial_no="DC202409010001",
                title="过期当前调查", customer="当前客户", status="待分配",
                owner="admin", department="总部",
                data={
                    "contract_id": 999,
                    "authorized_to": "2024-10-31",
                },
            )
            db.add(source)
            await db.commit()

            with self.assertRaises(HTTPException) as raised:
                await create_investigation_task(
                    source.id, self._payload(), {"username": "admin", "role": "admin"}, db
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "该任务已过期，不允许新建子任务")

    async def test_legacy_expired_investigation_is_also_rejected(self):
        async with self.sessions() as db:
            await self._add_users(db)
            source = BusinessRecord(
                module="investigation", serial_no="RW2411260046472",
                title="过期历史调查", customer="历史客户", status="待分配",
                owner="admin", department="总部",
                data={
                    "migration_source": "legacy",
                    "legacy_investigation_id": 1,
                    "authorized_to": "2024-11-23T00:00:00+08:00",
                },
            )
            db.add(source)
            await db.commit()

            with self.assertRaises(HTTPException) as raised:
                await create_investigation_task(
                    source.id, self._payload(), {"username": "admin", "role": "admin"}, db
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "该任务已过期，不允许新建子任务")

    async def test_current_investigation_without_contract_is_still_rejected(self):
        async with self.sessions() as db:
            await self._add_users(db)
            source = BusinessRecord(
                module="investigation", serial_no="DC202609010001",
                title="当前调查", customer="当前客户", status="待分配",
                owner="admin", department="总部", data={},
            )
            db.add(source)
            await db.commit()

            with self.assertRaises(HTTPException) as raised:
                await create_investigation_task(
                    source.id, self._payload(), {"username": "admin", "role": "admin"}, db
                )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "创建调查任务前必须绑定同客户合同")


if __name__ == "__main__":
    unittest.main()

"""8.13 row 10: legacy clue-report fields remain writable after create and edit."""

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import RecordInput, RecordUpdate, create_investigation_record, update_investigation_record
from app.models import BusinessRecord, User


IDENTITY = {"username": "admin", "role": "admin"}


class InvestigationClueLegacyFieldsRow10Test(unittest.IsolatedAsyncioTestCase):
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

    async def test_create_and_edit_keep_legacy_clue_report_fields(self):
        async with self.sessions() as db:
            db.add(User(
                username="admin", display_name="管理员", department="上海",
                password_hash="x", role="admin",
            ))
            source_task = BusinessRecord(
                module="task", serial_no="RW-CODEX-813-R10", title="来源调查任务",
                customer="CODEX客户", status="进行中", owner="admin", department="上海",
                data={"investigation_record_id": 1},
            )
            db.add(source_task)
            await db.commit()

            created = await create_investigation_record(
                RecordInput(
                    module="clue", serial_no="ignored", title="CODEX店铺侵权线索",
                    customer="不应覆盖来源客户", owner="other",
                    description="旧系统备注", data={
                        "source_task_id": source_task.id,
                        "infringement_method": "电商平台",
                        "sales_channel": "淘宝",
                        "platform": "淘宝",
                        "shop_name": "CODEX旗舰店",
                        "shop_id": "codex-shop",
                        "store_url": "https://example.test/codex-shop",
                        "has_product": False,
                        "investigated_at": "2026-08-13",
                        "investigation_assistant": "assistant",
                    },
                ),
                IDENTITY, db,
            )
            edited = await update_investigation_record(
                created["id"],
                RecordUpdate(data={
                    "sales_channel": "天猫",
                    "platform": "天猫",
                    "shop_name": "CODEX天猫旗舰店",
                    "has_product": True,
                }),
                IDENTITY,
                db,
            )

        self.assertEqual(created["customer"], "CODEX客户")
        self.assertEqual(created["data"]["sales_channel"], "淘宝")
        self.assertEqual(created["data"]["shop_name"], "CODEX旗舰店")
        self.assertFalse(created["data"]["has_product"])
        self.assertEqual(edited["data"]["sales_channel"], "天猫")
        self.assertEqual(edited["data"]["shop_name"], "CODEX天猫旗舰店")
        self.assertTrue(edited["data"]["has_product"])


if __name__ == "__main__":
    unittest.main()

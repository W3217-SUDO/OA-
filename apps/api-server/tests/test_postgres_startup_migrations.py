"""独立 PostgreSQL 测试库中的真实迁移、锁和回填验证。"""

import asyncio
import multiprocessing
import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
from app.core.startup_backfills import HISTORICAL_BACKFILL_REVISION, rerun_historical_backfills
from app.core.startup_data import initialize_startup_data
from app.core.startup_migrations import (
    SCHEMA_BOOTSTRAP_REVISION, lock_startup_transaction, migrate_startup_schema,
)
from app.database import Base
from app.legacy_schema import create_full_legacy_schema
from app.models import BusinessRecord, WorkflowEvent


POSTGRES_URL = os.environ.get("OA_TEST_POSTGRES_URL")


def _postgres_worker(database_url: str, schema: str, fail: bool, result_queue) -> None:
    async def run() -> None:
        engine = create_async_engine(
            database_url, connect_args={"server_settings": {"search_path": schema}},
        )
        try:
            def upgrade(connection) -> None:
                _upgrade_schema(connection)
                if fail:
                    raise RuntimeError("模拟 PostgreSQL 迁移失败")

            await migrate_startup_schema(engine, upgrade)
        finally:
            await engine.dispose()

    try:
        asyncio.run(run())
        result_queue.put("ok")
    except RuntimeError as exc:
        result_queue.put(str(exc))
    except Exception as exc:
        result_queue.put(f"{type(exc).__name__}: {exc}")


@unittest.skipUnless(POSTGRES_URL, "需要显式设置 OA_TEST_POSTGRES_URL")
class PostgreSQLStartupMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.schema = f"oa_test_enterprise_reliability_{uuid4().hex[:12]}"
        self.admin_engine = create_async_engine(POSTGRES_URL)
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(
            POSTGRES_URL, connect_args={"server_settings": {"search_path": self.schema}},
        )

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin_engine.dispose()

    async def test_empty_schema_failure_rollback_and_repeated_startup(self) -> None:
        def fail_after_upgrade(connection) -> None:
            _upgrade_schema(connection)
            raise RuntimeError("模拟 PostgreSQL 迁移失败")

        with self.assertRaisesRegex(RuntimeError, "模拟 PostgreSQL 迁移失败"):
            await migrate_startup_schema(self.engine, fail_after_upgrade)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = current_schema()"
            ))).scalar_one(), 0)

        await migrate_startup_schema(self.engine, _upgrade_schema)
        await migrate_startup_schema(self.engine, fail_after_upgrade)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        with patch.object(settings, "initial_admin_password", "EnterpriseReliability123!"):
            await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)

            async def fail_if_rerun(_session) -> int:
                raise RuntimeError("已登记修正不应重跑")

            await initialize_startup_data(sessions, fail_if_rerun)
        async with self.engine.connect() as connection:
            revisions = set((await connection.execute(text(
                "SELECT key FROM schema_migrations"
            ))).scalars().all())
            self.assertIn(SCHEMA_BOOTSTRAP_REVISION, revisions)
            self.assertIn(HISTORICAL_BACKFILL_REVISION, revisions)
            self.assertEqual((await connection.execute(text("SELECT count(*) FROM users"))).scalar_one(), 1)
            self.assertEqual((await connection.execute(text("SELECT count(*) FROM business_records"))).scalar_one(), 0)

    async def test_existing_schema_upgrade_and_explicit_reentrant_backfill(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(create_full_legacy_schema)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with sessions() as session:
            session.add(BusinessRecord(
                module="contract", serial_no="ENTERPRISE-RELIABILITY-PG-OLD-CONTRACT",
                title="旧合同", customer="测试客户", status="已通过", owner="admin", data={},
            ))
            await session.commit()

        await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT status FROM business_records "
                "WHERE serial_no = 'ENTERPRISE-RELIABILITY-PG-OLD-CONTRACT'"
            ))).scalar_one(), "审批通过")

        with patch.object(settings, "initial_admin_password", "EnterpriseReliability123!"):
            await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)
        async with sessions() as session:
            case = BusinessRecord(
                module="case", serial_no="ENTERPRISE-RELIABILITY-PG-CASE",
                title="历史转案", customer="测试客户", status="等待公证书",
                owner="admin", data={"batch_converted": True},
            )
            session.add(case)
            await session.flush()
            session.add(WorkflowEvent(
                record_id=case.id, action="线索生成案件", to_status="等待公证书",
                operator="admin", created_at=datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc),
            ))
            await session.commit()
        with patch.object(settings, "initial_admin_password", "EnterpriseReliability123!"):
            await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)
        async with sessions() as session:
            case = await session.scalar(select(BusinessRecord).where(
                BusinessRecord.serial_no == "ENTERPRISE-RELIABILITY-PG-CASE",
            ))
            self.assertNotIn("case_register_date", case.data)
        await rerun_historical_backfills(sessions, _backfill_clue_generated_case_register_dates)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT data ->> 'case_register_date' FROM business_records "
                "WHERE serial_no = 'ENTERPRISE-RELIABILITY-PG-CASE'"
            ))).scalar_one(), "2026-09-01")

    async def test_postgres_transaction_lock_and_concurrent_processes(self) -> None:
        acquired = asyncio.Event()

        async def competing_lock() -> None:
            async with self.engine.begin() as connection:
                await lock_startup_transaction(connection)
                acquired.set()

        async with self.engine.begin() as connection:
            await lock_startup_transaction(connection)
            competing = asyncio.create_task(competing_lock())
            await asyncio.sleep(0.3)
            self.assertFalse(acquired.is_set())
        await asyncio.wait_for(competing, timeout=10)
        self.assertTrue(acquired.is_set())

        context = multiprocessing.get_context("spawn")

        def run_workers(failure_modes: tuple[bool, ...]) -> list[str]:
            result_queue = context.Queue()
            workers = [context.Process(
                target=_postgres_worker,
                args=(POSTGRES_URL, self.schema, failure_mode, result_queue),
            ) for failure_mode in failure_modes]
            for worker in workers:
                worker.start()
            try:
                results = [result_queue.get(timeout=120) for _ in workers]
                for worker in workers:
                    worker.join(timeout=120)
                    self.assertEqual(worker.exitcode, 0)
                return results
            finally:
                for worker in workers:
                    if worker.is_alive():
                        worker.terminate()
                        worker.join(timeout=10)
                result_queue.close()

        self.assertEqual(await asyncio.to_thread(run_workers, (True,)), ["模拟 PostgreSQL 迁移失败"])
        self.assertEqual(await asyncio.to_thread(run_workers, (False, False)), ["ok", "ok"])
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM schema_migrations WHERE key = :key"
            ), {"key": SCHEMA_BOOTSTRAP_REVISION})).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()

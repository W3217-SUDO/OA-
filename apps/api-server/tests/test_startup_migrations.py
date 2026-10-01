"""隔离数据库中的启动迁移事务、幂等和进程并发回归测试。"""

import asyncio
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
from app.core.startup_data import initialize_startup_data
from app.core.startup_migrations import migrate_startup_schema
from app.models import BusinessRecord
from scripts.seed_demo_data import seed_demo_data


def _schema_worker(database_url: str, fail_after_upgrade: bool, result_queue) -> None:
    async def run() -> None:
        engine = create_async_engine(database_url)
        try:
            def upgrade(connection) -> None:
                _upgrade_schema(connection)
                if fail_after_upgrade:
                    raise RuntimeError("模拟结构迁移中断")

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


class StartupMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="oa-test-enterprise-reliability-")
        self.database_url = f"sqlite+aiosqlite:///{Path(self.directory.name) / 'startup.db'}"
        self.engine = create_async_engine(self.database_url)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.directory.cleanup()

    async def test_schema_repeat_and_failure_rollback(self) -> None:
        def fail_after_upgrade(connection) -> None:
            _upgrade_schema(connection)
            raise RuntimeError("模拟结构迁移中断")

        with self.assertRaisesRegex(RuntimeError, "模拟结构迁移中断"):
            await migrate_startup_schema(self.engine, fail_after_upgrade)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
            ))).scalar_one(), 0)

        snapshots = []
        for _ in range(2):
            await migrate_startup_schema(self.engine, _upgrade_schema)
            async with self.engine.connect() as connection:
                snapshots.append((
                    (await connection.execute(text("SELECT count(*) FROM schema_migrations"))).scalar_one(),
                    (await connection.execute(text(
                        "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
                    ))).scalar_one(),
                ))
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertGreater(snapshots[0][0], 0)
        self.assertGreater(snapshots[0][1], 0)

        def fail_if_revision_repeats(_connection) -> None:
            raise RuntimeError("已登记的结构迁移不应重跑")

        await migrate_startup_schema(self.engine, fail_if_revision_repeats)

    async def test_data_failure_rolls_back_then_repeat_is_idempotent(self) -> None:
        await migrate_startup_schema(self.engine, _upgrade_schema)
        session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

        async def fail_after_backfill(_session) -> int:
            raise RuntimeError("模拟数据回填中断")

        with patch.object(settings, "seed_demo_data", False), patch.object(
            settings, "initial_admin_password", "EnterpriseReliability123!"
        ):
            with self.assertRaisesRegex(RuntimeError, "模拟数据回填中断"):
                await initialize_startup_data(session_factory, fail_after_backfill)
            async with self.engine.connect() as connection:
                self.assertEqual((await connection.execute(text("SELECT count(*) FROM users"))).scalar_one(), 0)
                self.assertEqual((await connection.execute(text("SELECT count(*) FROM system_menus"))).scalar_one(), 0)

            async with session_factory() as session:
                session.add(BusinessRecord(
                    module="seal", serial_no="ENTERPRISE-RELIABILITY-SEAL-1",
                    title="启动印章关联校验", customer="", status="草稿",
                    owner="admin", department="上海分所", data={"seal_type": "公章"},
                ))
                await session.commit()
            snapshots = []
            for _ in range(2):
                await initialize_startup_data(session_factory, _backfill_clue_generated_case_register_dates)
                async with self.engine.connect() as connection:
                    snapshots.append((
                        (await connection.execute(text("SELECT count(*) FROM users"))).scalar_one(),
                        (await connection.execute(text("SELECT count(*) FROM system_menus"))).scalar_one(),
                    ))
            self.assertEqual(snapshots[0], snapshots[1])
            self.assertEqual(snapshots[0][0], 1)
            self.assertGreater(snapshots[0][1], 0)
            await initialize_startup_data(session_factory, fail_after_backfill)
            async with self.engine.connect() as connection:
                self.assertIsNotNone((await connection.execute(text(
                    "SELECT json_extract(data, '$.seal_asset_id') FROM business_records "
                    "WHERE serial_no = 'ENTERPRISE-RELIABILITY-SEAL-1'"
                ))).scalar_one())

    async def test_demo_seed_keeps_record_and_event_counts_on_repeat(self) -> None:
        await migrate_startup_schema(self.engine, _upgrade_schema)
        session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        snapshots = []
        with patch.object(settings, "initial_admin_password", "EnterpriseReliability123!"):
            await initialize_startup_data(session_factory, _backfill_clue_generated_case_register_dates)
            async with self.engine.connect() as connection:
                self.assertEqual((await connection.execute(text(
                    "SELECT count(*) FROM business_records"
                ))).scalar_one(), 0)
            for _ in range(2):
                async with session_factory() as session:
                    await seed_demo_data(session)
                    await session.commit()
                await initialize_startup_data(session_factory, _backfill_clue_generated_case_register_dates)
                async with self.engine.connect() as connection:
                    snapshots.append((
                        (await connection.execute(text("SELECT count(*) FROM business_records"))).scalar_one(),
                        (await connection.execute(text("SELECT count(*) FROM workflow_events"))).scalar_one(),
                    ))
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertGreater(snapshots[0][0], 0)
        self.assertGreater(snapshots[0][1], 0)

    async def test_date_backfill_pages_large_case_set(self) -> None:
        await migrate_startup_schema(self.engine, _upgrade_schema)
        session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all(BusinessRecord(
                module="case", serial_no=f"ENTERPRISE-RELIABILITY-CASE-{number:04d}",
                title="历史转案", customer="测试客户", status="等待公证书",
                owner="admin", data={"batch_converted": True},
            ) for number in range(405))
            await session.commit()
            self.assertEqual(await _backfill_clue_generated_case_register_dates(session), 405)
            await session.commit()
            self.assertEqual(await _backfill_clue_generated_case_register_dates(session), 0)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM business_records "
                "WHERE json_extract(data, '$.case_register_date') IS NOT NULL"
            ))).scalar_one(), 405)

    async def test_parallel_processes_and_failed_process_retry(self) -> None:
        context = multiprocessing.get_context("spawn")

        def run_workers(failure_modes: tuple[bool, ...]) -> list[str]:
            result_queue = context.Queue()
            workers = [context.Process(
                target=_schema_worker,
                args=(self.database_url, failure_mode, result_queue),
            ) for failure_mode in failure_modes]
            for worker in workers:
                worker.start()
            try:
                results = [result_queue.get(timeout=90) for _ in workers]
                for worker in workers:
                    worker.join(timeout=90)
                    self.assertEqual(worker.exitcode, 0)
                return results
            finally:
                for worker in workers:
                    if worker.is_alive():
                        worker.terminate()
                        worker.join(timeout=10)
                result_queue.close()

        self.assertEqual(await asyncio.to_thread(run_workers, (True,)), ["模拟结构迁移中断"])
        self.assertEqual(await asyncio.to_thread(run_workers, (False, False)), ["ok", "ok"])
        self.assertEqual(await asyncio.to_thread(run_workers, (True,)), ["ok"])
        async with self.engine.connect() as connection:
            self.assertGreater((await connection.execute(text(
                "SELECT count(*) FROM schema_migrations"
            ))).scalar_one(), 0)


if __name__ == "__main__":
    unittest.main()

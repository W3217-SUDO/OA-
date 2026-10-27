"""隔离数据库中的启动迁移事务、幂等和进程并发回归测试。"""

import asyncio
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch

from sqlalchemy import Column, MetaData, Table, inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
from app.core.startup_data import initialize_startup_data
from app.core.startup_migrations import (
    DASHBOARD_FINANCE_REVISION, DASHBOARD_REVISION, NOTIFICATION_DELIVERY_REVISION,
    RECORD_READ_MODEL_REVISION, SCHEMA_BOOTSTRAP_REVISION, migrate_startup_schema,
)
from app.models import BusinessRecord, IncomingPayment
from app.database import Base
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


class IncomingFinanceMigrationAssertions:
    async def _prepare_old_incoming_schema(self):
        from app.core.dashboard_finance_read_model_migration import upgrade_dashboard_finance_read_model
        from app.core.dashboard_revision_migration import upgrade_dashboard_revision
        from app.core.record_read_model_migration import upgrade_record_read_model

        added = {"finance_scope", "legacy_finance_record_id", "payment_method", "local_allocation_summary"}
        self.old_incoming = Table("incoming_payments", MetaData(), *(
            Column(column.name, column.type, primary_key=column.primary_key, nullable=column.nullable,
                   default=column.default, server_default=column.server_default)
            for column in IncomingPayment.__table__.columns if column.name not in added
        ))
        def prepare(connection):
            Base.metadata.create_all(connection, tables=[table for table in Base.metadata.sorted_tables if table.name != "incoming_payments"])
            self.old_incoming.create(connection)
            upgrade_record_read_model(connection)
            upgrade_dashboard_finance_read_model(connection)
            upgrade_dashboard_revision(connection)
            connection.execute(text("CREATE TABLE schema_migrations (key VARCHAR(128) PRIMARY KEY)"))
            connection.execute(text("INSERT INTO schema_migrations (key) VALUES (:key)"), [
                {"key": key} for key in (SCHEMA_BOOTSTRAP_REVISION, NOTIFICATION_DELIVERY_REVISION,
                                        RECORD_READ_MODEL_REVISION, DASHBOARD_FINANCE_REVISION, DASHBOARD_REVISION)
            ])
            connection.execute(self.old_incoming.insert().values(id=1, receipt_no="EXISTING-INCOMING-MIGRATION",
                received_date=date(2026, 10, 16), amount=321.25, allocated_amount=12.5, status="历史原状态",
                source_kind="hz_crm_20260930", payer_name="独立迁移验证", operator="admin", remark="旧值不改",
                allocations=[{"amount": 12.5, "source_object": {"SeqId": 9, "ArchiveAmountSettlementStatus": 30}, "note": "原分配保留"}]))
            return tuple(connection.execute(self.old_incoming.select()).one())
        async with self.engine.begin() as connection:
            self.old_snapshot = await connection.run_sync(prepare)

    async def test_incoming_finance_revision_upgrades_bootstrapped_old_table_without_backfills(self):
        from app.core.incoming_finance_schema_migration import MIGRATION_REVISION

        await self._prepare_old_incoming_schema()
        def no_bootstrap(_connection):
            raise AssertionError("已登记 bootstrap 不得重跑")
        await migrate_startup_schema(self.engine, no_bootstrap)
        with patch("app.core.startup_migrations.upgrade_incoming_finance_schema", side_effect=AssertionError("版本不得重跑")):
            await migrate_startup_schema(self.engine, no_bootstrap)
        async with self.engine.connect() as connection:
            def verify(sync):
                columns = {item["name"]: item for item in inspect(sync).get_columns("incoming_payments")}
                for name in ("finance_scope", "legacy_finance_record_id", "local_allocation_summary"):
                    self.assertTrue(columns[name]["nullable"])
                self.assertFalse(columns["payment_method"]["nullable"])
                self.assertEqual(columns["payment_method"]["type"].length, 100)
                self.assertIsNotNone(columns["payment_method"]["default"])
                indexes = {item["name"]: item["column_names"] for item in inspect(sync).get_indexes("incoming_payments")}
                for name in ("finance_scope", "legacy_finance_record_id"):
                    self.assertEqual(indexes["ix_incoming_payments_" + name], [name])
                references = [item for item in inspect(sync).get_foreign_keys("incoming_payments")
                              if item["constrained_columns"] == ["legacy_finance_record_id"]]
                self.assertEqual(len(references), 1)
                self.assertEqual(references[0]["referred_table"], "legacy_finance_records")
                self.assertEqual(references[0]["referred_columns"], ["id"])
                if sync.dialect.name == "sqlite":
                    rules = list(sync.execute(text("PRAGMA foreign_key_list(incoming_payments)")).mappings())
                    self.assertEqual([rule["on_delete"] for rule in rules if rule["from"] == "legacy_finance_record_id"], ["RESTRICT"])
                else:
                    self.assertEqual(references[0]["options"]["ondelete"], "RESTRICT")
                self.assertEqual(tuple(sync.execute(self.old_incoming.select()).one()), self.old_snapshot)
                self.assertEqual(tuple(sync.execute(text("SELECT finance_scope, legacy_finance_record_id, payment_method, local_allocation_summary FROM incoming_payments")).one()), (None, None, "", None))
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM schema_migrations WHERE key=:key"), {"key": MIGRATION_REVISION}), 1)
                # 21：含 2026-10-24 补装财务查询修订触发器、退费单编号索引与读模型案号索引三个修订，及 2026-10-26 问题反馈改日期编号。
                self.assertEqual(sync.scalar(text("SELECT count(*) FROM schema_migrations")), 22)
                sync.execute(self.old_incoming.insert().values(id=2, receipt_no="EXISTING-WRITER-COMPATIBILITY",
                    received_date=date(2026, 10, 16), amount=1, allocated_amount=0, status="待认领",
                    payer_name="独立旧写入", operator="admin"))
                self.assertEqual(sync.scalar(text("SELECT payment_method FROM incoming_payments WHERE id=2")), "")
            await connection.run_sync(verify)

    async def test_incoming_finance_revision_failure_rolls_back_and_retries(self):
        from app.core.incoming_finance_schema_migration import MIGRATION_REVISION, upgrade_incoming_finance_schema

        await self._prepare_old_incoming_schema()
        def fail_after_ddl(connection):
            upgrade_incoming_finance_schema(connection)
            raise RuntimeError("模拟回款结构迁移中断")
        def no_bootstrap(_connection):
            raise AssertionError("已登记 bootstrap 不得重跑")
        with patch("app.core.startup_migrations.upgrade_incoming_finance_schema", fail_after_ddl):
            with self.assertRaisesRegex(RuntimeError, "模拟回款结构迁移中断"):
                await migrate_startup_schema(self.engine, no_bootstrap)
        async with self.engine.connect() as connection:
            columns = await connection.run_sync(lambda sync: {item["name"] for item in inspect(sync).get_columns("incoming_payments")})
            self.assertNotIn("finance_scope", columns)
            self.assertNotIn("payment_method", columns)
            self.assertEqual((await connection.execute(text("SELECT count(*) FROM schema_migrations WHERE key=:key"), {"key": MIGRATION_REVISION})).scalar_one(), 0)
            self.assertEqual(tuple((await connection.execute(self.old_incoming.select())).one()), self.old_snapshot)
        await migrate_startup_schema(self.engine, no_bootstrap)


class StartupMigrationTests(IncomingFinanceMigrationAssertions, unittest.IsolatedAsyncioTestCase):
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

    async def test_finance_projection_revision_failure_is_atomic_on_sqlite(self) -> None:
        from app.core.startup_migrations import upgrade_dashboard_finance_read_model

        def fail_finance_upgrade(connection) -> None:
            upgrade_dashboard_finance_read_model(connection)
            raise RuntimeError("模拟费用关系迁移中断")

        with patch("app.core.startup_migrations.upgrade_dashboard_finance_read_model", fail_finance_upgrade):
            with self.assertRaisesRegex(RuntimeError, "模拟费用关系迁移中断"):
                await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
            ))).scalar_one(), 0)

        await migrate_startup_schema(self.engine, _upgrade_schema)
        await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM schema_migrations WHERE key = :revision"
            ), {"revision": DASHBOARD_FINANCE_REVISION})).scalar_one(), 1)
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE name = 'dashboard_finance_relations'"
            ))).scalar_one(), 0)

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

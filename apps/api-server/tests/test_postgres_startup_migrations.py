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
    DASHBOARD_FINANCE_REVISION, SCHEMA_BOOTSTRAP_REVISION, lock_startup_transaction, migrate_startup_schema,
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

    async def test_finance_projection_raw_values_metadata_and_rollback(self) -> None:
        from app.core.dashboard_finance_read_model import LINK_FIELDS, RAW_FIELDS

        await migrate_startup_schema(self.engine, _upgrade_schema)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        definitions = [
            ({}, False, True),
            ({"case_id": "007", "case_record_id": True, "case_no": " 案号 ",
              "contract_id": [None, {"nested": None}], "contract_record_id": 2 ** 100,
              "contract_no": {"value": "合同"}, "legacy_case_fee_id": 12.75,
              "legacy_fee_id": " +0012 ", "fee_type": "代理费"}, False, True),
            ({"fee_type_name": ["其他费用", None]}, True, True),
            ({"contract_object_id": 0}, True, True),
            ({"contract_object_id": ""}, True, True),
            ({"contract_object_id": None, "fee_type": None}, False, True),
            (None, True, False),
            (["非对象"], True, False),
        ]
        async with sessions() as session:
            records = [BusinessRecord(module="finance", serial_no=f"CODEX-PG-RELATION-{index}",
                title="服务费用", status="草稿", owner="admin", data=data)
                for index, (data, _, _) in enumerate(definitions)]
            session.add_all(records)
            await session.commit()
        async with self.engine.connect() as connection:
            for record, (data, candidate, is_object) in zip(records, definitions):
                row = (await connection.execute(text(
                    "SELECT * FROM dashboard_finance_relations WHERE record_id = :id"
                ), {"id": record.id})).mappings().one()
                expected = data if isinstance(data, dict) else {}
                for field in RAW_FIELDS:
                    self.assertEqual(row[field], expected.get(field))
                self.assertEqual(row["links"], [expected.get(field) for field in LINK_FIELDS])
                self.assertIs(row["is_candidate"], candidate)
                self.assertIs(row["data_is_object"], is_object)

        record_id = records[0].id
        async with self.engine.connect() as connection:
            transaction = await connection.begin()
            await connection.execute(text("UPDATE business_records SET title = '官费' WHERE id = :id"),
                                     {"id": record_id})
            self.assertTrue((await connection.execute(text(
                "SELECT is_candidate FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": record_id})).scalar_one())
            await transaction.rollback()
        async with self.engine.connect() as connection:
            self.assertFalse((await connection.execute(text(
                "SELECT is_candidate FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": record_id})).scalar_one())
        async with self.engine.begin() as connection:
            await connection.execute(text("UPDATE business_records SET title = '官费', status = '已删除' WHERE id = :id"),
                                     {"id": record_id})
            self.assertTrue((await connection.execute(text(
                "SELECT is_candidate FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": record_id})).scalar_one())
            await connection.execute(text("UPDATE business_records SET module = 'customer' WHERE id = :id"),
                                     {"id": record_id})
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": record_id})).scalar_one(), 0)
            await connection.execute(text("UPDATE business_records SET module = 'finance' WHERE id = :id"),
                                     {"id": record_id})
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": record_id})).scalar_one(), 1)
            await connection.execute(text("DELETE FROM business_records WHERE id = :id"), {"id": record_id})
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": record_id})).scalar_one(), 0)
        async with self.engine.begin() as connection:
            await connection.execute(text("TRUNCATE business_records CASCADE"))
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM dashboard_finance_relations"
            ))).scalar_one(), 0)

    async def test_finance_projection_existing_schema_failure_rolls_back_and_retries(self) -> None:
        from app.core.dashboard_finance_read_model_migration import (
            FUNCTION_NAMES, TABLE_NAME, upgrade_dashboard_finance_read_model,
        )

        await migrate_startup_schema(self.engine, _upgrade_schema)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with sessions() as session:
            fee = BusinessRecord(module="finance", serial_no="CODEX-PG-RELATION-BACKFILL",
                                 title="代理费", owner="admin", data={"case_no": " 原案号 ", "legacy_fee_id": True})
            session.add(fee)
            await session.commit()
        async with self.engine.begin() as connection:
            # 只在本任务隔离 schema 中模拟尚未安装候选投影的旧版本。
            await connection.execute(text(f"DROP TABLE {TABLE_NAME} CASCADE"))
            for function in FUNCTION_NAMES:
                await connection.execute(text(f"DROP FUNCTION {function}() CASCADE"))
            await connection.execute(text("DELETE FROM schema_migrations WHERE key = :revision"),
                                     {"revision": DASHBOARD_FINANCE_REVISION})
            source_before = (await connection.execute(text(
                "SELECT data::text FROM business_records WHERE id = :id"
            ), {"id": fee.id})).scalar_one()

        from app.core import dashboard_revision
        from app.core.dashboard_revision_migration import validate_dashboard_revision

        old_dependencies = tuple(name for name in dashboard_revision.DEPENDENCY_TABLES if name != TABLE_NAME)
        self.assertEqual(len(old_dependencies), 14)
        # 只移除新版本新增检查，旧版十四表、函数体和事务日志断言全部保留。
        with patch.object(dashboard_revision, "DEPENDENCY_TABLES", old_dependencies), patch(
            "app.core.dashboard_finance_read_model_migration.finance_integrity_sql", return_value="true",
        ):
            old_integrity_query = text(f"SELECT {dashboard_revision.integrity_sql()}")
            async with self.engine.connect() as connection:
                await connection.run_sync(validate_dashboard_revision)
                self.assertTrue((await connection.execute(old_integrity_query)).scalar_one())
                self.assertEqual((await connection.execute(text(
                    "SELECT count(*) FROM schema_migrations WHERE key = :revision"
                ), {"revision": dashboard_revision.MIGRATION_REVISION})).scalar_one(), 1)

        def fail_after_projection(connection) -> None:
            upgrade_dashboard_finance_read_model(connection)
            raise RuntimeError("模拟费用投影回填后中断")

        with patch("app.core.startup_migrations.upgrade_dashboard_finance_read_model", fail_after_projection):
            with self.assertRaisesRegex(RuntimeError, "模拟费用投影回填后中断"):
                await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            self.assertIsNone((await connection.execute(text("SELECT to_regclass(:name)"),
                {"name": f"{self.schema}.{TABLE_NAME}"})).scalar_one())
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM schema_migrations WHERE key = :revision"
            ), {"revision": DASHBOARD_FINANCE_REVISION})).scalar_one(), 0)
            self.assertEqual((await connection.execute(text(
                "SELECT data::text FROM business_records WHERE id = :id"
            ), {"id": fee.id})).scalar_one(), source_before)
        await migrate_startup_schema(self.engine, _upgrade_schema)
        await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            row = (await connection.execute(text(
                "SELECT case_no, legacy_fee_id FROM dashboard_finance_relations WHERE record_id = :id"
            ), {"id": fee.id})).one()
            self.assertEqual(tuple(row), (" 原案号 ", True))
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM schema_migrations WHERE key = :revision"
            ), {"revision": DASHBOARD_FINANCE_REVISION})).scalar_one(), 1)
            self.assertTrue((await connection.execute(old_integrity_query)).scalar_one())

    async def test_finance_projection_partial_definition_is_not_registered(self) -> None:
        await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.begin() as connection:
            await connection.execute(text("DELETE FROM schema_migrations WHERE key = :revision"),
                                     {"revision": DASHBOARD_FINANCE_REVISION})
            await connection.execute(text("ALTER TABLE dashboard_finance_relations DROP COLUMN fee_type"))
        with self.assertRaisesRegex(RuntimeError, "列定义不一致"):
            await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            self.assertEqual((await connection.execute(text(
                "SELECT count(*) FROM schema_migrations WHERE key = :revision"
            ), {"revision": DASHBOARD_FINANCE_REVISION})).scalar_one(), 0)
            self.assertEqual((await connection.execute(text("SELECT count(*) FROM business_records"))).scalar_one(), 0)

    async def test_finance_projection_readiness_rejects_disabled_sync(self) -> None:
        from app.core.dashboard_finance_read_model_migration import SYNC_TRIGGER, validate_dashboard_finance_read_model
        from app.core.dashboard_revision import revision_query

        await migrate_startup_schema(self.engine, _upgrade_schema)
        async with self.engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(text(f"ALTER TABLE business_records DISABLE TRIGGER {SYNC_TRIGGER}"))
                with self.assertRaisesRegex(RuntimeError, "同步触发器不完整"):
                    await connection.run_sync(validate_dashboard_finance_read_model)
                self.assertFalse((await connection.execute(revision_query())).one().ready)
            finally:
                await transaction.rollback()
        await migrate_startup_schema(self.engine, _upgrade_schema)

    async def test_finance_projection_multiconnection_visibility_and_revision(self) -> None:
        await migrate_startup_schema(self.engine, _upgrade_schema)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with sessions() as session:
            fee = BusinessRecord(module="finance", serial_no="CODEX-PG-RELATION-COMMIT",
                                 title="代理费", owner="admin", data={"case_no": "旧案号"})
            session.add(fee)
            await session.commit()
        statement = text("SELECT source.data->>'case_no', projected.case_no "
                         "FROM business_records source JOIN dashboard_finance_relations projected "
                         "ON projected.record_id = source.id WHERE source.id = :id")
        revision = text("SELECT count(*) FROM dashboard_change_revisions")
        async with self.engine.connect() as writer, self.engine.connect() as reader:
            original_revision = (await reader.execute(revision)).scalar_one()
            transaction = await writer.begin()
            await writer.execute(text("UPDATE business_records SET data = '{\"case_no\":\"新案号\"}'::json WHERE id = :id"),
                                 {"id": fee.id})
            self.assertEqual(tuple((await reader.execute(statement, {"id": fee.id})).one()), ("旧案号", "旧案号"))
            self.assertEqual((await reader.execute(revision)).scalar_one(), original_revision)
            self.assertEqual(tuple((await writer.execute(statement, {"id": fee.id})).one()), ("新案号", "新案号"))
            await transaction.commit()
            self.assertEqual(tuple((await reader.execute(statement, {"id": fee.id})).one()), ("新案号", "新案号"))
            self.assertEqual((await reader.execute(revision)).scalar_one(), original_revision + 1)
            rollback_transaction = await writer.begin()
            await writer.execute(text("UPDATE business_records SET data = '{\"case_no\":\"回滚案号\"}'::json WHERE id = :id"),
                                 {"id": fee.id})
            await rollback_transaction.rollback()
            self.assertEqual(tuple((await reader.execute(statement, {"id": fee.id})).one()), ("新案号", "新案号"))
            self.assertEqual((await reader.execute(revision)).scalar_one(), original_revision + 1)


if __name__ == "__main__":
    unittest.main()

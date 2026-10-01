"""后台业务规则独立事务与任务候选筛选的持久化回归。"""

import os
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.system import _run_business_rules_once
from app.core.tasks import _apply_task_auto_completion, _apply_task_overdue_performance
from app.database import Base
from app.models import BusinessRecord, Notification, User, WorkflowEvent


POSTGRES_URL = os.environ.get("BUSINESS_RULE_TEST_POSTGRES_URL", "")
TABLES = [model.__table__ for model in (BusinessRecord, User, WorkflowEvent, Notification)]


class BusinessRuleAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("后台业务规则测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_rules_{uuid4().hex[:12]}"
            self.admin_engine = create_async_engine(self.database_url)
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(
                self.database_url,
                connect_args={"server_settings": {"search_path": self.schema}},
            )
        else:
            self.engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(
                sync_connection, tables=TABLES,
            ))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    async def test_failed_rule_rolls_back_and_later_rules_run_and_repeat(self):
        async with self.sessions() as db:
            db.add(User(
                username="enterprise-rule-owner", display_name="测试负责人",
                password_hash="test-only-hash", department="测试部", role="user",
            ))
            db.add_all([
                BusinessRecord(
                    module="task", serial_no="ENTERPRISE-RULE-AUTO-CONFIRM",
                    title="待自动验收", status="待确认", owner="enterprise-rule-owner",
                    data={"completion_auto_confirm_at": str(date.today() - timedelta(days=1))},
                ),
                BusinessRecord(
                    module="task", serial_no="ENTERPRISE-RULE-OVERDUE",
                    title="超期任务", status="待处理", owner="enterprise-rule-owner",
                    data={"deadline": str(date.today() - timedelta(days=2))},
                ),
            ])
            await db.commit()

        async def failing_notary(db):
            db.add(BusinessRecord(
                module="notary", serial_no="ENTERPRISE-RULE-ROLLED-BACK",
                title="失败事务标记", status="待审核", owner="system", data={},
            ))
            await db.flush()
            raise RuntimeError("注入公证规则失败")

        case_rule = AsyncMock(return_value=0)
        with patch("app.core.system.SessionLocal", self.sessions), \
             patch("app.core.investigation._apply_notary_auto_conversion", failing_notary), \
             patch("app.core.tasks._apply_case_automatic_task_rules", case_rule):
            with self.assertLogs("app.core.system", level="ERROR") as logs:
                await _run_business_rules_once()
        self.assertEqual(case_rule.await_count, 1)
        self.assertTrue(any("公证自动转案" in message for message in logs.output))

        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(BusinessRecord.id).where(
                BusinessRecord.serial_no == "ENTERPRISE-RULE-ROLLED-BACK",
            )))
            auto = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.serial_no == "ENTERPRISE-RULE-AUTO-CONFIRM",
            ))
            overdue = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.serial_no == "ENTERPRISE-RULE-OVERDUE",
            ))
            self.assertEqual(auto.status, "已验收")
            self.assertTrue(auto.data["auto_confirmed"])
            self.assertEqual(overdue.data["performance_impact"]["overdue_days"], 2)
            first_events = int(await db.scalar(select(func.count()).select_from(WorkflowEvent)) or 0)
            first_notifications = int(await db.scalar(select(func.count()).select_from(Notification)) or 0)
        self.assertEqual(first_events, 2)
        self.assertEqual(first_notifications, 1)

        with patch("app.core.system.SessionLocal", self.sessions), \
             patch("app.core.investigation._apply_notary_auto_conversion", AsyncMock(return_value=False)), \
             patch("app.core.tasks._apply_case_automatic_task_rules", case_rule):
            await _run_business_rules_once()
        self.assertEqual(case_rule.await_count, 2)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), first_events)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Notification)), first_notifications)

    async def test_terminal_statuses_are_not_loaded_and_basic_date_still_counts(self):
        async with self.sessions() as db:
            warehouse = BusinessRecord(
                module="warehouse", serial_no="ENTERPRISE-RULE-WAREHOUSE",
                title="待出库证据", status="在库", owner="enterprise-rule-owner", data={},
            )
            db.add(warehouse)
            await db.flush()
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-RULE-IGNORED-{index:03d}",
                    title="已结束任务", status="已拒绝" if index % 2 else "已验收",
                    owner="enterprise-rule-owner",
                    data={"deadline": str(date.today() - timedelta(days=2))},
                )
                for index in range(100)
            ])
            db.add(BusinessRecord(
                module="task", serial_no="ENTERPRISE-RULE-BASIC-DATE",
                title="历史紧凑日期任务", status="待处理",
                owner="enterprise-rule-owner",
                data={"deadline": (date.today() - timedelta(days=2)).strftime("%Y%m%d")},
            ))
            db.add(BusinessRecord(
                module="task", serial_no="ENTERPRISE-RULE-EVIDENCE",
                title="已验收出库任务", status="已验收", owner="enterprise-rule-owner",
                data={"auto_task_type": "take_evidence", "warehouse_evidence_id": warehouse.id},
            ))
            await db.commit()

        loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                loaded.append(item.serial_no) if isinstance(item, BusinessRecord) else None
            ))
            self.assertTrue(await _apply_task_overdue_performance(db))
        self.assertEqual(loaded, ["ENTERPRISE-RULE-BASIC-DATE"])

        loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                loaded.append(item.serial_no) if isinstance(item, BusinessRecord) else None
            ))
            self.assertFalse(await _apply_task_overdue_performance(db))
            self.assertEqual(loaded, ["ENTERPRISE-RULE-BASIC-DATE"])
            basic = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.serial_no == "ENTERPRISE-RULE-BASIC-DATE",
            ))
            self.assertEqual(basic.data["performance_impact"]["overdue_days"], 2)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 1)

        async with self.sessions() as db:
            loaded = []
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                loaded.append(item.serial_no) if isinstance(item, BusinessRecord) and item.module == "task" else None
            ))
            self.assertTrue(await _apply_task_auto_completion(db))
            self.assertEqual(len(loaded), 52)
            evidence = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.serial_no == "ENTERPRISE-RULE-WAREHOUSE",
            ))
            self.assertEqual(evidence.data["evidence_status"], "已出库")
            self.assertTrue(await db.scalar(select(BusinessRecord.id).where(
                BusinessRecord.serial_no == "ENTERPRISE-RULE-EVIDENCE",
            )))
        async with self.sessions() as db:
            self.assertFalse(await _apply_task_auto_completion(db))
        self.assertIn("ENTERPRISE-RULE-BASIC-DATE", loaded)
        self.assertFalse(any(number.startswith("ENTERPRISE-RULE-IGNORED-0") and
                             int(number[-3:]) % 2 for number in loaded))


class SQLiteBusinessRuleTest(BusinessRuleAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "设置 BUSINESS_RULE_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresBusinessRuleTest(BusinessRuleAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

"""通知发件箱在隔离 SQLite 和 PostgreSQL 中的持久化回归。"""

import asyncio
import inspect as pyinspect
import os
import secrets
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.params import Param
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.dingtalk import DingTalkError, DingTalkRejectedError
from app.models import (
    BusinessRecord, ContractApprovalStep, HearingSchedule, Notification, NotificationDelivery,
    NotificationSyncSchedule, RolePermission, User, WorkflowEvent,
)
from app.core import notification_delivery, notification_scheduler
from app.core.notification_schema_migration import upgrade_notification_delivery_schema
from app.core.tasks import _apply_hearing_sms_reminders
from tests.environment import validate_database_url, validate_test_environment


TABLES = [
    User.__table__, BusinessRecord.__table__, HearingSchedule.__table__,
    WorkflowEvent.__table__, ContractApprovalStep.__table__, Notification.__table__, NotificationDelivery.__table__,
    NotificationSyncSchedule.__table__, RolePermission.__table__,
]


class NotificationOutboxTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        validate_test_environment()
        self.temp = tempfile.TemporaryDirectory(prefix="oa-test-outbox-")
        postgres_url = os.environ.get("OUTBOX_TEST_POSTGRES_URL", "")
        if postgres_url:
            validate_database_url(postgres_url)
            if not postgres_url.rsplit("/", 1)[-1] == "oa_test_enterprise_outbox":
                raise RuntimeError("通知发件箱测试只能使用指定 PostgreSQL 测试库")
            self.schema = f"oa_outbox_{secrets.token_hex(5)}"
            self.admin_engine = create_async_engine(postgres_url)
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.engine = create_async_engine(
                postgres_url, connect_args={"server_settings": {"search_path": self.schema}},
            )
        else:
            self.schema = None
            path = Path(self.temp.name) / "outbox.sqlite"
            url = f"sqlite+aiosqlite:///{path.as_posix()}"
            validate_database_url(url)
            self.engine = create_async_engine(url, connect_args={"timeout": 30})
            self.admin_engine = None
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=TABLES))
        self.patches = [
            patch.object(notification_delivery, "SessionLocal", self.sessions),
            patch.object(notification_scheduler, "SessionLocal", self.sessions),
        ]
        for item in self.patches:
            item.start()
        self.old_settings = (
            settings.dingtalk_corp_id, settings.dingtalk_agent_id,
            settings.dingtalk_app_key, settings.dingtalk_app_secret,
            settings.dingtalk_notifications_enabled, settings.sms_webhook_url,
        )
        settings.dingtalk_corp_id = "test-corp"
        settings.dingtalk_agent_id = "1"
        settings.dingtalk_app_key = "test-key"
        settings.dingtalk_app_secret = "test-secret"
        settings.dingtalk_notifications_enabled = True
        settings.sms_webhook_url = "https://outbox-test.invalid/sms"

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        (
            settings.dingtalk_corp_id, settings.dingtalk_agent_id,
            settings.dingtalk_app_key, settings.dingtalk_app_secret,
            settings.dingtalk_notifications_enabled, settings.sms_webhook_url,
        ) = self.old_settings
        await self.engine.dispose()
        if self.admin_engine:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            await self.admin_engine.dispose()
        self.temp.cleanup()

    async def _add_user(self, username="staff", *, phone="13800000000", ding="ding-staff"):
        async with self.sessions() as db:
            db.add(User(
                username=username, display_name="测试员工", department="测试部门",
                role="user", role_ids=["user"], password_hash="test-only",
                profile={"phone": phone, "dingtalk_user_id": ding}, is_active=True,
            ))
            await db.commit()

    async def _add_notice(self, key="notice-1"):
        async with self.sessions() as db:
            db.add(Notification(
                source_key=key, source_type="task", recipient="staff",
                title="任务通知", content="待处理任务",
            ))
            await db.commit()

    async def _add_hearing(self, days=1):
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no=f"CASE-{days}-{secrets.token_hex(4)}", title="测试案件",
                customer="测试客户", status="审理中", owner="staff",
                department="测试部门", data={"handling_lawyers": ["测试员工"]},
            )
            db.add(case)
            await db.flush()
            db.add(HearingSchedule(
                case_record_id=case.id, hearing_date=date.today() + timedelta(days=days),
                hearing_time="09:00", court="测试法院", hearing_lawyer="测试员工", status="已排期",
            ))
            await db.commit()

    async def test_dingtalk_claim_is_atomic_and_sent_once(self):
        await self._add_user()
        await self._add_notice()
        async with self.sessions() as db:
            self.assertEqual(await notification_delivery.enqueue_dingtalk_notifications(db), 1)
        calls = []

        async def sender(delivery):
            calls.append((delivery.destination, delivery.payload["title"]))
            await asyncio.sleep(0.05)
            return "provider-task-1"

        await asyncio.gather(
            notification_delivery.dispatch_one("dingtalk", sender),
            notification_delivery.dispatch_one("dingtalk", sender),
        )
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery))
            notice = await db.scalar(select(Notification))
            self.assertEqual((delivery.state, delivery.attempts), ("sent", 1))
            self.assertEqual(delivery.provider_reference, "provider-task-1")
            self.assertEqual(notice.dingtalk_status, "sent")
        self.assertEqual(calls, [("ding-staff", "任务通知")])

    async def test_uncommitted_notice_and_delivery_never_send(self):
        await self._add_user()
        async with self.sessions() as db:
            db.add(Notification(source_key="rolled-back-notice", source_type="task", recipient="staff", title="未提交", content="未提交"))
            await db.flush()
            await db.rollback()
        async with self.sessions() as db:
            self.assertEqual(await notification_delivery.enqueue_dingtalk_notifications(db), 0)
            await notification_delivery.insert_delivery(db, {
                "channel": "dingtalk", "business_key": "rolled-back-delivery",
                "destination": "ding-staff", "payload": {"title": "未提交", "content": "未提交"},
                "state": "pending", "available_at": datetime.now(timezone.utc),
            })
            await db.rollback()
        self.assertIsNone(await notification_delivery.claim_delivery("dingtalk"))

    async def test_explicit_dingtalk_rejection_is_terminal(self):
        await self._add_user()
        await self._add_notice()
        async with self.sessions() as db:
            await notification_delivery.enqueue_dingtalk_notifications(db)
        calls = 0

        async def rejected(_delivery):
            nonlocal calls
            calls += 1
            raise DingTalkRejectedError("测试通道明确拒绝")

        self.assertTrue(await notification_delivery.dispatch_one("dingtalk", rejected))
        self.assertFalse(await notification_delivery.dispatch_one("dingtalk", rejected))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery))
            notice = await db.scalar(select(Notification))
            self.assertEqual(delivery.state, "rejected")
            self.assertEqual(notice.dingtalk_status, "failed")
        self.assertEqual(calls, 1)

    async def test_preexisting_dingtalk_attempt_limit_is_preserved(self):
        await self._add_user()
        await self._add_notice()
        async with self.sessions() as db:
            notice = await db.scalar(select(Notification))
            notice.dingtalk_attempts = 4
            notice.dingtalk_status = "failed"
            await db.commit()
            await notification_delivery.enqueue_dingtalk_notifications(db)

        async def preflight_failure(_delivery):
            raise DingTalkError("测试发送前准备失败")

        self.assertTrue(await notification_delivery.dispatch_one("dingtalk", preflight_failure))
        self.assertFalse(await notification_delivery.dispatch_one("dingtalk", preflight_failure))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery))
            notice = await db.scalar(select(Notification))
            self.assertEqual((delivery.state, delivery.attempts), ("rejected", 5))
            self.assertEqual((notice.dingtalk_status, notice.dingtalk_attempts), ("failed", 5))

    async def test_unknown_result_and_expired_claim_are_never_retried(self):
        await self._add_user()
        await self._add_notice()
        async with self.sessions() as db:
            await notification_delivery.enqueue_dingtalk_notifications(db)
        calls = 0

        async def uncertain(_delivery):
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("响应超时")

        self.assertTrue(await notification_delivery.dispatch_one("dingtalk", uncertain))
        self.assertFalse(await notification_delivery.dispatch_one("dingtalk", uncertain))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery))
            notice = await db.scalar(select(Notification))
            self.assertEqual(delivery.state, "unknown")
            self.assertEqual(notice.dingtalk_status, "unknown")
        self.assertEqual(calls, 1)

        await self._add_notice("notice-2")
        async with self.sessions() as db:
            await notification_delivery.enqueue_dingtalk_notifications(db)
        claim = await notification_delivery.claim_delivery("dingtalk")
        self.assertIsNotNone(claim)
        async with self.sessions() as db:
            delivery = await db.get(NotificationDelivery, claim[0])
            delivery.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            await db.commit()
        self.assertEqual(await notification_delivery.mark_expired_claims_unknown(), 1)
        self.assertFalse(await notification_delivery.dispatch_one("dingtalk", uncertain))
        self.assertEqual(calls, 1)

    async def test_sms_record_is_committed_before_concurrent_delivery(self):
        await self._add_user()
        await self._add_hearing()
        async with self.sessions() as db:
            self.assertTrue(await _apply_hearing_sms_reminders(db))
            self.assertFalse(await _apply_hearing_sms_reminders(db))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms"))
            record = await db.get(BusinessRecord, delivery.source_record_id)
            self.assertEqual((delivery.state, record.status), ("pending", "待发送"))
        calls = []

        async def sender(delivery):
            calls.append(delivery.payload["hearing_id"])
            await asyncio.sleep(0.05)
            return "provider-accepted"

        await asyncio.gather(
            notification_delivery.dispatch_one("sms", sender),
            notification_delivery.dispatch_one("sms", sender),
        )
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms"))
            record = await db.get(BusinessRecord, delivery.source_record_id)
            self.assertEqual((delivery.state, record.status), ("sent", "已发送"))
            self.assertEqual(record.data["provider_response"], "provider-accepted")
            self.assertEqual(await db.scalar(select(func.count()).select_from(NotificationDelivery)), 1)
        self.assertEqual(len(calls), 1)

    async def test_sms_unknown_after_timeout_is_visible_and_not_resent(self):
        await self._add_user()
        await self._add_hearing(days=3)
        async with self.sessions() as db:
            await _apply_hearing_sms_reminders(db)
        calls = 0

        async def uncertain(_delivery):
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("短信响应超时")

        self.assertTrue(await notification_delivery.dispatch_one("sms", uncertain))
        self.assertFalse(await notification_delivery.dispatch_one("sms", uncertain))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms"))
            record = await db.get(BusinessRecord, delivery.source_record_id)
            self.assertEqual((delivery.state, record.status), ("unknown", "结果待核实"))
        self.assertEqual(calls, 1)

    async def test_rescheduled_pending_sms_is_cancelled_and_new_schedule_sent_once(self):
        await self._add_user()
        await self._add_hearing(days=1)
        async with self.sessions() as db:
            await _apply_hearing_sms_reminders(db)
            hearing = await db.scalar(select(HearingSchedule))
            hearing.hearing_date = date.today() + timedelta(days=3)
            await db.commit()
            self.assertTrue(await _apply_hearing_sms_reminders(db))
            self.assertFalse(await _apply_hearing_sms_reminders(db))
        calls = []

        async def sender(delivery):
            calls.append(delivery.payload["content"])
            return "rescheduled-accepted"

        self.assertTrue(await notification_delivery.dispatch_one("sms", sender))
        self.assertEqual(calls, [])
        self.assertTrue(await notification_delivery.dispatch_one("sms", sender))
        self.assertFalse(await notification_delivery.dispatch_one("sms", sender))
        async with self.sessions() as db:
            deliveries = (await db.scalars(select(NotificationDelivery).order_by(NotificationDelivery.id))).all()
            self.assertEqual([row.state for row in deliveries], ["cancelled", "sent"])
            self.assertNotEqual(deliveries[0].business_key, deliveries[1].business_key)
            self.assertIn(str(date.today() + timedelta(days=3)), calls[0])
            notices = (await db.scalars(select(Notification).order_by(Notification.id))).all()
            self.assertEqual([row.title for row in notices], ["开庭短信：发送取消", "开庭短信：已发送"])
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "sms")), 2)

    async def test_same_date_time_change_invalidates_old_snapshot(self):
        await self._add_user()
        await self._add_hearing()
        async with self.sessions() as db:
            await _apply_hearing_sms_reminders(db)
            hearing = await db.scalar(select(HearingSchedule))
            hearing.hearing_time = "15:30"
            hearing.court = "变更后的法院"
            await db.commit()
            await _apply_hearing_sms_reminders(db)
        calls = []

        async def sender(delivery):
            calls.append(delivery.payload["content"])
            return "changed-time-accepted"

        await notification_delivery.dispatch_one("sms", sender)
        self.assertEqual(calls, [])
        await notification_delivery.dispatch_one("sms", sender)
        self.assertEqual(len(calls), 1)
        self.assertIn("15:30 在 变更后的法院", calls[0])

    async def test_sent_or_unknown_prior_schedule_does_not_block_new_schedule(self):
        for previous_state in ("sent", "unknown"):
            with self.subTest(previous_state=previous_state):
                await self._add_user(username=f"staff-{previous_state}")
                await self._add_hearing(days=1)
                async with self.sessions() as db:
                    await _apply_hearing_sms_reminders(db)
                    hearing = await db.scalar(select(HearingSchedule).order_by(HearingSchedule.id.desc()))
                    prior = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.payload["hearing_id"].as_integer() == hearing.id))
                    prior.state = previous_state
                    hearing.hearing_time = "16:00"
                    await db.commit()
                    await _apply_hearing_sms_reminders(db)
                    self.assertFalse(await _apply_hearing_sms_reminders(db))
                    deliveries = (await db.scalars(select(NotificationDelivery).where(NotificationDelivery.payload["hearing_id"].as_integer() == hearing.id).order_by(NotificationDelivery.id))).all()
                    self.assertEqual([row.state for row in deliveries], [previous_state, "pending"])
                    # 清空本轮待发送项，下一子场景的日程保持独立。
                    deliveries[-1].state = "sent"
                    await db.commit()

    async def test_legacy_unknown_schedule_is_not_automatically_resent(self):
        await self._add_user()
        await self._add_hearing()
        async with self.sessions() as db:
            hearing = await db.scalar(select(HearingSchedule))
            db.add(BusinessRecord(
                module="sms", serial_no="LEGACY-SMS", title="旧开庭提醒", customer="测试客户",
                status="已发送", owner="system", department="测试部门", description="无法确定日期的历史提醒",
                data={"hearing_id": hearing.id, "remind_days": 1},
            ))
            await db.commit()
            self.assertTrue(await _apply_hearing_sms_reminders(db))
            self.assertFalse(await _apply_hearing_sms_reminders(db))
            delivery = await db.scalar(select(NotificationDelivery))
            self.assertEqual(delivery.state, "unknown")
            self.assertIn("禁止自动重发", delivery.error)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "sms")), 1)

        async def sender(_delivery):
            raise AssertionError("不能自动重发无法确认日程的旧提醒")

        self.assertFalse(await notification_delivery.dispatch_one("sms", sender))

    async def test_sms_uncommitted_delivery_does_not_send(self):
        await self._add_user()
        await self._add_hearing()
        async with self.sessions() as db:
            await notification_delivery.insert_delivery(db, {
                "channel": "sms", "business_key": "hearing:1:1",
                "destination": "13800000000", "payload": {"hearing_id": 1},
                "state": "pending", "available_at": datetime.now(timezone.utc),
            })
            await db.rollback()
        self.assertIsNone(await notification_delivery.claim_delivery("sms"))

    async def test_sms_cancelled_hearing_is_never_sent(self):
        await self._add_user()
        await self._add_hearing()
        async with self.sessions() as db:
            await _apply_hearing_sms_reminders(db)
            hearing = await db.scalar(select(HearingSchedule))
            hearing.status = "已取消"
            await db.commit()
        calls = 0

        async def sender(_delivery):
            nonlocal calls
            calls += 1
            return "不应发送"

        self.assertTrue(await notification_delivery.dispatch_one("sms", sender))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms"))
            record = await db.get(BusinessRecord, delivery.source_record_id)
            self.assertEqual((delivery.state, record.status), ("cancelled", "发送取消"))
        self.assertEqual(calls, 0)

    async def test_sms_explicit_rejection_and_expired_claim(self):
        await self._add_user()
        await self._add_hearing()
        async with self.sessions() as db:
            await _apply_hearing_sms_reminders(db)

        async def rejected(_delivery):
            request = httpx.Request("POST", settings.sms_webhook_url)
            response = httpx.Response(400, request=request)
            raise httpx.HTTPStatusError("测试通道明确拒绝", request=request, response=response)

        self.assertTrue(await notification_delivery.dispatch_one("sms", rejected))
        async with self.sessions() as db:
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms"))
            record = await db.get(BusinessRecord, delivery.source_record_id)
            self.assertEqual((delivery.state, record.status), ("rejected", "发送失败"))

        await self._add_hearing(days=3)
        async with self.sessions() as db:
            await _apply_hearing_sms_reminders(db)
        claim = await notification_delivery.claim_delivery("sms")
        self.assertIsNotNone(claim)
        async with self.sessions() as db:
            delivery = await db.get(NotificationDelivery, claim[0])
            delivery.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            await db.commit()
        self.assertEqual(await notification_delivery.mark_expired_claims_unknown(), 1)
        async with self.sessions() as db:
            delivery = await db.get(NotificationDelivery, claim[0])
            record = await db.get(BusinessRecord, delivery.source_record_id)
            self.assertEqual((delivery.state, record.status), ("unknown", "结果待核实"))
        self.assertFalse(await notification_delivery.dispatch_one("sms", rejected))

    async def test_sync_schedule_claim_is_atomic(self):
        await self._add_user()
        self.assertEqual(await notification_scheduler.seed_notification_schedules(), 1)
        self.assertEqual(await notification_scheduler.seed_notification_schedules(), 0)
        claims = await asyncio.gather(
            notification_scheduler.claim_notification_sync(),
            notification_scheduler.claim_notification_sync(),
        )
        self.assertEqual(sum(item is not None for item in claims), 1)
        username, token = next(item for item in claims if item is not None)
        await notification_scheduler._finish_sync(username, token)
        self.assertIsNone(await notification_scheduler.claim_notification_sync())

    async def test_background_sync_uses_actual_recipient_identity(self):
        await self._add_user()
        await notification_scheduler.seed_notification_schedules()
        from app.core import permissions, tasks

        seen = []

        async def permission_payload(_user, _db):
            return {"menu_keys": ["task-mine"], "action_keys": [], "data_scope": "self"}

        async def sync(identity, _db):
            seen.append(identity)

        with patch.object(permissions, "_user_permission_payload", permission_payload), patch.object(tasks, "_sync_notifications", sync):
            self.assertTrue(await notification_scheduler.sync_one_recipient())
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["username"], "staff")
        self.assertEqual(seen[0]["role_ids"], ["user"])
        self.assertFalse(seen[0]["_page_menu_capability"])

    async def test_notification_and_task_get_handlers_do_not_commit(self):
        await self._add_user()
        await self._add_notice()
        async with self.sessions() as db:
            db.add(BusinessRecord(
                module="task", serial_no="TASK-1", title="待办任务",
                customer="测试客户", status="待接收", owner="staff",
                department="测试部门", data={
                    "initiator": "staff",
                    "handoff_auto_complete_at": str(date.today() - timedelta(days=1)),
                },
            ))
            await db.commit()

        from app.areas.system.router import list_notifications
        from app.areas.tp.router import list_tasks

        def arguments(handler, identity, db):
            result = {}
            for name, parameter in pyinspect.signature(handler).parameters.items():
                if name == "identity":
                    result[name] = identity
                elif name == "db":
                    result[name] = db
                else:
                    default = parameter.default
                    result[name] = default.default if isinstance(default, Param) else default
            return result

        identity = {"username": "staff", "role": "user", "role_ids": ["user"]}

        def forbid_commit(_session):
            raise AssertionError("GET 不应提交业务事务")

        async with self.sessions() as db:
            event.listen(db.sync_session, "before_commit", forbid_commit)
            try:
                notices = await list_notifications(**arguments(list_notifications, identity, db))
                tasks = await list_tasks(**arguments(list_tasks, identity, db))
            finally:
                event.remove(db.sync_session, "before_commit", forbid_commit)
            self.assertEqual(notices["total"], 1)
            self.assertEqual(tasks["total"], 1)
            task = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "task"))
            self.assertEqual(task.status, "待接收")

    async def test_notification_sync_loads_only_owned_tasks_and_notice_sources(self):
        await self._add_user()
        async with self.sessions() as db:
            owned = BusinessRecord(
                module="task", serial_no="SYNC-OWNED", title="本人任务", owner="staff", status="待接收",
                data={"deadline": str(date.today() + timedelta(days=1))},
            )
            history = BusinessRecord(
                module="task", serial_no="SYNC-HISTORY", title="协作历史", owner="other", status="已完成",
                data={"collaborators": ["staff"]},
            )
            db.add_all([owned, history])
            db.add_all(BusinessRecord(
                module="task" if index % 2 else "case", serial_no=f"SYNC-UNRELATED-{index}",
                title="无关业务", owner="other", status="待接收", data={"large_payload": "x" * 4096},
            ) for index in range(200))
            await db.flush()
            allowed_ids = {owned.id, history.id}
            db.add(Notification(
                source_key="task-message-history-staff", source_type="task", source_id=history.id,
                recipient="staff", title="任务历史消息", content="保留原协作关系",
            ))
            await db.commit()
        from app.core import tasks
        from app.core import ipr

        loaded_ids = []

        def loaded(record, _context):
            loaded_ids.append(record.id)

        async def no_ipr(_identity, _db):
            return None

        event.listen(BusinessRecord, "load", loaded)
        try:
            with patch.object(ipr, "_materialize_ipr_case_warnings", no_ipr):
                async with self.sessions() as db:
                    await tasks._sync_notifications({"username": "staff", "role": "admin"}, db)
        finally:
            event.remove(BusinessRecord, "load", loaded)
        self.assertEqual(set(loaded_ids), allowed_ids)
        async with self.sessions() as db:
            notices = (await db.scalars(select(Notification).where(Notification.recipient == "staff"))).all()
            self.assertTrue(any(row.source_key == "task-message-history-staff" for row in notices))
            self.assertTrue(any(row.source_key.startswith("task-") and row.source_id in allowed_ids for row in notices))

    async def test_postgres_migration_rolls_back_after_failure(self):
        if not self.schema:
            self.skipTest("PostgreSQL DDL transaction check")
        async with self.engine.begin() as connection:
            await connection.run_sync(NotificationDelivery.__table__.drop)
            await connection.run_sync(NotificationSyncSchedule.__table__.drop)
        with self.assertRaisesRegex(RuntimeError, "测试回滚"):
            async with self.engine.begin() as connection:
                await connection.run_sync(upgrade_notification_delivery_schema)
                raise RuntimeError("测试回滚")
        async with self.engine.begin() as connection:
            names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
            self.assertNotIn("notification_deliveries", names)
            self.assertNotIn("notification_sync_schedules", names)
            await connection.run_sync(upgrade_notification_delivery_schema)

    async def test_migration_reentry_preserves_delivery_state(self):
        await self._add_user()
        await self._add_notice()
        async with self.sessions() as db:
            await notification_delivery.enqueue_dingtalk_notifications(db)
        async with self.engine.begin() as connection:
            await connection.run_sync(upgrade_notification_delivery_schema)
            await connection.run_sync(upgrade_notification_delivery_schema)
            tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
        self.assertIn("notification_deliveries", tables)
        self.assertIn("notification_sync_schedules", tables)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(NotificationDelivery)), 1)


if __name__ == "__main__":
    unittest.main()

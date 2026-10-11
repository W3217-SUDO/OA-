import unittest
import asyncio
import json
from contextlib import ExitStack
from collections import OrderedDict
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard, list_pending_execution_cases
from app.models import BusinessRecord, ContractObject, HearingSchedule, User


IDENTITY = {"username": "admin", "role": "admin"}


class DashboardMetricsBindingContractTest(unittest.IsolatedAsyncioTestCase):
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
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="Dashboard Admin", department="上海", password_hash="test", role="admin", is_active=True))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_dashboard_metrics_follow_real_business_fields_and_routes(self):
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="HT-DASH-OFFICIAL", title="官费应收合同",
                customer="客户", status="审批通过", owner="admin", department="上海", data={},
            )
            db.add(contract)
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="AJ-DASH-OFFICIAL", title="官费应收案件",
                customer="客户", status="一审", owner="admin", department="上海",
                data={"contract_id": contract.id, "contract_no": contract.serial_no},
            )
            db.add(case)
            await db.flush()
            db.add(ContractObject(
                contract_record_id=contract.id, case_record_id=case.id,
                fee_type="官费", amount=100, created_by="admin", updated_by="admin",
            ))
            db.add_all([
                BusinessRecord(
                    module="finance", serial_no="FY-DASH-OFFICIAL", title="官费",
                    customer="客户", status="草稿", owner="admin", department="上海",
                    data={
                        "fee_type": "官方费用", "amount": 100, "paid_amount": 70,
                        "received_amount": 20, "contract_id": contract.id,
                        "case_id": case.id, "case_no": case.serial_no,
                    },
                ),
                BusinessRecord(
                    module="finance", serial_no="FY-DASH-REFUND", title="退费",
                    customer="客户", status="待审批", owner="admin", department="上海",
                    data={
                        "fee_type": "代理费", "refund_requested_amount": 50,
                        "refunded_amount": 10, "case_id": case.id, "case_no": case.serial_no,
                    },
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-URGENT", title="紧急案件",
                    customer="客户", status="新案待分配", owner="admin", department="上海",
                    data={"phase_changed_at": str(date.today() - timedelta(days=366))},
                ),
                BusinessRecord(
                    module="task", serial_no="TASK-DASH-URGENT", title="紧急案件任务",
                    customer="客户", status="待处理", owner="admin", department="上海",
                    data={
                        "source": "案件任务", "case_no": "AJ-DASH-URGENT",
                        "deadline": str(date.today() + timedelta(days=10)),
                    },
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-EXECUTION", title="待执行案件",
                    customer="客户", status="一审待执行", owner="admin", department="上海",
                    data={"case_phase": "一审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-APPEAL", title="待上诉案件",
                    customer="客户", status="待上诉", owner="admin", department="上海", data={},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-SUPPLEMENT", title="补充材料案件",
                    customer="客户", status="一审补充证据", owner="admin", department="上海",
                    data={"case_type": "民事争议"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-OPINION", title="补充代理意见案件",
                    customer="客户", status="一审补充代理意见", owner="admin", department="上海",
                    data={"case_type": "民事争议"},
                ),
                BusinessRecord(
                    module="case", serial_no="AJ-DASH-FALSE-SUPPLEMENT", title="仅文字提到补证",
                    customer="客户", status="文书准备", owner="admin", department="上海",
                    data={"case_type": "民事争议", "required_action": "补充证据"},
                ),
            ])
            await db.commit()
            result = await dashboard(IDENTITY, db, section=None)

        metrics = {item["key"]: item for item in result["metrics"]}
        self.assertEqual(metrics["official-fee-unpaid"]["value"], "1件")
        self.assertEqual(metrics["official-fee-unreceived"]["value"], "80.00元")
        self.assertEqual(metrics["refund-pending"]["value"], "1件")
        self.assertEqual(metrics["evidence-supplement"]["value"], "1件")
        self.assertEqual(metrics["opinion-supplement"]["value"], "1件")
        self.assertEqual(metrics["appeal-pending"]["value"], "1件")
        self.assertEqual(metrics["execution-pending"]["value"], "1件")
        self.assertEqual(metrics["urgent-cases"]["value"], "1件")
        self.assertEqual(metrics["evidence-supplement"]["route"], "dashboard-queue-evidence-supplement")
        self.assertEqual(metrics["opinion-supplement"]["route"], "dashboard-queue-opinion-supplement")
        self.assertEqual(metrics["execution-pending"]["route"], "dashboard-queue-execution-pending")
        self.assertEqual(result["source"], "realtime")

    async def test_pending_execution_list_uses_dashboard_phases_and_role_scope(self):
        async with self.sessions() as db:
            db.add(User(
                username="limited", display_name="受限用户", department="测试部",
                password_hash="unused", role="user", is_active=True,
            ))
            db.add_all([
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-FIRST", title="一审待执行",
                    customer="客户", status="一审待执行", owner="limited", department="测试部",
                    data={"case_phase": "一审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-SECOND", title="二审待执行",
                    customer="客户", status="二审待执行", owner="other", department="其他部",
                    data={"case_phase": "二审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-RETRIAL", title="再审待执行",
                    customer="客户", status="再审待执行", owner="other", department="其他部",
                    data={"case_phase": "再审待执行"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-ACTIVE", title="已经执行",
                    customer="客户", status="执行受理", owner="limited", department="测试部",
                    data={"case_phase": "执行受理", "execution_status": "执行受理"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-R6-STALE-SIGNAL", title="历史执行字段残留",
                    customer="客户", status="一审准备开庭", owner="limited", department="测试部",
                    data={"case_phase": "一审准备开庭", "execution_status": "一审待执行"},
                ),
            ])
            await db.commit()

            admin_dashboard = await dashboard(IDENTITY, db, section=None)
            admin_list = await list_pending_execution_cases(1, 20, IDENTITY, db)
            admin_page_one = await list_pending_execution_cases(1, 2, IDENTITY, db)
            admin_page_two = await list_pending_execution_cases(2, 2, IDENTITY, db)
            limited_list = await list_pending_execution_cases(
                1, 20, {"username": "limited", "role": "user"}, db,
            )

        admin_metric = next(item for item in admin_dashboard["metrics"] if item["key"] == "execution-pending")
        self.assertEqual(admin_metric["value"], "3件")
        self.assertEqual(admin_list["total"], 3)
        self.assertEqual(
            {item["serial_no"] for item in admin_list["items"]},
            {"CODEX-827-R6-FIRST", "CODEX-827-R6-SECOND", "CODEX-827-R6-RETRIAL"},
        )
        self.assertEqual(admin_page_one["total"], 3)
        self.assertEqual(admin_page_two["total"], 3)
        self.assertEqual(
            {item["serial_no"] for item in admin_page_one["items"] + admin_page_two["items"]},
            {"CODEX-827-R6-FIRST", "CODEX-827-R6-SECOND", "CODEX-827-R6-RETRIAL"},
        )
        self.assertEqual(limited_list["total"], 1)
        self.assertEqual(limited_list["items"][0]["serial_no"], "CODEX-827-R6-FIRST")

    async def test_dashboard_hearings_follow_case_court_fields_with_legacy_priority(self):
        first_hearing = datetime.combine(date.today() + timedelta(days=5), time(9, 30))
        retrial_hearing = datetime.combine(date.today() + timedelta(days=7), time(14, 15))
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-826-R2-CASE", title="开庭排期关联案件",
                customer="CODEX-826-R2-客户", status="再审", owner="admin", department="上海",
                data={
                    "first_court_name": "一审法院",
                    "first_court_hearing_date": str(first_hearing),
                    "retrial_court_name": "CODEX-826-R2-再审法院",
                    "retrial_court_courtroom": "第二法庭",
                    "retrial_court_hearing_date": str(retrial_hearing),
                    "hearing_lawyer": "开庭律师",
                    "handling_lawyers": ["经办律师"],
                    "assistant": "律师助理",
                },
            )
            db.add(case)
            await db.flush()
            db.add(HearingSchedule(
                case_record_id=case.id, hearing_date=first_hearing.date(), hearing_time="09:30",
                court="旧的独立排期", courtroom="第一法庭", hearing_type="一审开庭",
                hearing_lawyer="开庭律师", status="已排期",
            ))
            await db.commit()
            result = await dashboard(IDENTITY, db, section=None)

        matching = [item for item in result["hearings"] if item["case_no"] == "CODEX-826-R2-CASE"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["date"], str(retrial_hearing.date()))
        self.assertEqual(matching[0]["time"], "14:15")
        self.assertEqual(matching[0]["court"], "CODEX-826-R2-再审法院")
        self.assertEqual(matching[0]["lawyer"], "开庭律师")
        self.assertEqual(matching[0]["agent"], "经办律师")
        self.assertEqual(matching[0]["assistant"], "律师助理")


class DashboardSharedMetricsCacheTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.core import dashboard_metrics_cache as cache
        from app.core import dashboard_metrics_redis as shared

        self.cache, self.shared = cache, shared
        self.original_read = shared.read
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.revision = self.patches.enter_context(patch.object(shared, "source_revision", return_value="source-a"))
        self.patches.enter_context(patch.object(cache.settings, "cache_redis_url", "redis://cache:6380/0"))
        self.patches.enter_context(patch.object(cache.settings, "dashboard_metrics_cache_wait_seconds", 0.03))
        self.patches.enter_context(patch.object(cache.settings, "dashboard_metrics_compute_timeout_seconds", 0.02))
        self.snapshot = self.patches.enter_context(patch.object(cache, "_visible_snapshot", AsyncMock(return_value="10:20:")))
        self.result = {"metrics": [
            {"key": str(i), "label": "统计", "tone": "green", "value": "0件", "route": "dashboard-queue-" + str(i)}
            for i in range(8)
        ]}
        self.compute = self.patches.enter_context(patch.object(cache, "dashboard_metrics", AsyncMock(return_value=self.result)))
        self.read = self.patches.enter_context(patch.object(shared, "read", AsyncMock(return_value=None)))
        self.acquire = self.patches.enter_context(patch.object(shared, "acquire", AsyncMock(return_value="owner")))
        self.publish = self.patches.enter_context(patch.object(shared, "publish", AsyncMock()))
        self.release = self.patches.enter_context(patch.object(shared, "release", AsyncMock()))
        self.db = SimpleNamespace(
            new=[], dirty=[], deleted=[], rollback=AsyncMock(), in_transaction=Mock(return_value=True),
            get_bind=Mock(return_value=Mock(
                dialect=SimpleNamespace(name="postgresql"),
                url=make_url("postgresql+asyncpg://account:secret@db/oa"),
            )),
        )

    async def test_cached_hit_releases_read_connection_and_checks_new_snapshot(self):
        self.read.return_value = {"snapshot": "10:20:", "result": self.result}
        self.assertEqual(await self.cache.read_dashboard_metrics(IDENTITY, self.db), self.result)
        self.db.rollback.assert_awaited_once()
        self.assertEqual(self.snapshot.await_count, 3)
        self.compute.assert_not_awaited()

    async def test_disabled_cache_and_non_postgres_keep_original_path(self):
        self.db.get_bind.return_value.dialect.name = "sqlite"
        await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.read.assert_not_awaited()
        self.db.get_bind.return_value.dialect.name = "postgresql"
        with patch.object(self.cache.settings, "cache_redis_url", ""), patch.object(self.cache, "_entries", OrderedDict()):
            await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.read.assert_not_awaited()

    async def test_owner_refreshes_snapshot_and_publishes_complete_result(self):
        self.snapshot.side_effect = ["10:20:", "10:20:", "20:30:", "20:30:"]
        self.assertEqual(await self.cache.read_dashboard_metrics(IDENTITY, self.db), self.result)
        self.publish.assert_awaited_once()
        self.assertEqual(self.publish.await_args.args[2:], ("20:30:", self.result))
        self.release.assert_awaited_once()

    async def test_changed_snapshot_during_compute_does_not_publish(self):
        self.snapshot.side_effect = ["10:20:", "10:20:", "10:20:", "20:30:"]
        self.assertEqual(await self.cache.read_dashboard_metrics(IDENTITY, self.db), self.result)
        self.publish.assert_not_awaited()

    async def test_pending_writes_and_fixed_snapshot_bypass_without_rollback(self):
        for pending in ("new", "dirty", "deleted"):
            setattr(self.db, pending, [object()])
            await self.cache.read_dashboard_metrics(IDENTITY, self.db)
            setattr(self.db, pending, [])
        self.snapshot.return_value = None
        await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.db.rollback.assert_not_awaited()
        self.read.assert_not_awaited()

    async def test_second_snapshot_ineligible_does_not_rollback(self):
        self.snapshot.side_effect = ["10:20:", None]
        await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.db.rollback.assert_not_awaited()
        self.read.assert_not_awaited()

    async def test_pending_change_after_second_check_does_not_rollback(self):
        async def snapshot(db):
            if self.snapshot.await_count == 2:
                db.dirty.append(object())
            return "10:20:"
        self.snapshot.side_effect = snapshot
        await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.db.rollback.assert_not_awaited()

    async def test_lock_wait_has_no_checked_out_database_connection(self):
        self.acquire.return_value = None
        held = True
        async def rollback():
            nonlocal held
            held = False
        async def acquire(key):
            self.assertFalse(held)
            return None
        self.db.rollback.side_effect = rollback
        self.db.in_transaction.side_effect = lambda: held
        self.acquire.side_effect = acquire
        with self.assertRaises(HTTPException) as caught:
            await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.assertEqual(caught.exception.status_code, 503)
        self.release.assert_not_awaited()
        self.compute.assert_not_awaited()

    async def test_continuously_changing_cached_snapshot_is_bounded(self):
        self.read.return_value = {"snapshot": "10:20:", "result": self.result}
        self.acquire.return_value = None
        async def snapshot(db):
            return f"{self.snapshot.await_count}:{1000 + self.snapshot.await_count}:"
        self.snapshot.side_effect = snapshot
        with self.assertRaises(HTTPException):
            await asyncio.wait_for(self.cache.read_dashboard_metrics(IDENTITY, self.db), 0.3)
        self.compute.assert_not_awaited()

    async def test_waiter_accepts_new_published_snapshot_without_reacquiring_lock(self):
        self.read.side_effect = [None, {"snapshot": "20:30:", "result": self.result}]
        self.acquire.return_value = None
        self.db.in_transaction.side_effect = [True, False]
        self.snapshot.side_effect = ["10:20:", "10:20:", "20:30:"]
        with patch.object(self.cache.settings, "dashboard_metrics_cache_wait_seconds", 0.3), \
                patch.object(self.cache.asyncio, "sleep", AsyncMock()):
            self.assertEqual(await self.cache.read_dashboard_metrics(IDENTITY, self.db), self.result)
        self.acquire.assert_awaited_once()
        self.db.rollback.assert_awaited_once()
        self.compute.assert_not_awaited()

    async def test_redis_failure_is_explicit_and_does_not_compute(self):
        self.read.side_effect = RedisConnectionError("unavailable")
        with self.assertRaises(HTTPException) as caught:
            await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.assertEqual(caught.exception.status_code, 503)
        self.compute.assert_not_awaited()

    async def test_compute_timeout_releases_lock_and_preserves_error(self):
        async def slow(*args):
            await asyncio.sleep(1)
        self.compute.side_effect = slow
        self.release.side_effect = RedisConnectionError("cleanup failed")
        with self.assertRaises(HTTPException) as caught:
            await self.cache.read_dashboard_metrics(IDENTITY, self.db)
        self.assertIn("计算超时", caught.exception.detail)
        self.release.assert_awaited_once()
        self.publish.assert_not_awaited()

    async def test_owner_cancel_waits_for_cleanup_and_preserves_cancellation(self):
        started = asyncio.Event()
        async def slow(*args):
            started.set()
            await asyncio.sleep(1)
        self.compute.side_effect = slow
        self.release.side_effect = RedisConnectionError("cleanup failed")
        task = asyncio.create_task(self.cache.read_dashboard_metrics(IDENTITY, self.db))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.release.assert_awaited_once()

    async def test_namespace_isolates_full_identity_database_and_date(self):
        key = self.cache._shared_key(IDENTITY, self.db, date.today())
        self.assertNotIn("secret", key)
        self.assertNotIn("account", key)
        self.revision.return_value = "source-b"
        self.assertNotEqual(key, self.cache._shared_key(IDENTITY, self.db, date.today()))
        self.revision.return_value = "source-a"
        self.assertNotEqual(key, self.cache._shared_key({**IDENTITY, "action_keys": ["*"]}, self.db, date.today()))
        self.assertNotEqual(key, self.cache._shared_key(IDENTITY, self.db, date.today() + timedelta(days=1)))
        self.db.get_bind.return_value.url = make_url("postgresql+asyncpg://account:secret@db/other")
        self.assertNotEqual(key, self.cache._shared_key(IDENTITY, self.db, date.today()))

    async def test_cache_corruption_is_explicit(self):
        client = SimpleNamespace(get=AsyncMock())
        with patch.object(self.shared, "client", return_value=client):
            for payload in (b"{", b"\xff", b"{}", json.dumps({"snapshot": "invalid", "result": self.result}),
                            json.dumps({"snapshot": "10:20:", "result": {"metrics": []}})):
                client.get.return_value = payload
                with self.assertRaises(HTTPException) as caught:
                    await self.original_read("key")
                self.assertEqual(caught.exception.status_code, 503)

    async def test_pool_url_cannot_override_limits_and_shutdown_closes_owner(self):
        from redis.asyncio import BlockingConnectionPool
        url = "redis://cache:6380/0?max_connections=999&socket_timeout=99&socket_connect_timeout=99&decode_responses=True&timeout=99"
        pool = BlockingConnectionPool.from_url(url)
        client = SimpleNamespace(ping=AsyncMock(), aclose=AsyncMock())
        with patch.object(self.shared, "_client", None), patch.object(self.shared.settings, "cache_redis_url", url), \
                patch.object(self.shared.BlockingConnectionPool, "from_url", return_value=pool), \
                patch.object(self.shared.Redis, "from_pool", return_value=client):
            await self.shared.start_dashboard_metrics_cache()
            self.assertEqual(pool.max_connections, 16)
            self.assertEqual(pool.timeout, 1)
            self.assertEqual(pool.connection_kwargs["socket_timeout"], 1)
            self.assertEqual(pool.connection_kwargs["socket_connect_timeout"], 1)
            self.assertFalse(pool.connection_kwargs["decode_responses"])
            self.assertEqual(pool.connection_kwargs["retry"]._retries, 0)
            await self.shared.close_dashboard_metrics_cache()
            client.aclose.assert_awaited_once()
            self.assertIsNone(self.shared._client)

    async def test_source_revision_is_portable_stable_and_content_sensitive(self):
        with TemporaryDirectory() as left, TemporaryDirectory() as right:
            for root in (Path(left), Path(right)):
                (root / "core").mkdir()
                (root / "core" / "metrics.py").write_bytes(b"value = 1\n")
                (root / "settings.py").write_bytes(b"enabled = True\n")
            digest = self.shared._source_digest(Path(left))
            self.assertEqual(digest, self.shared._source_digest(Path(right)))
            (Path(right) / "core" / "metrics.py").write_bytes(b"value = 2\n")
            self.assertNotEqual(digest, self.shared._source_digest(Path(right)))
            (Path(right) / "core" / "metrics.py").write_bytes(b"value = 1\n")
            (Path(right) / "settings.py").rename(Path(right) / "other.py")
            self.assertNotEqual(digest, self.shared._source_digest(Path(right)))


if __name__ == "__main__":
    unittest.main()

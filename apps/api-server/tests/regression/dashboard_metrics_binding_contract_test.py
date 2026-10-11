import unittest
import asyncio
import json
from contextlib import ExitStack
from collections import OrderedDict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.requests import Request
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError as RedisResponseError
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


class QuerySharedCacheTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.core import query_cache as cache
        from app.core import query_cache_store as store
        from app.core import dashboard_metrics_redis as shared

        self.cache, self.store, self.shared = cache, store, shared
        self.original_read, self.original_publish = store.read, store.publish
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.object(cache.settings, "cache_redis_url", "redis://cache:6380/0"))
        self.patches.enter_context(patch.object(cache.settings, "dashboard_metrics_cache_wait_seconds", 0.03))
        self.patches.enter_context(patch.object(cache.settings, "dashboard_metrics_compute_timeout_seconds", 0.02))
        self.revision = self.patches.enter_context(patch.object(shared, "source_revision", return_value="source-a"))
        self.snapshot = self.patches.enter_context(patch.object(cache, "visible_snapshot", AsyncMock(return_value="10:20:")))
        self.read = self.patches.enter_context(patch.object(store, "read", AsyncMock(return_value=None)))
        self.acquire = self.patches.enter_context(patch.object(store, "acquire", AsyncMock(return_value="owner")))
        self.publish = self.patches.enter_context(patch.object(store, "publish", AsyncMock()))
        self.release = self.patches.enter_context(patch.object(store, "release", AsyncMock()))
        self.db = SimpleNamespace(
            new=[], dirty=[], deleted=[], rollback=AsyncMock(), in_transaction=Mock(return_value=True),
            get_bind=Mock(return_value=Mock(dialect=SimpleNamespace(name="postgresql"),
                                          url=make_url("postgresql+asyncpg://account:secret@db/oa"))),
        )
        self.result = {"items": [{"date": date(2026, 10, 11), "amount": Decimal("100.20"),
                                  "created_at": datetime(2026, 10, 11, 9, 30), "empty": None}], "total": 1}
        self.compute = AsyncMock(return_value=self.result)
        self.namespace = "finance.incoming.list"
        self.parameters = {"keyword": "客户", "page": 1}

    async def query(self):
        return await self.cache.cached_query(self.db, IDENTITY, self.namespace, self.parameters, self.compute)

    async def test_cold_preserves_original_result_and_hot_preserves_json_wire_values(self):
        cold = await self.query()
        self.assertIs(cold, self.result)
        encoded = self.store._encode("10:20:", cold)
        self.read.return_value = self.store._decode(encoded)
        self.compute.reset_mock()
        hot = await self.query()
        self.assertEqual(jsonable_encoder(cold), hot)
        self.assertEqual(JSONResponse(jsonable_encoder(cold)).body, JSONResponse(hot).body)
        self.compute.assert_not_awaited()

    async def test_key_isolates_full_permission_identity_parameters_source_database_and_date(self):
        today = date.today()
        def key(identity=IDENTITY, parameters=None, namespace=None, day=today):
            return self.cache._query_key(self.db, identity, namespace or self.namespace,
                                         parameters or self.parameters, day)
        base = key()
        self.assertNotIn("secret", base)
        self.assertNotIn("客户", base)
        for field, value in (("role", "user"), ("field_keys", ["amount"]),
                             ("action_keys", ["finance.read"]), ("_actual_role", "partner"),
                             ("_page_menu_capability", {"role": "admin"}), ("_request_path", "/other")):
            self.assertNotEqual(base, key(identity={**IDENTITY, field: value}))
        for parameters in ({"keyword": "other", "page": 1}, {"keyword": "客户", "page": 2},
                           {**self.parameters, "date": date.today()}, {**self.parameters, "id": 2}):
            self.assertNotEqual(base, key(parameters=parameters))
        self.assertNotEqual(base, key(namespace="finance.incoming.detail"))
        self.assertNotEqual(base, key(day=today + timedelta(days=1)))
        self.revision.return_value = "source-b"
        self.assertNotEqual(base, key())
        self.revision.return_value = "source-a"
        self.db.get_bind.return_value.url = make_url("postgresql+asyncpg://account:secret@db/other")
        self.assertNotEqual(base, key())

    async def test_parameters_use_fastapi_encoder_for_validated_dates_and_decimals(self):
        typed = {"date": date(2026, 10, 11), "amount": Decimal("10.20"), "filters": (1, 2)}
        self.assertEqual(self.cache._digest(typed), self.cache._digest(jsonable_encoder(typed)))
        self.assertEqual(self.cache._digest({"a": 1, "b": None}), self.cache._digest({"b": None, "a": 1}))
        self.assertNotEqual(self.cache._digest({"b": None}), self.cache._digest({}))

    async def test_ineligible_sessions_and_disabled_cache_do_not_rollback(self):
        with patch.object(self.cache.settings, "cache_redis_url", ""):
            self.assertIs(await self.query(), self.result)
        self.snapshot.assert_not_awaited()
        self.db.get_bind.return_value.dialect.name = "sqlite"
        await self.query()
        self.db.get_bind.return_value.dialect.name = "postgresql"
        for field in ("new", "dirty", "deleted"):
            setattr(self.db, field, [object()])
            await self.query()
            setattr(self.db, field, [])
        self.snapshot.return_value = None
        await self.query()
        self.db.rollback.assert_not_awaited()
        self.read.assert_not_awaited()

    async def test_changed_snapshot_or_pending_write_does_not_publish(self):
        self.snapshot.side_effect = ["10:20:", "10:20:", "10:20:", "20:30:"]
        self.assertIs(await self.query(), self.result)
        self.publish.assert_not_awaited()
        self.snapshot.side_effect = None
        async def compute():
            self.db.dirty.append(object())
            return self.result
        self.compute.side_effect = compute
        self.assertIs(await self.query(), self.result)
        self.publish.assert_not_awaited()

    async def test_lock_wait_does_not_hold_database_connection(self):
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
            await self.query()
        self.assertEqual(caught.exception.status_code, 503)
        self.compute.assert_not_awaited()

    async def test_enabled_redis_network_or_oom_failure_never_recomputes(self):
        for error in (RedisConnectionError("offline"), RedisResponseError("OOM command not allowed")):
            self.read.side_effect = error
            with self.assertRaises(HTTPException) as caught:
                await self.query()
            self.assertEqual(caught.exception.status_code, 503)
        self.compute.assert_not_awaited()

    async def test_payload_limit_and_response_objects_are_explicit_admission_bypasses(self):
        client = SimpleNamespace(eval=AsyncMock(return_value=1))
        with patch.object(self.shared, "client", return_value=client), \
                patch.object(self.store.settings, "query_cache_max_payload_bytes", 1024):
            self.assertIsNone(self.store._encode("10:20:", {"items": ["客户" * 1000]}))
            await self.original_publish("key", "owner", "10:20:", {"items": ["客户" * 1000]})
            for response in (JSONResponse({"ok": True}, status_code=202),
                             FileResponse("unused.docx"), StreamingResponse(iter([b"data"]))):
                await self.original_publish("key", "owner", "10:20:", response)
        client.eval.assert_not_awaited()

    async def test_store_validates_schema_size_and_nonfinite_numbers_without_fake_results(self):
        client = SimpleNamespace(get=AsyncMock())
        with patch.object(self.shared, "client", return_value=client), \
                patch.object(self.store.settings, "query_cache_max_payload_bytes", 1024):
            for payload in (b"{", b"\xff", b"{}", b"x" * 1025,
                            b'{"snapshot":"bad","result":null}',
                            b'{"snapshot":"10:20:","result":NaN}',
                            b'{"snapshot":"10:20:","result":1e999}',
                            b'{"snapshot":"10:20:","result":{},"extra":1}'):
                client.get.return_value = payload
                with self.assertRaises(HTTPException) as caught:
                    await self.original_read("key")
                self.assertEqual(caught.exception.status_code, 503)
            for result in (None, [], [{"a": None}, {"b": 1}], True, "文字", 100.2):
                client.get.return_value = self.store._encode("10:20:", result)
                self.assertEqual((await self.original_read("key"))["result"], result)

    async def test_publish_uses_bounded_ttl_and_checks_owner_token(self):
        client = SimpleNamespace(eval=AsyncMock(return_value=1))
        with patch.object(self.shared, "client", return_value=client):
            await self.original_publish("key", "owner", "10:20:", self.result)
            args = client.eval.await_args.args
            self.assertEqual(args[:5], (self.shared._PUBLISH, 2, "key:lock", "key:data", "owner"))
            self.assertEqual(args[6], 60)
            self.assertEqual(self.store._decode(args[5])["result"], jsonable_encoder(self.result))
            client.eval.return_value = 0
            with self.assertRaises(HTTPException) as caught:
                await self.original_publish("key", "expired", "10:20:", self.result)
            self.assertEqual(caught.exception.status_code, 503)


    async def test_request_and_orm_dependencies_are_not_encoded(self):
        for value in (Request({"type": "http"}), User(username="unused")):
            with self.assertRaises(TypeError):
                self.cache._digest({"dependency": value})
            with self.assertRaises(TypeError):
                self.store._encode("10:20:", {"item": value})

    async def test_actual_snapshot_reader_rejects_own_xid_and_fixed_isolation(self):
        from app.core.query_cache_flow import visible_snapshot
        row = SimpleNamespace(snapshot="10:20:", own_xid=None, isolation="read committed")
        db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(one=lambda: row)))
        self.assertEqual(await visible_snapshot(db), "10:20:")
        row.own_xid = "15"
        self.assertIsNone(await visible_snapshot(db))
        row.own_xid = None
        for isolation in ("repeatable read", "serializable"):
            row.isolation = isolation
            self.assertIsNone(await visible_snapshot(db))

    async def test_small_cold_concurrency_has_one_owner_and_independent_sessions(self):
        entries, locks, databases = {}, {}, []
        async def read(key):
            return entries.get(key)
        async def acquire(key):
            if key in locks:
                return None
            locks[key] = "owner"
            return "owner"
        async def publish(key, token, snapshot, result):
            self.assertEqual(locks[key], token)
            entries[key] = self.store._decode(self.store._encode(snapshot, result))
        async def release(key, token):
            self.assertEqual(locks.pop(key), token)
        async def compute():
            await asyncio.sleep(0.01)
            return self.result
        self.read.side_effect, self.acquire.side_effect = read, acquire
        self.publish.side_effect, self.release.side_effect = publish, release
        self.compute.side_effect = compute
        for _ in range(4):
            databases.append(SimpleNamespace(
                new=[], dirty=[], deleted=[], rollback=AsyncMock(), in_transaction=Mock(return_value=True),
                get_bind=self.db.get_bind,
            ))
        self.assertEqual(self.cache.settings.dashboard_metrics_compute_timeout_seconds, 0.02)
        with patch.object(self.cache.settings, "dashboard_metrics_cache_wait_seconds", 0.5), \
                patch.object(self.cache.settings, "dashboard_metrics_compute_timeout_seconds", 0.3):
            results = await asyncio.gather(*(self.cache.cached_query(
                db, IDENTITY, self.namespace, self.parameters, self.compute,
            ) for db in databases))
        self.assertEqual(self.cache.settings.dashboard_metrics_compute_timeout_seconds, 0.02)
        self.compute.assert_awaited_once()
        self.publish.assert_awaited_once()
        self.release.assert_awaited_once()
        self.assertFalse(locks)
        for result in results:
            self.assertEqual(jsonable_encoder(result), jsonable_encoder(self.result))
        for db in databases:
            db.rollback.assert_awaited()

    async def test_generic_cancel_and_compute_timeout_release_owned_lock(self):
        started = asyncio.Event()
        async def slow():
            started.set()
            await asyncio.sleep(1)
        self.compute.side_effect = slow
        task = asyncio.create_task(self.query())
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.release.assert_awaited_once()
        self.publish.assert_not_awaited()
        self.release.reset_mock()
        with self.assertRaises(HTTPException) as caught:
            await self.query()
        self.assertIn("计算超时", caught.exception.detail)
        self.release.assert_awaited_once()
        self.publish.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

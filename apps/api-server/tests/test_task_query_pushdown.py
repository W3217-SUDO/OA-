"""任务列表查询与旧实现的结果、分页及数据库载入量对照。"""

import os
import unittest
from datetime import date, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from uuid import uuid4

from sqlalchemy import event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.tp.router import list_tasks, list_vip_tasks
from app.core.investigation import _is_investigation_task
from app.core.task_query import task_canonical_deadline, task_not_investigation_condition
from app.database import Base
from app.models import BusinessRecord, User, VipTask, VipTaskMessage, VipTaskNode


POSTGRES_URL = os.environ.get("TASK_QUERY_TEST_POSTGRES_URL", "")
BASELINE_PATH = os.environ.get("E07_BASELINE_TP_ROUTER", "")


class TaskQueryPushdownAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("任务查询测试只能使用独立 PostgreSQL 测试库")
            self.schema = f"oa_test_task_query_{uuid4().hex[:12]}"
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
                sync_connection,
                tables=[BusinessRecord.__table__, User.__table__, VipTask.__table__, VipTaskNode.__table__, VipTaskMessage.__table__],
            ))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    async def test_vip_list_pages_only_matching_entities(self):
        async with self.sessions() as db:
            db.add_all([
                VipTask(
                    serial_no=f"ENTERPRISE-VIP-QUERY-{index:03d}", title=f"任务 {index}",
                    customer="普通客户", status="待处理" if index % 2 else "处理中",
                    priority="普通" if index % 3 else "紧急", owner="other",
                    department="测试部", description="普通描述", created_by="other",
                    collaborators=["viewer"] if index % 4 == 0 else [],
                ) for index in range(120)
            ])
            db.add_all([
                VipTask(
                    serial_no="ENTERPRISE-VIP-QUERY-UNICODE", title="Straße K",
                    customer="Straße 客户", status="待处理", priority="紧急",
                    owner="viewer", department="测试部", description="特殊搜索",
                    created_by="other", collaborators=[],
                ),
                VipTask(
                    serial_no="ENTERPRISE-VIP-QUERY-CREATOR", title="创建人任务",
                    customer="普通客户", status="待处理", priority="普通",
                    owner="other", department="测试部", description="创建人可见",
                    created_by="viewer", collaborators=[],
                ),
            ])
            await db.commit()

        baseline = None
        if BASELINE_PATH:
            spec = spec_from_file_location("e07_task_query_baseline", BASELINE_PATH)
            baseline = module_from_spec(spec)
            spec.loader.exec_module(baseline)
        identities = (
            {"username": "viewer", "role": "user"},
            {"username": "admin", "role": "admin"},
        )
        filters = (
            {}, {"page": 2, "page_size": 7}, {"page": 999},
            {"status_filter": "待处理", "priority": "紧急"},
            {"keyword": "strasse"}, {"keyword": "k"}, {"customer": "STRASSE"},
        )
        for identity in identities:
            for extra in filters:
                params = {
                    "keyword": "", "customer": "", "status_filter": "", "priority": "",
                    "page": 1, "page_size": 15, "identity": identity,
                    **extra,
                }
                loaded = []
                async with self.sessions() as db:
                    event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                        loaded.append(item.id) if isinstance(item, VipTask) else None
                    ))
                    actual = await list_vip_tasks(db=db, **params)
                self.assertLessEqual(len(loaded), params["page_size"])
                self.assertEqual(len(loaded), len(actual["items"]))
                if baseline:
                    async with self.sessions() as db:
                        expected = await baseline.list_vip_tasks(db=db, **params)
                    self.assertEqual(actual, expected, (identity, extra))

    async def test_vip_legacy_collaborator_json_preserves_membership(self):
        historical_values = (None, "viewer", {"viewer": True}, [1, True], ["viewer"])
        async with self.sessions() as db:
            db.add_all([
                VipTask(
                    serial_no=f"ENTERPRISE-VIP-LEGACY-{index:03d}", title=f"历史任务 {index}",
                    customer="历史客户", status="待处理", priority="普通",
                    owner="other", department="测试部", description="异形协作人",
                    created_by="other", collaborators=value,
                ) for index, value in enumerate(historical_values)
            ])
            await db.commit()
        baseline = None
        if BASELINE_PATH:
            spec = spec_from_file_location("e07_vip_legacy_baseline", BASELINE_PATH)
            baseline = module_from_spec(spec)
            spec.loader.exec_module(baseline)
        for username in ("viewer", "v", "1", "True", "other", "admin"):
            identity = {"username": username, "role": "admin" if username == "admin" else "user"}
            for extra in ({}, {"page": 2, "page_size": 2}, {"keyword": "历史任务"}):
                params = {
                    "keyword": "", "customer": "", "status_filter": "", "priority": "",
                    "page": 1, "page_size": 15, "identity": identity, **extra,
                }
                loaded = []
                async with self.sessions() as db:
                    event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                        loaded.append(item.id) if isinstance(item, VipTask) else None
                    ))
                    actual = await list_vip_tasks(db=db, **params)
                self.assertEqual(len(loaded), len(actual["items"]))
                self.assertLessEqual(len(loaded), params["page_size"])
                if baseline:
                    async with self.sessions() as db:
                        expected = await baseline.list_vip_tasks(db=db, **params)
                    self.assertEqual(actual, expected, (username, extra))

    async def test_investigation_sql_condition_matches_historical_json_values(self):
        samples = [
            {}, {"investigation_record_id": 0}, {"investigation_record_id": False},
            {"investigation_record_id": ""}, {"investigation_record_id": []},
            {"investigation_record_id": {}}, {"investigation_record_id": 1},
            {"investigation_record_id": "0"}, {"investigation_record_id": [0]},
            {"investigation_record_id": {"id": 1}},
            {"investigation_no": "\u3000"}, {"investigation_no": "I-1"},
            {"investigation_no": []}, {"investigation_no": [1]},
            {"investigation_module": " investigation \u3000"},
            {"source": "\u3000调查任务\u3000"},
            {"source": "调查子任务"},
            {"task_business_type": "  ", "business_type": "调查任务"},
            {"task_business_type": "", "business_type": "调查任务"},
            {"task_business_type": False, "business_type": "调查子任务"},
            {"business_type": "调查任务"},
            {"business_type": "普通任务"},
        ]
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-TASK-JSON-{index:03d}",
                    title="JSON 边界", customer="", status="待处理", owner="viewer",
                    department="测试部", data=data,
                ) for index, data in enumerate(samples)
            ])
            await db.commit()
        async with self.sessions() as db:
            tasks = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()
            expected = {task.id for task in tasks if not _is_investigation_task(task)}
            condition = task_not_investigation_condition(db.get_bind().dialect.name)
            actual = set((await db.scalars(select(BusinessRecord.id).where(
                BusinessRecord.module == "task", condition,
            ))).all())
        self.assertEqual(actual, expected)

    async def test_sql_date_sort_guard_preserves_legacy_parser_boundary(self):
        samples = [
            {}, {"deadline": None}, {"deadline": ""},
            {"deadline": "2026-02-28"}, {"deadline": "2024-02-29"},
            {"deadline": "2026-02-29"}, {"deadline": "2026-13-01"},
            {"deadline": "0000-01-01"}, {"deadline": "20261001"},
            {"deadline": "2026-W40-4"}, {"deadline": "2026-10-01T10:00:00"},
            {"deadline": 0, "task_end_time": "2026-10-01"},
            {"deadline": " ", "task_end_time": "2026-10-01"},
            {"task_end_time": "2026-10-02"}, {"TaskEndTime": "2026-10-03"},
        ]
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-TASK-DATE-{index:03d}",
                    title="日期边界", customer="", status="待处理", owner="viewer",
                    department="测试部", data=data,
                ) for index, data in enumerate(samples)
            ])
            await db.commit()
        async with self.sessions() as db:
            raw, canonical = task_canonical_deadline(db.get_bind().dialect.name)
            rows = (await db.execute(select(
                BusinessRecord.serial_no, raw, canonical,
            ).where(BusinessRecord.module == "task").order_by(BusinessRecord.serial_no))).all()
        for index, row in enumerate(rows):
            data = samples[index]
            expected_raw = data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime") or ""
            expected_canonical = False
            try:
                expected_canonical = str(date.fromisoformat(str(expected_raw))) == str(expected_raw)
            except ValueError:
                pass
            self.assertEqual(str(row[1]), str(expected_raw), index)
            self.assertEqual(bool(row[2]), expected_canonical, index)

    async def test_task_sql_page_matches_current_response_and_loads_one_page(self):
        async with self.sessions() as db:
            db.add(User(username="viewer", display_name="查看人", password_hash="x", role="user", department="测试部"))
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-TASK-PAGE-{index:03d}",
                    title=f"任务 {index}", customer="普通客户", status="待处理",
                    owner="viewer", department="测试部", description="查询分页",
                    data={
                        "initiator": "other", "collaborators": [],
                        "deadline": str(date.today() + timedelta(days=index % 30)),
                        "large_payload": "x" * 4096,
                    },
                ) for index in range(120)
            ])
            await db.commit()
        baseline = None
        if BASELINE_PATH:
            spec = spec_from_file_location("e07_task_list_baseline", BASELINE_PATH)
            baseline = module_from_spec(spec)
            spec.loader.exec_module(baseline)
        for sort_by in ("deadline", "created_at", "updated_at"):
            for page in (1, 2, 999):
                params = dict(
                    scope="mine", relation="owned", page_id=None,
                    sort_by=sort_by, sort_order="desc", page=page, page_size=15,
                    identity={"username": "viewer", "role": "user"},
                )
                loaded = []
                statements = []
                def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
                    statements.append(statement.lower())
                event.listen(self.engine.sync_engine, "before_cursor_execute", capture_sql)
                try:
                    async with self.sessions() as db:
                        event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                            loaded.append(item.id)
                            if isinstance(item, BusinessRecord) and item.module == "task" else None
                        ))
                        actual = await list_tasks(db=db, **params)
                finally:
                    event.remove(self.engine.sync_engine, "before_cursor_execute", capture_sql)
                self.assertEqual(actual["total"], 120)
                self.assertEqual(actual["summary"]["total"], 120)
                self.assertEqual(len(loaded), len(actual["items"]))
                self.assertLessEqual(len(loaded), 15)
                self.assertTrue(any("limit" in sql and "business_records" in sql for sql in statements))
                self.assertTrue(any("count(*)" in sql and "business_records" in sql for sql in statements))
                if baseline:
                    async with self.sessions() as db:
                        expected = await baseline.list_tasks(db=db, **params)
                    self.assertEqual(actual, expected, (sort_by, page))

    async def test_task_unicode_and_linked_case_filters_match_current_response(self):
        async with self.sessions() as db:
            db.add(User(username="viewer", display_name="用户姓名", password_hash="x", role="user", department="测试部"))
            db.add(BusinessRecord(
                module="hr", serial_no="ENTERPRISE-TASK-HR", title="展示姓名",
                customer="", status="在职", owner="viewer", department="测试部",
                data={"username": "viewer"},
            ))
            linked_case = BusinessRecord(
                module="case", serial_no="ENTERPRISE-TASK-CASE-UTF",
                title="关联案件", customer="客户甲", status="审理中",
                owner="viewer", department="测试部",
                data={"plaintiff": "ＡＢＣ", "defendant": "被告乙"},
            )
            db.add(linked_case)
            await db.flush()
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-TASK-SEARCH-{index:03d}",
                    title="Straße 测试" if index == 0 else f"普通任务 {index}",
                    customer="客户甲", status="待处理", owner="viewer",
                    department="测试部", description="搜索描述",
                    data={
                        "initiator": "viewer", "collaborators": [],
                        "source": "案件任务", "priority": "紧急" if index == 0 else "普通",
                        "case_record_id": linked_case.id if index == 0 else None,
                        "deadline": "20261001" if index == 0 else str(date.today() + timedelta(days=index)),
                        "large_payload": "z" * 4096,
                    },
                ) for index in range(30)
            ])
            await db.commit()
        baseline = None
        if BASELINE_PATH:
            spec = spec_from_file_location("e07_task_filter_baseline", BASELINE_PATH)
            baseline = module_from_spec(spec)
            spec.loader.exec_module(baseline)
        for extra in (
            {"case_no": "TASK-CASE-UTF"}, {"plaintiff": "ａｂｃ"},
            {"defendant": "被告乙"}, {"owner": "展示姓名"},
            {"initiator": "用户姓名"}, {"keyword": "strasse"},
            {"keyword": "straße"}, {"priority": "紧急"},
            {"source": "案件任务"}, {"statuses": "处理中,进行中"},
            {"status_filter": "待处理"}, {"reminder_only": True},
            {"deadline_from": date.today()}, {"sort_by": "days_remaining"},
        ):
            params = {
                **dict(
                scope="mine", relation="owned", page_id=None,
                sort_by="deadline", sort_order="desc", page=1, page_size=5,
                identity={"username": "viewer", "role": "user"},
                ),
                **extra,
            }
            loaded = []
            async with self.sessions() as db:
                event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                    loaded.append(item.id)
                    if isinstance(item, BusinessRecord) and item.module == "task" else None
                ))
                actual = await list_tasks(db=db, **params)
            self.assertEqual(len(loaded), len(actual["items"]))
            self.assertLessEqual(len(loaded), 5)
            if baseline:
                async with self.sessions() as db:
                    expected = await baseline.list_tasks(db=db, **params)
                self.assertEqual(actual, expected, extra)

    async def test_task_scope_matrix_and_investigation_exclusion_match_current_response(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="viewer", display_name="查看人", password_hash="x", role="user", department="A"),
                User(username="teammate", display_name="同事", password_hash="x", role="user", department="A"),
                User(username="outsider", display_name="外部", password_hash="x", role="user", department="B"),
            ])
            rows = [
                ("viewer", "outsider", ["teammate"], {}),
                ("outsider", "viewer", [], {}),
                ("outsider", "teammate", ["viewer"], {}),
                ("teammate", "outsider", [], {}),
                ("outsider", "outsider", [], {}),
                ("viewer", "viewer", [], {"source": "调查任务"}),
                ("viewer", "viewer", [], {"investigation_module": "investigation"}),
            ]
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-TASK-SCOPE-{index:03d}",
                    title=f"范围任务 {index}", customer="客户", status="待处理",
                    owner=owner, department="A" if owner != "outsider" else "B",
                    data={
                        "initiator": initiator, "collaborators": collaborators,
                        "deadline": str(date.today() + timedelta(days=index)), **extra,
                    },
                ) for index, (owner, initiator, collaborators, extra) in enumerate(rows)
            ])
            await db.commit()
        baseline = None
        if BASELINE_PATH:
            spec = spec_from_file_location("e07_task_scope_baseline", BASELINE_PATH)
            baseline = module_from_spec(spec)
            spec.loader.exec_module(baseline)
        identity = {"username": "viewer", "role": "user", "_page_menu_capability": True}
        cases = (
            ("default", "", None), ("mine", "owned", None),
            ("mine", "initiated", None), ("mine", "collaborating", None),
            ("department", "", None), ("department", "owned", None),
            ("department", "collaborating", None),
            ("company", "", None), ("company", "initiated", None),
            ("company", "collaborating", None),
            ("default", "", "9001001030"),
        )
        for scope, relation, page_id in cases:
            params = dict(
                scope=scope, relation=relation, page_id=page_id,
                sort_by="created_at", sort_order="asc", page=1, page_size=3,
                identity=identity,
            )
            loaded = []
            async with self.sessions() as db:
                event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                    loaded.append(item.id)
                    if isinstance(item, BusinessRecord) and item.module == "task" else None
                ))
                actual = await list_tasks(db=db, **params)
            self.assertEqual(len(loaded), len(actual["items"]))
            self.assertLessEqual(len(loaded), 3)
            if baseline:
                async with self.sessions() as db:
                    expected = await baseline.list_tasks(db=db, **params)
                self.assertEqual(actual, expected, (scope, relation, page_id))


class SQLiteTaskQueryPushdownTest(TaskQueryPushdownAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "设置 TASK_QUERY_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresTaskQueryPushdownTest(TaskQueryPushdownAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

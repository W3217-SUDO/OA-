"""公司任务候选轻投影保留筛选、动态汇总及完整页结果。"""

import os
import unittest
from datetime import date, datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.tp.router import list_tasks
from app.database import Base
from app.models import BusinessRecord, User


POSTGRES_URL = os.environ.get("TASK_PROJECTION_TEST_POSTGRES_URL", "")
BASELINE_PATH = os.environ.get("E07_BASELINE_TP_ROUTER", "")


class TaskProjectionAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("公司任务投影测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_taskview_{uuid4().hex[:12]}"
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
                sync_connection, tables=[BusinessRecord.__table__, User.__table__],
            ))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.identity = {
            "username": "task-projection-admin", "role": "admin",
            "_actual_role_ids": ["admin"], "_page_menu_capability": True,
        }

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    async def test_company_page_full_response_and_candidate_load(self):
        async with self.sessions() as db:
            db.add_all([
                User(
                    username="task-projection-admin", display_name="任务管理员",
                    password_hash="test-only-hash", department="测试部", role="admin",
                ),
                User(
                    username="task-projection-owner", display_name="任务负责人",
                    password_hash="test-only-hash", department="测试部", role="user",
                ),
            ])
            case = BusinessRecord(
                module="case", serial_no="ENTERPRISE-TASK-CASE", title="关联案件",
                customer="客户甲", status="审理中", owner="task-projection-owner",
                data={"plaintiff": "原告甲", "defendant": "被告乙", "case_stage": "审理"},
            )
            db.add(case)
            await db.flush()
            db.add(BusinessRecord(
                module="hr", serial_no="ENTERPRISE-TASK-HR", title="人事姓名",
                customer="", status="在职", owner="task-projection-owner",
                data={"username": "task-projection-owner", "large_payload": "h" * 4096},
            ))
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-TASK-PROJECTION-{index:03d}",
                    title=f"任务 {index}", customer="客户甲", status="待处理" if index % 2 else "处理中",
                    owner="task-projection-owner", department="测试部",
                    description="任务描述", created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
                    data={
                        "initiator": "task-projection-admin", "collaborators": ["task-projection-owner"],
                        "source": "案件任务", "priority": "重要" if index % 3 else "普通",
                        "deadline": str(date.today() + timedelta(days=index % 8 - 4)),
                        "case_id": case.id, "case_no": case.serial_no,
                        "large_payload": "t" * 4096,
                    },
                )
                for index in range(120)
            ])
            db.add(BusinessRecord(
                module="task", serial_no="ENTERPRISE-TASK-EXPLICIT-NULL",
                title="空值筛选任务", customer="客户甲", status="待处理",
                owner="task-projection-owner", department="测试部",
                data={"source": None, "priority": None, "initiator": "task-projection-admin"},
            ))
            await db.commit()

        params = dict(
            scope="company", relation="initiated", page_id=None,
            sort_by="deadline", sort_order="desc", page=2, page_size=15,
        )
        loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                loaded.append(item.serial_no)
                if isinstance(item, BusinessRecord) and item.module == "task" else None
            ))
            actual = await list_tasks(identity=dict(self.identity), db=db, **params)
        self.assertEqual(actual["total"], 121)
        self.assertEqual(actual["summary"]["total"], 121)
        self.assertEqual(len(actual["items"]), 15)
        self.assertEqual(len(loaded), 15)
        self.assertTrue(all(item["data"].get("large_payload") == "t" * 4096 for item in actual["items"]))
        empty_loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                empty_loaded.append(item.id)
                if isinstance(item, BusinessRecord) and item.module == "task" else None
            ))
            empty_page = await list_tasks(
                identity=dict(self.identity), db=db, **{**params, "page": 999},
            )
        self.assertEqual(empty_page["items"], [])
        self.assertEqual(empty_page["total"], 121)
        self.assertEqual(empty_page["summary"], actual["summary"])
        self.assertEqual(empty_loaded, [])

        if BASELINE_PATH:
            spec = spec_from_file_location("e07_baseline_tp_router", BASELINE_PATH)
            baseline_router = module_from_spec(spec)
            spec.loader.exec_module(baseline_router)
            baseline_loaded = []
            async with self.sessions() as db:
                event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                    baseline_loaded.append(item.serial_no)
                    if isinstance(item, BusinessRecord) and item.module == "task" else None
                ))
                expected = await baseline_router.list_tasks(identity=dict(self.identity), db=db, **params)
            self.assertEqual(actual, expected)
            self.assertEqual(len(baseline_loaded), 121)
            async with self.sessions() as db:
                baseline_empty = await baseline_router.list_tasks(
                    identity=dict(self.identity), db=db, **{**params, "page": 999},
                )
            self.assertEqual(empty_page, baseline_empty)

            for extra in (
                {"source": "None"}, {"priority": "None"},
                {"relation": "collaborating", "sort_by": "created_at"},
                {"relation": "owned", "sort_by": "days_remaining"},
                {"scope": "mine", "relation": "initiated", "sort_by": "updated_at"},
                {"status_filter": "已逾期"},
            ):
                filtered_params = {**params, **extra, "page": 1}
                async with self.sessions() as db:
                    filtered = await list_tasks(identity=dict(self.identity), db=db, **filtered_params)
                async with self.sessions() as db:
                    baseline_filtered = await baseline_router.list_tasks(
                        identity=dict(self.identity), db=db, **filtered_params,
                    )
                self.assertEqual(filtered, baseline_filtered)


class SQLiteTaskProjectionTest(TaskProjectionAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "设置 TASK_PROJECTION_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresTaskProjectionTest(TaskProjectionAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

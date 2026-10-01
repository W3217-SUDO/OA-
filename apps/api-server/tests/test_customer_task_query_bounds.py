"""空客户页和任务关系筛选的载入量、总数及顺序验证。"""

import os
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_customers
from app.areas.tp.router import list_tasks
from app.database import Base
from app.models import BusinessRecord, RolePermission, SystemParameter, User


POSTGRES_URL = os.environ.get("CUSTOMER_TASK_TEST_POSTGRES_URL", "")


class CustomerTaskQueryAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("客户任务查询测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_query_{uuid4().hex[:12]}"
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
                tables=[User.__table__, RolePermission.__table__, SystemParameter.__table__, BusinessRecord.__table__],
            ))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.identity = {
            "username": "query-admin", "role": "admin", "_actual_role_ids": ["admin"],
            "_page_menu_capability": True,
        }

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    async def test_customer_empty_page_keeps_total_summary_without_related_load(self):
        async with self.sessions() as db:
            db.add(User(
                username="query-admin", display_name="查询管理员", department="上海",
                password_hash="x", role="admin", role_ids=["admin"],
            ))
            db.add(SystemParameter(
                category="customer_type", code="customer", name="客户",
                created_by="query-admin", updated_by="query-admin",
            ))
            customer = BusinessRecord(
                module="customer", serial_no="ENTERPRISE-QUERY-CUSTOMER",
                title="ＡＢＣ公司", customer="", status="正常", owner="query-admin",
                department="上海", data={
                    "customer_type": "客户", "agency_fee_due": 11,
                    "custom_payload": "c" * 4096,
                },
            )
            db.add(customer)
            await db.flush()
            db.add_all([
                BusinessRecord(
                    module="contract" if index % 2 else "case",
                    serial_no=f"ENTERPRISE-QUERY-RELATED-{index:03d}",
                    title="关联记录", customer="ABC公司", status="正常",
                    owner="other", department="上海",
                    data={"case_type": "民事案件", "large_payload": "r" * 4096}
                    if index % 2 == 0 else {"large_payload": "r" * 4096},
                ) for index in range(100)
            ])
            db.add_all([
                BusinessRecord(
                    module="hr", serial_no=f"ENTERPRISE-QUERY-HR-{index:03d}",
                    title="员工", customer="", status="在职", owner=f"other-{index}",
                    department="上海", data={"large_payload": "h" * 4096},
                ) for index in range(100)
            ])
            db.add_all([
                BusinessRecord(
                    module="contract", serial_no="ENTERPRISE-QUERY-BY-ID",
                    title="按客户 ID 关联", customer="", status="正常", owner="other",
                    data={"customer_id": str(customer.id)},
                ),
                BusinessRecord(
                    module="contract", serial_no="ENTERPRISE-QUERY-BY-NO",
                    title="按客户编号关联", customer="", status="正常", owner="other",
                    data={"customer_no": customer.serial_no},
                ),
                BusinessRecord(
                    module="case", serial_no="ENTERPRISE-QUERY-CASE-BY-ID",
                    title="按客户 ID 关联案件", customer="", status="正常", owner="other",
                    data={"customer_record_id": customer.id, "case_type": "民事案件"},
                ),
                BusinessRecord(
                    module="contract", serial_no="ENTERPRISE-QUERY-ARCHIVED",
                    title="归档合同不计数", customer="ABC公司", status="已归档", owner="other",
                    data={},
                ),
            ])
            await db.commit()

        loaded_related = []
        async with self.sessions() as db:
            def record_load(_session, instance):
                if isinstance(instance, BusinessRecord) and instance.module in {"contract", "case", "hr"}:
                    loaded_related.append(instance.id)

            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            result = await list_customers(
                scope="company", customer_name="", customer_type="客户", manager="",
                page=999, page_size=15, identity=self.identity, db=db,
            )
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["summary"]["agency_fee_due"], 11)
        self.assertEqual(loaded_related, [])

        loaded_page = []
        async with self.sessions() as db:
            def first_page_load(_session, instance):
                if isinstance(instance, BusinessRecord):
                    loaded_page.append((instance.module, instance.id))

            event.listen(db.sync_session, "loaded_as_persistent", first_page_load)
            first_page = await list_customers(
                scope="company", customer_name="", customer_type="客户", manager="",
                page=1, page_size=15, identity=self.identity, db=db,
            )
        self.assertEqual(first_page["total"], 1)
        self.assertEqual(first_page["summary"], result["summary"])
        self.assertEqual(first_page["items"][0]["data"]["contract_count"], 52)
        self.assertEqual(first_page["items"][0]["data"]["civil_case_count"], 51)
        self.assertEqual(first_page["items"][0]["data"]["custom_payload"], "c" * 4096)
        self.assertEqual([module for module, _ in loaded_page], ["customer"])
        baseline_path = os.environ.get("E07_BASELINE_CRM_ROUTER", "")
        if baseline_path:
            baseline_spec = spec_from_file_location("e07_baseline_crm_router", baseline_path)
            baseline_router = module_from_spec(baseline_spec)
            baseline_spec.loader.exec_module(baseline_router)
            async with self.sessions() as db:
                baseline_page = await baseline_router.list_customers(
                    scope="company", customer_name="", customer_type="客户", manager="",
                    page=1, page_size=15, identity=dict(self.identity), db=db,
                )
            self.assertEqual(first_page, baseline_page)

    async def test_company_customer_page_loads_only_page_and_streams_global_totals(self):
        async with self.sessions() as db:
            db.add(User(username="query-admin", display_name="查询管理员", department="上海", password_hash="x", role="admin", role_ids=["admin"]))
            db.add(SystemParameter(category="customer_type", code="customer", name="客户"))
            db.add_all(BusinessRecord(
                module="customer", serial_no=f"BOUNDED-CUSTOMER-{index:04d}", title=f"客户{index}",
                owner="query-admin", status="正常", department="上海",
                data={"customer_type": "客户", "agency_fee_due": index, "large_payload": "x" * 4096},
            ) for index in range(501))
            await db.commit()
        loaded = []
        async with self.sessions() as db:
            def record_load(_session, instance):
                if isinstance(instance, BusinessRecord):
                    loaded.append(instance.serial_no)

            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            result = await list_customers(
                scope="company", customer_name="", customer_type="客户", manager="",
                page=2, page_size=3, identity=self.identity, db=db,
            )
        self.assertEqual(result["total"], 501)
        self.assertEqual(result["summary"]["agency_fee_due"], 125250)
        self.assertEqual([item["serial_no"] for item in result["items"]], [
            "BOUNDED-CUSTOMER-0497", "BOUNDED-CUSTOMER-0496", "BOUNDED-CUSTOMER-0495",
        ])
        self.assertEqual(len(loaded), 3)

    async def test_owned_task_relation_is_filtered_before_display_projection(self):
        async with self.sessions() as db:
            db.add(User(
                username="query-admin", display_name="查询管理员", department="上海",
                password_hash="x", role="admin", role_ids=["admin"],
            ))
            db.add_all([
                BusinessRecord(
                    module="task", serial_no=f"ENTERPRISE-QUERY-TASK-OTHER-{index:03d}",
                    title="协作任务", customer="", status="待处理", owner="other",
                    department="上海", data={"initiator": "other", "collaborators": ["query-admin"]},
                ) for index in range(100)
            ])
            db.add_all([
                BusinessRecord(
                    module="task", serial_no="ENTERPRISE-QUERY-TASK-OWNED-1",
                    title="本人任务一", customer="", status="待处理", owner="query-admin",
                    department="上海", data={"initiator": "other", "deadline": "2026-12-01"},
                ),
                BusinessRecord(
                    module="task", serial_no="ENTERPRISE-QUERY-TASK-OWNED-2",
                    title="本人任务二", customer="", status="待处理", owner="query-admin",
                    department="上海", data={"initiator": "other", "deadline": "2026-12-02"},
                ),
            ])
            await db.commit()

        loaded_tasks = []
        async with self.sessions() as db:
            def record_load(_session, instance):
                if isinstance(instance, BusinessRecord) and instance.module == "task":
                    loaded_tasks.append(instance.serial_no)

            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            result = await list_tasks(
                scope="mine", relation="owned", page_id=None,
                sort_by="deadline", sort_order="desc", page=1, page_size=15,
                identity=self.identity, db=db,
            )
        self.assertEqual(len(loaded_tasks), 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["summary"]["total"], 2)
        self.assertEqual([item["serial_no"] for item in result["items"]], [
            "ENTERPRISE-QUERY-TASK-OWNED-2", "ENTERPRISE-QUERY-TASK-OWNED-1",
        ])

        loaded_hr = []
        async with self.sessions() as db:
            def employee_load(_session, instance):
                if isinstance(instance, BusinessRecord) and instance.module == "hr":
                    loaded_hr.append(instance.id)

            event.listen(db.sync_session, "loaded_as_persistent", employee_load)
            empty = await list_tasks(
                scope="mine", relation="initiated", page_id=None,
                sort_by="deadline", sort_order="desc", page=1, page_size=15,
                identity=self.identity, db=db,
            )
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["summary"]["total"], 0)
        self.assertEqual(loaded_hr, [])


class SQLiteCustomerTaskQueryTest(CustomerTaskQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "设置 CUSTOMER_TASK_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresCustomerTaskQueryTest(CustomerTaskQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

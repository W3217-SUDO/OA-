"""501580（陶国南 11-05 确认）：系统中心“自动任务”“逾期扣款”按部门/角色排除。

覆盖：设置校验；部门或人事角色任一取消勾选就排除；排除的人不生成自动任务、不记超期绩效，
已记的绩效保留；两个设置各自独立；接口读写与页面菜单映射（各自单独授权）。
"""

import unittest
from datetime import date, timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.case_automation import _create
from app.core.constants import DEFAULT_SYSTEM_CONFIGS, DEFAULT_SYSTEM_MENUS
from app.core.tasks import _apply_task_overdue_performance
from app.core.task_scopes import (
    AUTOMATIC_TASK_SCOPE_KEY, OVERDUE_PENALTY_SCOPE_KEY, load_scope, user_excluded, validate_scope,
)
from app.data_models.identity import Department, JobRole
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemConfig, User
from app.security import _PAGE_MENU_PREFIXES, current_identity

API = settings.api_prefix
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "管理部"}
LAWYER = {"username": "lawyer1", "role": "user", "role_ids": ["user"], "display_name": "律师甲", "department": "诉讼部"}
EMPTY = {"excluded_departments": [], "excluded_roles": []}


class TaskScopes501580Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        overdue = (date.today() - timedelta(days=3)).isoformat()
        async with self.sessions() as db:
            db.add_all([
                Department(code="SS", name="诉讼部"), Department(code="DC", name="调查部"),
                JobRole(code="ASSISTANT", name="律师助理", permissions=[], field_keys=[]),
                JobRole(code="INVESTIGATOR", name="调查员", permissions=[], field_keys=[]),
                User(username="admin", display_name="管理者", department="管理部", password_hash="x", role="admin", is_active=True),
                User(username="assistant1", display_name="助理甲", department="诉讼部", password_hash="x", role="user",
                     role_ids=["user"], profile={"permission_role": "律师助理"}, is_active=True),
                User(username="investigator1", display_name="调查甲", department="调查部", password_hash="x", role="user",
                     role_ids=["user"], profile={"permission_role_code": "INVESTIGATOR"}, is_active=True),
                SystemConfig(key=AUTOMATIC_TASK_SCOPE_KEY, label="自动任务", group="业务配置", description="", value=EMPTY, updated_by="system"),
                SystemConfig(key=OVERDUE_PENALTY_SCOPE_KEY, label="逾期扣款", group="业务配置", description="", value=EMPTY, updated_by="system"),
                BusinessRecord(id=1, module="case", serial_no="AJ1", title="案件", status="文书准备", owner="assistant1", data={}),
                BusinessRecord(id=11, module="task", serial_no="RW11", title="任务A", status="待接收", owner="assistant1",
                               data={"source": "案件任务", "deadline": overdue, "case_id": 1}),
                BusinessRecord(id=12, module="task", serial_no="RW12", title="任务B", status="待接收", owner="investigator1",
                               data={"source": "案件任务", "deadline": overdue, "case_id": 1,
                                     "performance_impact": {"overdue": True, "overdue_days": 1, "penalty_points": 1,
                                                            "recorded_for": "2026-11-01", "responsible_user": "investigator1"}}),
            ])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://scope-501580.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _set(self, key, value):
        async with self.sessions() as db:
            item = await db.scalar(select(SystemConfig).where(SystemConfig.key == key))
            item.value = value
            await db.commit()

    def test_defaults_menus_and_separate_page_permissions(self):
        self.assertEqual(DEFAULT_SYSTEM_CONFIGS[AUTOMATIC_TASK_SCOPE_KEY]["value"], EMPTY)
        self.assertEqual(DEFAULT_SYSTEM_CONFIGS[OVERDUE_PENALTY_SCOPE_KEY]["value"], EMPTY)
        menus = {key: (parent, label) for key, parent, label, *_ in DEFAULT_SYSTEM_MENUS}
        self.assertEqual(menus["system-parameters-automatic-task"], ("system-parameters", "自动任务"))
        self.assertEqual(menus["system-parameters-overdue-penalty"], ("system-parameters", "逾期扣款"))
        prefixes = dict(_PAGE_MENU_PREFIXES)
        self.assertEqual(prefixes["/system/task-scopes/automatic-task"], ("system-parameters-automatic-task", "@root:system"))
        self.assertEqual(prefixes["/system/task-scopes/overdue-penalty"], ("system-parameters-overdue-penalty", "@root:system"))

    def test_validate_scope(self):
        self.assertEqual(validate_scope({"excluded_departments": [" 调查部 ", "调查部"], "excluded_roles": []}),
                         {"excluded_departments": ["调查部"], "excluded_roles": []})
        for bad in ({"excluded_departments": "调查部"}, {"other": []}, {"excluded_roles": [1]}, []):
            with self.assertRaises(HTTPException):
                validate_scope(bad)

    async def test_department_or_role_excludes(self):
        async with self.sessions() as db:
            assistant = await db.scalar(select(User).where(User.username == "assistant1"))
            investigator = await db.scalar(select(User).where(User.username == "investigator1"))
            self.assertFalse(await user_excluded(assistant, EMPTY, db))
            self.assertTrue(await user_excluded(assistant, {"excluded_departments": ["诉讼部"], "excluded_roles": []}, db))
            self.assertTrue(await user_excluded(assistant, {"excluded_departments": [], "excluded_roles": ["律师助理"]}, db))
            # 人事角色按编码绑定的也能按名称匹配。
            self.assertTrue(await user_excluded(investigator, {"excluded_departments": [], "excluded_roles": ["调查员"]}, db))
            self.assertFalse(await user_excluded(investigator, {"excluded_departments": ["诉讼部"], "excluded_roles": ["律师助理"]}, db))

    async def test_excluded_owner_gets_no_automatic_task(self):
        await self._set(AUTOMATIC_TASK_SCOPE_KEY, {"excluded_departments": [], "excluded_roles": ["律师助理"]})
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, 1)
            owner = await db.scalar(select(User).where(User.username == "assistant1"))
            before = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "task"))
            with self.assertLogs(level="WARNING") as logs:
                result = await _create(case, db, number=1, title="文书过期提醒", owner=owner, initiator=owner,
                                       description="x", trigger_at=date.today(), source="s", days=10)
            self.assertIsNone(result)
            self.assertTrue(any("owner_excluded_by_scope" in line for line in logs.output))
            after = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "task"))
            self.assertEqual(before, after)

    async def test_overdue_penalty_skips_excluded_and_keeps_recorded(self):
        # “自动任务”的设置不影响“逾期扣款”。
        await self._set(AUTOMATIC_TASK_SCOPE_KEY, {"excluded_departments": ["诉讼部", "调查部"], "excluded_roles": []})
        await self._set(OVERDUE_PENALTY_SCOPE_KEY, {"excluded_departments": ["调查部"], "excluded_roles": []})
        async with self.sessions() as db:
            await _apply_task_overdue_performance(db)
        async with self.sessions() as db:
            first = await db.get(BusinessRecord, 11)
            second = await db.get(BusinessRecord, 12)
        self.assertEqual(first.data["performance_impact"]["overdue_days"], 3)
        # 已记的不追溯：保持原值，不再按天累加。
        self.assertEqual(second.data["performance_impact"]["overdue_days"], 1)

    async def test_api_read_write(self):
        response = await self.client.get(f"{API}/system/task-scopes/overdue-penalty")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["value"], EMPTY)
        self.assertEqual([item["name"] for item in body["departments"]], ["诉讼部", "调查部"])
        self.assertEqual({item["name"] for item in body["roles"]}, {"律师助理", "调查员"})
        response = await self.client.put(f"{API}/system/task-scopes/overdue-penalty", json={"value": {"excluded_departments": ["调查部"], "excluded_roles": []}})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            self.assertEqual((await load_scope(db, OVERDUE_PENALTY_SCOPE_KEY))["excluded_departments"], ["调查部"])
            self.assertEqual(await load_scope(db, AUTOMATIC_TASK_SCOPE_KEY), EMPTY)
        self.assertEqual((await self.client.get(f"{API}/system/task-scopes/other")).status_code, 404)
        app.dependency_overrides[current_identity] = lambda: LAWYER
        self.assertEqual((await self.client.get(f"{API}/system/task-scopes/automatic-task")).status_code, 403)


if __name__ == "__main__":
    unittest.main()

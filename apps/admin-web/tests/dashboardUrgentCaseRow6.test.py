"""9.22 第6行：控制台紧急案件与案件任务期限及菜单权限保持一致。"""

import unittest
from datetime import date, datetime, timedelta, timezone

import httpx
import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, User
from app.security import current_identity


class DashboardUrgentCaseRow6Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.manager = "CODEX-922-urgent-manager"
        self.member = "CODEX-922-urgent-member"
        self.other = "CODEX-922-urgent-other"
        async with self.sessions() as db:
            db.add_all([
                JobRole(code="CODEX-922-CASE-COMPANY", name="CODEX-922-公司案件角色", permissions=["case-company"], is_active=True),
                JobRole(code="CODEX-922-CASE-MINE", name="CODEX-922-我的案件角色", permissions=["case-mine"], is_active=True),
                User(username=self.manager, display_name="部门负责人", role="manager", password_hash="x", is_active=True, profile={"permission_role_code": "CODEX-922-CASE-COMPANY"}),
                User(username=self.member, display_name="案件成员", role="user", password_hash="x", is_active=True, profile={"permission_role_code": "CODEX-922-CASE-MINE"}),
                User(username=self.other, display_name="其他成员", role="user", password_hash="x", is_active=True),
            ])
            await db.flush()
            cases = {}
            for suffix, owner, status in (
                ("own", self.member, "文书准备"),
                ("company", self.other, "待立案审批"),
                ("daily", self.other, "文书准备"),
                ("late", self.other, "文书准备"),
                ("merged", self.other, "已合并"),
            ):
                case = BusinessRecord(
                    module="case", serial_no=f"CODEX-922-URGENT-{suffix}", title=suffix,
                    customer="第6行测试客户", owner=owner, status=status,
                    data={"case_type": "民事争议", "handling_lawyer_usernames": [owner]},
                )
                db.add(case)
                await db.flush()
                cases[suffix] = case
            today = date.today()
            for suffix, case_name, source, days, status in (
                ("own", "own", "案件任务", -1, "待处理"),
                ("company", "company", "案件任务", 15, "待接收"),
                ("company-duplicate", "company", "案件任务", 10, "待处理"),
                ("daily", "daily", "日常任务", 2, "待处理"),
                ("late", "late", "案件任务", 16, "待处理"),
                ("merged", "merged", "案件任务", 1, "待处理"),
                ("completed", "daily", "案件任务", 1, "已验收"),
            ):
                case = cases[case_name]
                db.add(BusinessRecord(
                    module="task", serial_no=f"CODEX-922-URGENT-TASK-{suffix}",
                    title=suffix, customer="第6行测试客户", owner=case.owner, status=status,
                    data={"source": source, "deadline": (today + timedelta(days=days)).isoformat(),
                          "case_id": case.id, "case_no": case.serial_no},
                ))
            await db.commit()
            self.expected_company_case_ids = {cases["own"].id, cases["company"].id}
            self.expected_personal_case_ids = {cases["own"].id}
            self.company_case_id = cases["company"].id

        async def database():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[current_identity] = lambda: {"username": self.manager, "role": "manager"}
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://dashboard-row6.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def _dashboard_and_cases(self):
        metrics_response = await self.client.get(f"{settings.api_prefix}/dashboard", params={"section": "metrics"})
        self.assertEqual(metrics_response.status_code, 200, metrics_response.text)
        case_response = await self.client.post(
            f"{settings.api_prefix}/cases/search",
            json={"dashboard_queue": "urgent-cases", "scope": "company", "page_size": 20},
        )
        self.assertEqual(case_response.status_code, 200, case_response.text)
        metric = next(item for item in metrics_response.json()["metrics"] if item["key"] == "urgent-cases")
        return metric, case_response.json()

    async def test_company_case_permission_counts_due_case_tasks_and_matches_drilldown(self):
        metric, search = await self._dashboard_and_cases()
        self.assertEqual(metric["value"], "2件")
        self.assertEqual(search["total"], 2)
        self.assertEqual({item["id"] for item in search["items"]}, self.expected_company_case_ids)

    async def test_without_company_case_permission_only_personal_cases_are_counted(self):
        app.dependency_overrides[current_identity] = lambda: {"username": self.member, "role": "user"}
        metric, search = await self._dashboard_and_cases()
        self.assertEqual(metric["value"], "1件")
        self.assertEqual(search["total"], 1)
        self.assertEqual({item["id"] for item in search["items"]}, self.expected_personal_case_ids)

    async def test_company_case_menu_opens_drilldown_record_with_real_identity(self):
        app.dependency_overrides.pop(current_identity)
        token = jwt.encode(
            {"sub": self.manager, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.secret_key, algorithm="HS256",
        )
        response = await self.client.get(
            f"{settings.api_prefix}/records/{self.company_case_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], self.company_case_id)


if __name__ == "__main__":
    unittest.main()

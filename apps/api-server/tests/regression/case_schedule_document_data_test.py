"""文书测试数据第2行：三个排期范围的真实接口与隔离数据回归。"""

import unittest
from datetime import date

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, HearingSchedule, RolePermission, User
from app.security import current_identity


PREFIX = "CODEXDOCSCHED"


class CaseScheduleDocumentDataTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {"username": PREFIX + "-me", "display_name": "本人", "department": PREFIX,
                         "role": "admin", "role_ids": ["admin", "user"], "_actual_role_ids": ["user"], "_page_menu_capability": True}
        async with self.sessions() as db:
            root = Department(code=PREFIX, name=PREFIX)
            db.add(root)
            await db.flush()
            db.add(Department(code=PREFIX + "-sub", name=PREFIX + "-sub", parent_department_id=root.id))
            db.add(RolePermission(role="user", display_name=PREFIX, data_scope="本人数据", menu_keys=["case-mine-schedule", "case-dept-schedule", "case-company-schedule"], field_keys=[]))
            for suffix, department in [("me", PREFIX), ("peer", PREFIX), ("sub", PREFIX + "-sub"), ("other", PREFIX + "-other")]:
                db.add(User(username=PREFIX + "-" + suffix, display_name=suffix, department=department, role="user", role_ids=["user"], password_hash="unused", is_active=True))
            records = []
            for index, suffix in enumerate(["me", "peer", "sub", "other"]):
                records.append(BusinessRecord(module="case", serial_no=PREFIX + "-" + suffix, title=suffix, owner="unrelated-owner", department="来源部门",
                    status="一审立案受理", data={"case_type": "民事争议", "hearing_lawyer_username": PREFIX + "-" + suffix,
                    "handling_lawyer_usernames": [PREFIX + "-" + suffix], "first_court_hearing_date": f"2026-10-{15 + index}T09:00:00"}))
            db.add_all(records)
            await db.flush()
            self.mine_id = records[0].id
            await db.commit()
        self.previous = dict(app.dependency_overrides)
        async def database():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://schedule.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        async with self.sessions() as db:
            await db.execute(delete(HearingSchedule))
            await db.execute(delete(BusinessRecord))
            await db.execute(delete(User))
            await db.execute(delete(RolePermission))
            await db.execute(delete(Department).where(Department.parent_department_id.is_not(None)))
            await db.execute(delete(Department))
            await db.commit()
            for model in [HearingSchedule, BusinessRecord, User, RolePermission, Department]:
                self.assertEqual(await db.scalar(select(func.count()).select_from(model)), 0)
        await self.engine.dispose()

    async def query(self, scope, **params):
        return await self.client.get(settings.api_prefix + "/cases/special-records", params={"kind": "schedule", "scope": scope, **params})

    async def test_scopes_use_court_dates_without_schedule_rows_and_do_not_leak_company_data(self):
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(HearingSchedule)), 0)
        for scope, suffixes in [("mine", ["me"]), ("department", ["me", "peer", "sub"]), ("company", ["me", "peer", "sub", "other"])]:
            response = await self.query(scope)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["total"], len(suffixes))
            self.assertEqual([item["case_no"] for item in response.json()["items"]], [PREFIX + "-" + suffix for suffix in suffixes])
        # 同样的用户名片段不能变成本人的案件关系。
        self.identity = {**self.identity, "username": PREFIX + "-m"}
        response = await self.query("mine")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 0)

    async def test_one_sided_dates_both_dates_order_and_pagination(self):
        for filters, expected in [({"hearing_from": "2026-10-17"}, ["sub", "other"]),
                                  ({"hearing_to": "2026-10-16"}, ["me", "peer"]),
                                  ({"hearing_from": "2026-10-16", "hearing_to": "2026-10-17"}, ["peer", "sub"])]:
            response = await self.query("company", **filters)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([item["case_no"] for item in response.json()["items"]], [PREFIX + "-" + suffix for suffix in expected])
        response = await self.query("department", page=2, page_size=2)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 3)
        self.assertEqual([item["case_no"] for item in response.json()["items"]], [PREFIX + "-sub"])
        response = await self.query("mine", hearing_from="2026-10-18", hearing_to="2026-10-15")
        self.assertEqual(response.status_code, 422, response.text)

    async def test_duplicate_schedule_is_not_repeated_and_department_permission_is_required(self):
        async with self.sessions() as db:
            db.add(HearingSchedule(case_record_id=self.mine_id, hearing_date=date(2026, 10, 15), hearing_time="09:00", court="法院", courtroom="", hearing_type="一审开庭", hearing_lawyer=PREFIX + "-me", status="已排期"))
            await db.commit()
        response = await self.query("mine")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        self.assertIn("schedule:", response.json()["items"][0]["id"])
        async with self.sessions() as db:
            permission = await db.scalar(select(RolePermission).where(RolePermission.role == "user"))
            permission.menu_keys = ["case-mine-schedule"]
            denied = await db.scalar(select(User).where(User.username == PREFIX + "-other"))
            denied.profile = {"permission_overrides": {"menu_keys": []}}
            await db.commit()
        response = await self.query("department")
        self.assertEqual(response.status_code, 403, response.text)
        response = await self.query("mine", export_format="xls")
        self.assertEqual(response.status_code, 422, response.text)
        self.identity = {"username": PREFIX + "-other", "role": "viewer", "role_ids": ["viewer"]}
        response = await self.query("company")
        self.assertEqual(response.status_code, 403, response.text)
        response = await self.query("mine", export_format="xls")
        self.assertEqual(response.status_code, 403, response.text)

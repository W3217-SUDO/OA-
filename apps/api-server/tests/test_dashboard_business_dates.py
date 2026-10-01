"""控制台与报表按业务时区统计，最新案件在数据库限制载入量。"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.rpt.router import report_large_screen
from app.core.dashboard_cases import dashboard_cases
from app.database import Base
from app.models import BusinessRecord, User


POSTGRES_URL = os.environ.get("DASHBOARD_DATES_TEST_POSTGRES_URL", "")
NOW = datetime(2026, 12, 31, 16, 30, tzinfo=timezone.utc)
IDENTITY = {"username": "business-date-admin", "role": "admin", "_actual_role_ids": ["admin"]}


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


class BusinessDateAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("业务日期测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_dates_{uuid4().hex[:12]}"
            self.admin_engine = create_async_engine(self.database_url)
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(
                self.database_url, connect_args={"server_settings": {"search_path": self.schema}},
            )
        else:
            self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="日期统计管理员", role="admin", password_hash="test-only"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    def case(self, index, created_at):
        return BusinessRecord(
            module="case", serial_no=f"ENTERPRISE-DATE-{index}", title="日期统计案件",
            customer="", status="一审", owner=IDENTITY["username"], created_at=created_at,
            data={"case_type": "民事案件", "case_register_date": "invalid-old-date", "large_payload": "x" * 4096},
        )

    async def test_month_and_year_boundary_agrees_with_business_filing_date(self):
        dates = [
            datetime(2026, 12, 31, 15, 59, tzinfo=timezone.utc),
            datetime(2026, 12, 31, 16, 0, tzinfo=timezone.utc),
            datetime(2026, 12, 31, 16, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 31, 16, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 31, 15, 59, tzinfo=timezone.utc),
        ]
        async with self.sessions() as db:
            db.add_all([self.case(index, value) for index, value in enumerate(dates)])
            await db.commit()
        with patch("app.core.dashboard_cases.datetime", FrozenDatetime), patch("app.areas.rpt.router.datetime", FrozenDatetime):
            async with self.sessions() as db:
                dashboard = await dashboard_cases(dict(IDENTITY), db)
            async with self.sessions() as db:
                report = await report_large_screen(dict(IDENTITY), db)
        trend = {item["date"]: item["value"] for item in dashboard["case_trend"]}
        self.assertEqual(trend["2027-01"], 2)
        self.assertEqual(trend["2026-12"], 1)
        self.assertEqual(trend["2026-04"], 1)
        self.assertEqual(sum(trend.values()), 4)
        monthly = {item["month"]: item["cases"] for item in report["monthly_trend"]}
        self.assertEqual(monthly["2027-01"], 2)
        self.assertEqual(monthly["2026-12"], 1)
        self.assertEqual(report["employee_ranking"][0]["value"], 2)

    async def test_latest_cases_load_only_thirteen_in_creation_order(self):
        async with self.sessions() as db:
            db.add_all([self.case(index, NOW - timedelta(minutes=index)) for index in range(100)])
            await db.commit()
        loaded = []
        with patch("app.core.dashboard_cases.datetime", FrozenDatetime):
            async with self.sessions() as db:
                event.listen(db.sync_session, "loaded_as_persistent", lambda _session, row: (
                    loaded.append(row.serial_no) if isinstance(row, BusinessRecord) else None
                ))
                result = await dashboard_cases(dict(IDENTITY), db)
        expected = [f"ENTERPRISE-DATE-{index}" for index in range(13)]
        self.assertEqual([item["case_no"] for item in result["latest_cases"]], expected)
        self.assertEqual(loaded, expected)


class SQLiteBusinessDateTest(BusinessDateAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "设置 DASHBOARD_DATES_TEST_POSTGRES_URL 运行专用 PostgreSQL 测试")
class PostgresBusinessDateTest(BusinessDateAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

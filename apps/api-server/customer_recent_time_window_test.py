import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, SystemParameter, User
from app.security import current_identity
from app.areas.crm import router as crm


LOCAL_ZONE = timezone(timedelta(hours=8))


class FixedDateTime(datetime):
    current = None

    @classmethod
    def now(cls, tz=None):
        value = cls.current
        return value if tz is None else value.astimezone(tz)

    def astimezone(self, tz=None):
        # Emulate a process whose local wall-clock zone is +08:00 on any host.
        return self if tz is None else super().astimezone(tz)


class CustomerRecentTimeWindowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {"username": "recent-admin", "role": "admin"}
        async with self.sessions() as db:
            db.add(User(username="recent-admin", role="admin", display_name="CODEX admin", password_hash="test-only"))
            db.add(User(username="recent-user", role="user", display_name="CODEX user", password_hash="test-only"))
            db.add(RolePermission(role="user", display_name="CODEX", data_scope="本人及共享数据",
                                  menu_keys=["customer-recent-contact", "customer-recent-update"], field_keys=["*"]))
            db.add(SystemParameter(category="customer_type", code="customer", name="客户", is_active=True))
            await db.commit()
        self.set_now(2026, 3, 31)
        self.clock = patch.object(crm, "datetime", FixedDateTime)
        self.clock.start()
        self.overrides = dict(app.dependency_overrides)

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://recent-window.test")

    def set_now(self, year, month, day):
        FixedDateTime.current = FixedDateTime(year, month, day, 12, 30, tzinfo=LOCAL_ZONE)

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.overrides)
        self.clock.stop()
        await self.engine.dispose()

    async def add(self, label, value, *, owner="recent-admin", modifier="recent-admin", status="正常"):
        stamp = value if isinstance(value, datetime) else FixedDateTime.current
        contact = value.isoformat() if isinstance(value, datetime) else value
        async with self.sessions() as db:
            row = BusinessRecord(module="customer", serial_no=f"CODEX-RECENT-{label}", title=label, owner=owner,
                                 status=status, updated_at=stamp.astimezone(timezone.utc).replace(tzinfo=None),
                                 data={"last_contact_at": contact, "last_modified_by": modifier, "customer_type": "客户"})
            db.add(row)
            await db.commit()
            return row.id

    async def query(self, scope, **params):
        response = await self.client.get(f"{settings.api_prefix}/customers", params={"scope": scope, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_contact_window_filters_before_total_and_paging(self):
        now = FixedDateTime.current
        start = now.replace(month=2, day=28)
        await self.add("old", start - timedelta(seconds=1))
        boundary = await self.add("boundary", start)
        middle = await self.add("middle", now - timedelta(days=1))
        latest = await self.add("now", now)
        await self.add("future", now + timedelta(seconds=1))
        await self.add("blank", "")
        await self.add("bad", "invalid-date")
        first = await self.query("recent_contact", page=1, page_size=2)
        second = await self.query("recent_contact", page=2, page_size=2)
        self.assertEqual(first["total"], 3)
        self.assertEqual([row["id"] for row in first["items"]], [latest, middle])
        self.assertEqual([row["id"] for row in second["items"]], [boundary])
        self.assertEqual((await self.query("recent_contact", customer_name="old"))["total"], 0)

    async def test_update_window_filters_before_total_and_preserves_actor_scope(self):
        now = FixedDateTime.current
        await self.add("old", now.replace(month=2, day=28) - timedelta(seconds=1))
        boundary = await self.add("boundary", now.replace(month=2, day=28))
        latest = await self.add("now", now)
        await self.add("future", now + timedelta(seconds=1))
        await self.add("other-actor", now, modifier="recent-user")
        result = await self.query("recent_update", page=1, page_size=1)
        self.assertEqual(result["total"], 2)
        self.assertEqual([row["id"] for row in result["items"]], [latest])
        self.assertEqual([row["id"] for row in (await self.query("recent_update", page=2, page_size=1))["items"]], [boundary])

    async def test_calendar_month_clamps_leap_day_and_crosses_year(self):
        for year, month, day, start_year, start_month, start_day in [(2024, 3, 31, 2024, 2, 29), (2026, 1, 31, 2025, 12, 31)]:
            self.set_now(year, month, day)
            start = FixedDateTime(start_year, start_month, start_day, 12, 30, tzinfo=LOCAL_ZONE)
            label = f"{year}-{month}"
            boundary = await self.add(f"{label}-boundary", start)
            await self.add(f"{label}-old", start - timedelta(seconds=1))
            for scope in ("recent_contact", "recent_update"):
                with self.subTest(scope=scope, year=year, month=month):
                    result = await self.query(scope, customer_name=label)
                    self.assertEqual([row["id"] for row in result["items"]], [boundary])

    async def test_contact_offsets_and_legacy_local_wall_clock_share_one_timeline(self):
        now = FixedDateTime.current
        expected = []
        expected.append(await self.add("local", now.replace(tzinfo=None).isoformat()))
        expected.append(await self.add("offset", now.isoformat()))
        expected.append(await self.add("utc", now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")))
        await self.add("future-local", (now + timedelta(seconds=1)).replace(tzinfo=None).isoformat())
        result = await self.query("recent_contact")
        self.assertEqual([row["id"] for row in result["items"]], list(reversed(expected)))

    async def test_other_list_scopes_do_not_gain_a_time_restriction(self):
        old = await self.add("old", FixedDateTime.current - timedelta(days=300))
        for scope in ("mine", "company"):
            result = await self.query(scope)
            self.assertIn(old, [row["id"] for row in result["items"]])

    async def test_user_scope_and_status_rules_remain_in_force(self):
        now = FixedDateTime.current
        own = await self.add("own", now, owner="recent-user", modifier="recent-user")
        await self.add("other", now, modifier="recent-user")
        await self.add("public", now, owner="recent-user", modifier="recent-user", status="公海")
        recycled = await self.add("recycled", now, owner="recent-user", modifier="recent-user", status="已回收")
        self.identity = {"username": "recent-user", "role": "user"}
        contact = await self.query("recent_contact")
        updated = await self.query("recent_update")
        self.assertEqual([row["id"] for row in contact["items"]], [own])
        self.assertEqual({row["id"] for row in updated["items"]}, {own, recycled})


if __name__ == "__main__":
    unittest.main()

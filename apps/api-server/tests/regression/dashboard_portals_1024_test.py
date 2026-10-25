"""首页分端待办（2026-10-24 用户要求）：系统参数里配置律师端、财务行政端、调查端的待办和角色归属。

覆盖：默认配置合法且与用户给定的分端一致；非法配置被拒绝；系统参数接口读写并留审计；
管理员账号看管理端（全部待办），律师角色只看律师端；分端单独统计的数字与点进去的列表同一口径。
"""

import unittest

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.dashboard_portals import DEFAULT_CONFIG, ITEM_KEYS, MANAGE_PORTAL, validate_config
from app.data_models.identity import JobRole
from app.database import Base, get_db
from app.main import app, dashboard
from app.models import BusinessRecord, SystemConfig, User
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1024-PORTAL-"
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "测试部"}
LAWYER = {"username": "lawyer1", "role": "user", "role_ids": ["user"], "display_name": "律师甲", "department": "测试部"}


class DashboardPortalsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理者", department="测试部", password_hash="x", role="admin", is_active=True),
                User(username="lawyer1", display_name="律师甲", department="测试部", password_hash="x", role="user",
                     role_ids=["user"], profile={"permission_role": "承办律师"}, is_active=True),
                JobRole(code="HANDLING-LAWYER", name="承办律师", permissions=[], field_keys=[]),
                SystemConfig(key="dashboard_portals", label="首页分端待办", group="业务配置", description="", value=DEFAULT_CONFIG, updated_by="system"),
                BusinessRecord(module="notary", serial_no=f"{PREFIX}N1", title="公证1", customer="", status="待审核",
                               owner="other", department="测试部", data={}),
                BusinessRecord(module="notary", serial_no=f"{PREFIX}N2", title="公证2", customer="", status="审核通过",
                               owner="other", department="测试部", data={}),
            ])
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://portal-1024.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    def test_default_config_matches_requested_split(self):
        value = validate_config(DEFAULT_CONFIG)
        portals = {portal["name"]: portal["items"] for portal in value["portals"]}
        self.assertEqual(list(portals), ["律师端", "财务行政端", "调查端"])
        self.assertEqual(portals["律师端"], ["task", "fee-unpaid", "appeal", "evidence", "opinion", "receipts-pending", "receivable", "archive-closing"])
        self.assertEqual(portals["财务行政端"], ["task", "fee-unpaid", "internal-fee-audit", "fee-audit", "settlement-audit", "archive-fee", "seal-stamping"])
        self.assertEqual(portals["调查端"], ["task", "fee-unpaid", "clue-audit", "notary-review", "evidence"])
        self.assertEqual(value["role_portals"]["系统管理员"], [MANAGE_PORTAL])

    def test_invalid_config_is_rejected(self):
        broken = [
            {**DEFAULT_CONFIG, "portals": DEFAULT_CONFIG["portals"][:2]},
            {**DEFAULT_CONFIG, "portals": [{**DEFAULT_CONFIG["portals"][0], "items": ["task", "no-such-item"]}, *DEFAULT_CONFIG["portals"][1:]]},
            {**DEFAULT_CONFIG, "portals": [{**DEFAULT_CONFIG["portals"][0], "items": list(ITEM_KEYS)}, *DEFAULT_CONFIG["portals"][1:]]},
            {**DEFAULT_CONFIG, "role_portals": {"承办律师": ["unknown"]}},
        ]
        for value in broken:
            with self.assertRaises(HTTPException):
                validate_config(value)

    async def test_settings_endpoint_reads_and_saves(self):
        response = await self.client.get(f"{API}/system/dashboard-portals")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(len(body["items"]), len(ITEM_KEYS))
        self.assertIn("承办律师", [role["name"] for role in body["roles"]])
        value = body["value"]
        value["portals"][0]["items"] = ["task", "appeal"]
        value["role_portals"]["承办律师"] = ["lawyer", "investigation"]
        saved = await self.client.put(f"{API}/system/dashboard-portals", json={"value": value})
        self.assertEqual(saved.status_code, 200, saved.text)
        again = (await self.client.get(f"{API}/system/dashboard-portals")).json()["value"]
        self.assertEqual(again["portals"][0]["items"], ["task", "appeal"])
        self.assertEqual(again["role_portals"]["承办律师"], ["lawyer", "investigation"])
        rejected = await self.client.put(f"{API}/system/dashboard-portals", json={"value": {**value, "portals": value["portals"][:1]}})
        self.assertEqual(rejected.status_code, 422)
        async with self.sessions() as db:
            audits = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "system_audit"))).all()
        self.assertIn("系统配置:dashboard_portals", [audit.title for audit in audits])

    async def test_admin_sees_manage_portal_and_list_counts(self):
        async with self.sessions() as db:
            result = await dashboard(ADMIN, db, section="portals")
        self.assertEqual([portal["key"] for portal in result["portals"]], [MANAGE_PORTAL])
        self.assertEqual(result["portals"][0]["items"], list(ITEM_KEYS))
        extra = {item["key"] for item in result["portal_items"] if item["source"] == "extra"}
        self.assertEqual(set(result["portal_counts"]), extra)
        listed = await self.client.get(f"{API}/records", params={"module": "notary", "record_status": "待审核", "page": 1, "page_size": 1})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(result["portal_counts"]["notary-review"], listed.json()["total"])
        self.assertEqual(result["portal_counts"]["notary-review"], 1)

    async def test_admin_without_manage_tick_sees_no_portals(self):
        # 用户 2026-10-25：系统管理员那一行没勾就不显示，首页回到原来的“我的待办”。
        async with self.sessions() as db:
            item = await db.scalar(select(SystemConfig).where(SystemConfig.key == "dashboard_portals"))
            roles = {role: keys for role, keys in DEFAULT_CONFIG["role_portals"].items() if role != "系统管理员"}
            item.value = {**DEFAULT_CONFIG, "role_portals": roles}
            await db.commit()
        async with self.sessions() as db:
            result = await dashboard(ADMIN, db, section="portals")
        self.assertEqual(result["portals"], [])
        self.assertEqual(result["portal_counts"], {})

    async def test_lawyer_role_sees_lawyer_portal_only(self):
        async with self.sessions() as db:
            result = await dashboard(LAWYER, db, section="portals")
        self.assertEqual([portal["name"] for portal in result["portals"]], ["律师端"])
        self.assertEqual(set(result["portal_counts"]), {"receipts-pending", "receivable", "archive-closing"})


if __name__ == "__main__":
    unittest.main()

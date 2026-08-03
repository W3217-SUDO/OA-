"""Isolated runtime contracts for bounded seal-asset audit history."""

import unittest
from datetime import datetime, timedelta

import httpx
from fastapi import status
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import SealAsset, SealAssetAudit
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "seal-audit-d10-admin", "role": "admin", "display_name": "印章管理员", "department": "上海分所"}
MANAGER = {"username": "seal-audit-d10-manager", "role": "manager", "display_name": "印章负责人", "department": "上海分所"}
USER = {"username": "seal-audit-d10-user", "role": "user", "display_name": "普通员工", "department": "上海分所"}


class SealAssetAuditBackendD10Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sql_statements = []
        self._sql_listener = lambda conn, cursor, statement, parameters, context, executemany: self.sql_statements.append((statement, parameters))
        event.listen(self.engine.sync_engine, "before_cursor_execute", self._sql_listener)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            asset = SealAsset(code="SEAL-D10-A", name="D10 公章", seal_type="公章", custodian="admin", location="A01", status="可用")
            other = SealAsset(code="SEAL-D10-B", name="D10 合同章", seal_type="合同章", custodian="admin", location="A02", status="可用")
            db.add_all([asset, other])
            await db.flush()
            base = datetime(2025, 1, 1, 10, 0, 0)
            db.add_all([
                SealAssetAudit(asset_id=asset.id, asset_code=asset.code, asset_name=asset.name, action="创建印章资产", operator="admin", comment="创建记录", created_at=base),
                SealAssetAudit(asset_id=asset.id, asset_code=asset.code, asset_name=asset.name, action="修改印章资产", operator="alice", comment="更换保管人", created_at=base + timedelta(days=1)),
                SealAssetAudit(asset_id=asset.id, asset_code=asset.code, asset_name=asset.name, action="完成实际用印", operator="bob", comment="案件盖章", created_at=base + timedelta(days=2)),
            ] + [
                SealAssetAudit(asset_id=asset.id, asset_code=asset.code, asset_name=asset.name, action="完成实际用印", operator="operator", comment=f"历史记录 {index}", created_at=base + timedelta(days=index))
                for index in range(3, 17)
            ])
            db.add(SealAssetAudit(asset_id=other.id, asset_code=other.code, asset_name=other.name, action="创建印章资产", operator="other", comment="其他资产", created_at=base + timedelta(days=3)))
            await db.commit()
            self.asset_id = asset.id
        self.sql_statements.clear()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://seal-audit-d10.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        event.remove(self.engine.sync_engine, "before_cursor_execute", self._sql_listener)
        await self.engine.dispose()

    async def test_audit_paging_order_filters_and_bounded_sql(self):
        response = await self.client.get(f"{API}/seals/assets/{self.asset_id}/audit")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        payload = response.json()
        self.assertEqual((payload["total"], payload["page"], payload["page_size"], payload["pages"]), (17, 1, 15, 2))
        self.assertEqual(len(payload["items"]), 15)
        self.assertTrue(all(set(("id", "asset_id", "asset_code", "asset_name", "action", "operator", "comment", "created_at")) <= set(item) for item in payload["items"]))
        page2 = await self.client.get(f"{API}/seals/assets/{self.asset_id}/audit", params={"page": 2})
        self.assertEqual(page2.status_code, status.HTTP_200_OK, page2.text)
        self.assertEqual((page2.json()["total"], page2.json()["page"], page2.json()["page_size"], page2.json()["pages"], len(page2.json()["items"])), (17, 2, 15, 2, 2))
        created = [item["created_at"] for item in payload["items"] + page2.json()["items"]]
        self.assertEqual(created, sorted(created, reverse=True))
        audit_queries = [sql.lower() for sql, _ in self.sql_statements if "seal_asset_audits" in sql.lower() and "asset_id" in sql.lower()]
        self.assertTrue(any("count" in sql for sql in audit_queries), audit_queries)
        self.assertTrue(any("select seal_asset_audits" in sql for sql in audit_queries), audit_queries)
        filtered = await self.client.get(f"{API}/seals/assets/{self.asset_id}/audit", params={"action": "修改", "operator": "alice", "keyword": "保管", "date_from": "2025-01-02", "date_to": "2025-01-02"})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK, filtered.text)
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(filtered.json()["items"][0]["comment"], "更换保管人")

    async def test_missing_asset_and_non_admin_are_rejected(self):
        missing = await self.client.get(f"{API}/seals/assets/999999/audit")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)
        app.dependency_overrides[current_identity] = lambda: MANAGER
        manager = await self.client.get(f"{API}/seals/assets/{self.asset_id}/audit")
        self.assertEqual(manager.status_code, status.HTTP_200_OK, manager.text)
        app.dependency_overrides[current_identity] = lambda: USER
        forbidden = await self.client.get(f"{API}/seals/assets/{self.asset_id}/audit")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)


if __name__ == "__main__":
    unittest.main()

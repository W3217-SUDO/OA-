"""智能体每轮看到本人及全局共享MCP连接目录（只有名称、工具名和说明，没有凭据）。"""
import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.capability_market.connector_store import connector_config_key
from app.areas.capability_market.mcp_access import runtime_connection_catalog
from app.areas.capability_market.personal_mcp import SOURCE
from app.database import Base
from app.models import SystemConfig


def _record(item_id, scope, owner, name):
    return SystemConfig(key=connector_config_key(item_id, scope, owner), label=name, updated_by="t", value={
        "schema_version": 1, "item_id": item_id, "display_name": name, "scope": scope, "owner": owner, "source": SOURCE,
        "revision": "r1", "status": "verified", "encrypted": "SECRET-TOKEN",
        "servers": [{"name": "default", "server_name": "s", "tools": [{"name": "chatCompletions", "description": "搜索实时信息"}]}]})


class RuntimeCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_global_and_own_connections_listed_without_credentials(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            db.add_all([_record("personal-mcp-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "global", "global", "baidu-ai-search"),
                        _record("personal-mcp-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "personal", "alice", "alice-own"),
                        _record("personal-mcp-cccccccccccccccccccccccccccccccc", "personal", "bob", "bob-own")])
            await db.commit()
            catalog = await runtime_connection_catalog({"username": "alice", "role": "user"}, db)
        await engine.dispose()
        self.assertEqual(sorted(item["name"] for item in catalog), ["alice-own", "baidu-ai-search"])
        self.assertEqual(catalog[0]["tools"][0]["name"], "chatCompletions")
        self.assertNotIn("SECRET-TOKEN", repr(catalog))


if __name__ == "__main__":
    unittest.main()

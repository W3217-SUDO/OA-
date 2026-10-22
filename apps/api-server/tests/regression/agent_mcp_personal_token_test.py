"""MCP 个人访问令牌：只存摘要、可撤销可过期、账号停用即失效、只读过滤、审计和限流。"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_mcp import personal_tokens
from app.agent_mcp.auth import AuthContext
from app.data_models.mcp_tokens import McpAccessToken, McpCallLog
from app.database import Base
from app.models import User

ADMIN = {"username": "boss"}


class PersonalTokenTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="boss", display_name="管理者", role="admin", role_ids=["admin"], password_hash="x"))
            await db.commit()
        patcher = patch.object(personal_tokens, "SessionLocal", self.sessions)
        patcher.start()
        self.addCleanup(patcher.stop)
        personal_tokens._calls.clear()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _create(self, name="笔记本", days=30):
        async with self.sessions() as db:
            return await personal_tokens.create_token(ADMIN, db, name, days)

    async def test_plain_token_is_returned_once_and_only_hash_is_stored(self):
        created = await self._create()
        self.assertTrue(personal_tokens.is_personal_token(created["token"]))
        async with self.sessions() as db:
            row = await db.scalar(select(McpAccessToken))
            listed = await personal_tokens.list_tokens(ADMIN, db)
        self.assertEqual(row.token_hash, personal_tokens.token_hash(created["token"]))
        self.assertNotIn(created["token"], repr(row.__dict__))
        self.assertNotIn("token", listed[0])
        self.assertEqual(listed[0]["status"], "active")

    async def test_validity_and_active_count_limits(self):
        for days in (0, personal_tokens.MAX_DAYS + 1):
            with self.assertRaises(HTTPException):
                await self._create(days=days)
        for _ in range(personal_tokens.MAX_ACTIVE_PER_USER):
            await self._create()
        with self.assertRaises(HTTPException) as caught:
            await self._create()
        self.assertEqual(caught.exception.status_code, 409)

    async def test_authenticate_accepts_active_and_rejects_revoked_expired_unknown_or_disabled(self):
        created = await self._create()
        token_id, username, session = await personal_tokens.authenticate(created["token"])
        self.assertEqual((token_id, username), (created["id"], "boss"))
        self.assertTrue(session)
        with self.assertRaises(HTTPException):
            await personal_tokens.authenticate("oamcp_" + "x" * 40)
        async with self.sessions() as db:
            await personal_tokens.revoke_token(ADMIN, db, created["id"])
        with self.assertRaises(HTTPException) as caught:
            await personal_tokens.authenticate(created["token"])
        self.assertEqual(caught.exception.status_code, 401)

        expired = await self._create(name="过期")
        async with self.sessions() as db:
            row = await db.get(McpAccessToken, expired["id"])
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(HTTPException):
            await personal_tokens.authenticate(expired["token"])

        disabled = await self._create(name="停用")
        async with self.sessions() as db:
            user = await db.scalar(select(User))
            user.is_active = False
            await db.commit()
        with self.assertRaises(HTTPException):
            await personal_tokens.authenticate(disabled["token"])

    async def test_rate_limit(self):
        created = await self._create()
        with patch.object(personal_tokens, "RATE_LIMIT_PER_MINUTE", 3):
            for _ in range(3):
                await personal_tokens.authenticate(created["token"])
            with self.assertRaises(HTTPException) as caught:
                await personal_tokens.authenticate(created["token"])
        self.assertEqual(caught.exception.status_code, 429)

    async def test_record_call_writes_audit_and_counts(self):
        created = await self._create()
        await personal_tokens.record_call(created["id"], "boss", "list_cases", True, {"page": 1})
        async with self.sessions() as db:
            log = await db.scalar(select(McpCallLog))
            listed = await personal_tokens.list_tokens(ADMIN, db)
        self.assertEqual((log.tool_name, log.ok, log.token_id), ("list_cases", 1, created["id"]))
        self.assertEqual(listed[0]["call_count"], 1)
        self.assertIsNotNone(listed[0]["last_used_at"])


class ReadOnlyGatewayTest(unittest.IsolatedAsyncioTestCase):
    def _context(self, token_id):
        return AuthContext(application=object(), bearer="jwt", scope={}, token_id=token_id)

    async def test_write_tools_are_hidden_and_refused_for_personal_token(self):
        from app.agent_mcp import gateway, service
        reader = SimpleNamespace(name="list_cases", is_write=False, to_mcp=lambda: {
            "name": "list_cases", "description": "查案", "inputSchema": {"type": "object"}})
        writer = SimpleNamespace(name="create_case", is_write=True, to_mcp=lambda: {
            "name": "create_case", "description": "建案", "inputSchema": {"type": "object"}})
        catalog = SimpleNamespace(tools=[reader, writer], get=lambda name: {"list_cases": reader, "create_case": writer}[name])
        for token_id, expected in ((7, {"oa_list_tool_groups", "oa_search_tools", "list_cases"}),
                                   (None, {"oa_list_tool_groups", "oa_search_tools", "list_cases", "create_case"})):
            with patch.object(gateway, "get_auth_context", lambda token_id=token_id: self._context(token_id)), \
                 patch.object(gateway, "get_catalog", lambda _app: catalog):
                listed = await gateway._list_tools(None, None)
            self.assertEqual({tool.name for tool in listed.tools}, expected)
        with patch.object(service, "get_auth_context", lambda: self._context(7)), \
             patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "authenticated_identity", lambda: _async({"username": "boss"})):
            with self.assertRaises(HTTPException) as caught:
                await service.call_tool("create_case", {})
        self.assertEqual(caught.exception.status_code, 403)

    async def test_personal_token_never_valid_outside_mcp_entry(self):
        from app.agent_mcp.auth import RequestAuthContextMiddleware
        seen = {}

        async def app(scope, receive, send):
            from app.agent_mcp.auth import get_auth_context
            seen["bearer"] = get_auth_context().bearer

        middleware = RequestAuthContextMiddleware(app, application=object())
        await middleware({"type": "http", "path": "/api/v1/cases", "headers": [(b"authorization", b"Bearer oamcp_" + b"y" * 40)]}, None, None)
        self.assertTrue(seen["bearer"].startswith("oamcp_"))  # 原样透传给普通接口，由 JWT 校验拒绝


async def _async(value):
    return value


if __name__ == "__main__":
    unittest.main()

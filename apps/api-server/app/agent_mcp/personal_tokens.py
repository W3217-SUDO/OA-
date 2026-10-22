"""MCP 个人访问令牌：管理员在 OA 里生成，供自己电脑上的本地 agent 只读访问 OA。

令牌只对 /mcp 入口有效，只读，只给系统管理员；每次调用都重新核对账号状态和管理员身份，并记审计。
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import secrets
import time

from fastapi import HTTPException
from sqlalchemy import select, update

from app.database import SessionLocal
from app.data_models.mcp_tokens import McpAccessToken, McpCallLog

logger = logging.getLogger(__name__)
TOKEN_PREFIX = "oamcp_"
DEFAULT_DAYS = 30
MAX_DAYS = 90
MAX_ACTIVE_PER_USER = 5
RATE_LIMIT_PER_MINUTE = 120
SESSION_MINUTES = 5  # 令牌换出的内部登录凭据有效期，只在单次请求内使用
_calls: dict[int, deque] = defaultdict(deque)


def token_hash(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def is_personal_token(value: str) -> bool:
    return value.startswith(TOKEN_PREFIX) and len(value) > len(TOKEN_PREFIX) + 20


def generate() -> tuple[str, str, str]:
    plain = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return plain, token_hash(plain), plain[:len(TOKEN_PREFIX) + 4]


def _view(row: McpAccessToken) -> dict:
    now = datetime.now(timezone.utc)
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    status = "revoked" if row.revoked_at else "expired" if expires <= now else "active"
    return {
        "id": row.id, "name": row.name, "username": row.username, "token_prefix": row.token_prefix,
        "status": status, "created_at": row.created_at, "expires_at": row.expires_at,
        "last_used_at": row.last_used_at, "call_count": row.call_count, "revoked_at": row.revoked_at,
    }


async def create_token(identity: dict, db, name: str, days: int) -> dict:
    if not 1 <= days <= MAX_DAYS:
        raise HTTPException(422, f"有效期必须为 1 至 {MAX_DAYS} 天")
    name = name.strip()
    if not name:
        raise HTTPException(422, "请填写令牌名称，例如“我的笔记本”")
    now = datetime.now(timezone.utc)
    rows = (await db.scalars(select(McpAccessToken).where(
        McpAccessToken.username == identity["username"], McpAccessToken.revoked_at.is_(None)))).all()
    if sum(1 for row in rows if _view(row)["status"] == "active") >= MAX_ACTIVE_PER_USER:
        raise HTTPException(409, f"有效令牌最多 {MAX_ACTIVE_PER_USER} 枚，请先撤销不用的")
    plain, digest, prefix = generate()
    row = McpAccessToken(username=identity["username"], name=name[:100], token_hash=digest, token_prefix=prefix,
                         created_by=identity["username"], expires_at=now + timedelta(days=days))
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {**_view(row), "token": plain}  # 明文只在创建时返回这一次


async def list_tokens(identity: dict, db) -> list[dict]:
    rows = (await db.scalars(select(McpAccessToken).where(McpAccessToken.username == identity["username"])
                             .order_by(McpAccessToken.id.desc()).limit(100))).all()
    return [_view(row) for row in rows]


async def revoke_token(identity: dict, db, token_id: int) -> dict:
    row = await db.scalar(select(McpAccessToken).where(
        McpAccessToken.id == token_id, McpAccessToken.username == identity["username"]))
    if row is None:
        raise HTTPException(404, "令牌不存在")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return _view(row)


async def list_calls(identity: dict, db, limit: int = 50) -> list[dict]:
    rows = (await db.scalars(select(McpCallLog).where(McpCallLog.username == identity["username"])
                             .order_by(McpCallLog.id.desc()).limit(limit))).all()
    return [{"id": row.id, "token_id": row.token_id, "tool_name": row.tool_name, "ok": bool(row.ok),
             "detail": row.detail, "created_at": row.created_at} for row in rows]


def _check_rate(token_id: int) -> None:
    window = _calls[token_id]
    now = time.monotonic()
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(429, f"调用过于频繁，每分钟最多 {RATE_LIMIT_PER_MINUTE} 次")
    window.append(now)


async def authenticate(plain: str) -> tuple[int, str, str]:
    """校验令牌，返回（令牌编号, 用户名, 内部登录凭据）。任何一项不满足都拒绝。"""
    from app.models import User
    from app.security import create_token as create_session, user_role_ids
    async with SessionLocal() as db:
        row = await db.scalar(select(McpAccessToken).where(McpAccessToken.token_hash == token_hash(plain)))
        if row is None or _view(row)["status"] != "active":
            raise HTTPException(401, "MCP 访问令牌无效、已过期或已撤销")
        user = await db.scalar(select(User).where(User.username == row.username))
        if user is None or not user.is_active:
            raise HTTPException(401, "令牌所属账号已停用")
        _check_rate(row.id)
        role = (user_role_ids(user) or ["user"])[0]
        return row.id, row.username, create_session(row.username, role, SESSION_MINUTES)


def _summary(arguments) -> str:
    try:
        text = json.dumps(arguments, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = "?"
    return text[:300]


async def record_call(token_id: int, username: str, tool_name: str, ok: bool, arguments=None, detail: str = "") -> None:
    """审计不能影响调用本身：失败只记日志。"""
    try:
        async with SessionLocal() as db:
            db.add(McpCallLog(token_id=token_id, username=username, tool_name=tool_name[:200], ok=int(ok),
                              detail=(detail or _summary(arguments))[:1000]))
            await db.execute(update(McpAccessToken).where(McpAccessToken.id == token_id).values(
                last_used_at=datetime.now(timezone.utc), call_count=McpAccessToken.call_count + 1))
            await db.commit()
    except Exception:
        logger.exception("MCP 调用审计写入失败 token=%s tool=%s", token_id, tool_name)

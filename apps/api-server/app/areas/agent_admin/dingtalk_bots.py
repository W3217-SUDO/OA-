"""智能体中心 › 钉钉机器人中心：填写收文助手机器人的 AppKey、AppSecret，测试连接。

只有系统管理员能看能改；AppSecret 加密保存，任何接口都不回显。写法和“云端智能体”配置一致。
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.harness_agent.model_providers import _unseal, seal_key
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix + "/agent-admin/dingtalk-bots")

CONFIG_KEY = "dingtalk_receipt_bot"
TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"


class BotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    app_secret: str = Field(default="", max_length=256)  # 留空表示不改


def _require_admin(identity: dict) -> None:
    from app.core.permissions import _require_actual_system_admin
    try:
        _require_actual_system_admin(identity)
    except HTTPException as exc:
        raise HTTPException(403, "钉钉机器人配置只有系统管理员可以查看和修改") from exc


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


async def _load(db: AsyncSession, *, lock: bool = False):
    from app.models import SystemConfig

    statement = select(SystemConfig).where(SystemConfig.key == CONFIG_KEY)
    record = await db.scalar(statement.with_for_update() if lock else statement)
    raw = record.value if record is not None else None
    return record, (dict(raw) if isinstance(raw, dict) else {})


async def _save(db: AsyncSession, record, value: dict) -> None:
    from app.models import SystemConfig

    if record is None:
        record = SystemConfig(key=CONFIG_KEY, label="钉钉收文助手", group="智能体",
                              description="智能体中心 › 钉钉机器人中心；AppSecret 加密保存、不回显", value={})
    record.value = value
    record.updated_by = value.get("updated_by", "")
    db.add(record)
    await db.commit()


def _public(value: dict) -> dict:
    return {"app_key": value.get("app_key", ""), "secret_set": bool(value.get("encrypted_secret")),
            "updated_by": value.get("updated_by", ""), "updated_at": value.get("updated_at", ""),
            "verified_at": value.get("verified_at", ""), "verify_ok": value.get("verify_ok"),
            "verify_message": value.get("verify_message", "")}


async def probe(app_key: str, app_secret: str, transport=None) -> tuple[bool, str]:
    """向钉钉换一次访问令牌，验证 AppKey 和 AppSecret 是否匹配；令牌用完即弃，钉钉的返回内容不外传。"""
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, transport=transport) as client:
            response = await client.post(TOKEN_URL, json={"appKey": app_key, "appSecret": app_secret})
    except httpx.HTTPError as exc:
        return False, "连接钉钉失败：" + type(exc).__name__
    try:
        token = response.json().get("accessToken") if response.status_code == 200 else ""
    except ValueError:
        token = ""
    if token:
        return True, "连接正常：AppKey 和 AppSecret 有效"
    return False, f"钉钉拒绝（HTTP {response.status_code}），请核对 AppKey 和 AppSecret"


@router.get("")
async def get_dingtalk_bot(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    _, value = await _load(db)
    return _public(value)


@router.put("")
async def update_dingtalk_bot(body: BotInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    record, value = await _load(db, lock=True)
    secret = body.app_secret.strip()
    changed = {**value, "app_key": body.app_key, "updated_by": identity["username"], "updated_at": _now()}
    if secret:
        changed["encrypted_secret"] = seal_key(secret)
    if secret or body.app_key != value.get("app_key"):
        changed.update({"verified_at": "", "verify_ok": None, "verify_message": ""})
    await _save(db, record, changed)
    return _public(changed)


@router.post("/test")
async def test_dingtalk_bot(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    _, value = await _load(db)
    if not (value.get("app_key") and value.get("encrypted_secret")):
        raise HTTPException(422, "请先填写 AppKey 和 AppSecret")
    ok, message = await probe(value["app_key"], _unseal(value["encrypted_secret"]))
    record, value = await _load(db, lock=True)
    await _save(db, record, {**value, "verified_at": _now(), "verify_ok": ok, "verify_message": message})
    return {"ok": ok, "message": message}

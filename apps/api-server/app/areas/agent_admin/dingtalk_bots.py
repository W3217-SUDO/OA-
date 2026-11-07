"""智能体中心 › 钉钉机器人中心：填写收文助手机器人的 AppKey、AppSecret，测试连接。

只有系统管理员能看能改；AppSecret 加密保存，任何接口都不回显。写法和“云端智能体”配置一致。
"""
from __future__ import annotations

from dataclasses import dataclass
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
MAX_SEEN_GROUPS = 10


class BotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    app_secret: str = Field(default="", max_length=256)  # 留空表示不改
    enabled: bool = False
    group_id: str = Field(default="", max_length=128)  # 收文群的 openConversationId；只认 ID，群名只作显示
    use_cloud_agent: bool = False  # 云端智能体读短信：文书内容会发到模型服务，要陶威拍板后再开
    auto_save_unique: bool = False  # 服务器判断唯一匹配时直接入库：跳过律师确认，要陶威拍板后再开


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
            "enabled": bool(value.get("enabled")), "group_id": value.get("group_id") or "", "group_title": value.get("group_title") or "",
            "seen_groups": value.get("seen_groups") or [],
            "use_cloud_agent": bool(value.get("use_cloud_agent")), "auto_save_unique": bool(value.get("auto_save_unique")),
            "updated_by": value.get("updated_by", ""), "updated_at": value.get("updated_at", ""),
            "verified_at": value.get("verified_at", ""), "verify_ok": value.get("verify_ok"),
            "verify_message": value.get("verify_message", "")}


@dataclass(frozen=True)
class BotConfig:
    enabled: bool
    app_key: str
    app_secret: str
    group_id: str
    use_cloud_agent: bool
    auto_save_unique: bool

    @property
    def ready(self) -> bool:
        """没选群也算就绪：要连上钉钉，有人在群里 @ 一次，页面才列得出群；没选群时任何消息都不处理。"""
        return self.enabled and bool(self.app_key and self.app_secret)


async def load_bot(db: AsyncSession) -> BotConfig:
    """给常驻程序用；解密失败视为未就绪，不抛错。"""
    _, value = await _load(db)
    try:
        secret = _unseal(value["encrypted_secret"]) if value.get("encrypted_secret") else ""
    except HTTPException:
        secret = ""
    return BotConfig(enabled=bool(value.get("enabled")), app_key=str(value.get("app_key") or ""), app_secret=secret,
                     group_id=str(value.get("group_id") or "").strip(),
                     use_cloud_agent=bool(value.get("use_cloud_agent")), auto_save_unique=bool(value.get("auto_save_unique")))


async def note_seen_group(db: AsyncSession, group_id: str, title: str) -> None:
    """记下 @ 过机器人的群（只存 ID 和群名），给管理员在页面上选收文群。"""
    if not group_id:
        return
    _, value = await _load(db)
    seen = value.get("seen_groups") or []
    if any(item.get("id") == group_id and item.get("title") == title for item in seen):
        return
    record, value = await _load(db, lock=True)
    if record is None:
        return
    others = [item for item in value.get("seen_groups") or [] if item.get("id") != group_id]
    await _save(db, record, {**value, "seen_groups": [{"id": group_id, "title": title[:100], "seen_at": _now()}, *others][:MAX_SEEN_GROUPS]})


async def probe(app_key: str, app_secret: str, transport=None) -> tuple[bool, str]:
    """向钉钉换一次访问令牌，验证 AppKey 和 AppSecret 是否匹配；令牌用完即弃，钉钉的返回内容不外传。"""
    try:
        async with httpx.AsyncClient(timeout=15, transport=transport) as client:
            response = await client.post(TOKEN_URL, json={"appKey": app_key, "appSecret": app_secret})
    except httpx.HTTPError as exc:
        return False, "连接钉钉失败：" + type(exc).__name__
    try:
        payload = response.json() if response.status_code == 200 else {}
    except ValueError:
        payload = {}
    if isinstance(payload, dict) and payload.get("accessToken"):
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
    changed = {**value, "app_key": body.app_key, "enabled": body.enabled, "group_id": body.group_id.strip(),
               "group_title": next((item["title"] for item in value.get("seen_groups") or [] if item.get("id") == body.group_id.strip()),
                                   value.get("group_title") if body.group_id.strip() == value.get("group_id") else ""),
               "use_cloud_agent": body.use_cloud_agent, "auto_save_unique": body.auto_save_unique,
               "updated_by": identity["username"], "updated_at": _now()}
    if body.enabled and not (secret or value.get("encrypted_secret")):
        raise HTTPException(422, "启用前请先填写 AppSecret")
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
    try:
        secret = _unseal(value["encrypted_secret"])
    except HTTPException as exc:
        raise HTTPException(409, "AppSecret 解密失败，请重新填写") from exc
    ok, message = await probe(value["app_key"], secret)
    record, value = await _load(db, lock=True)
    await _save(db, record, {**value, "verified_at": _now(), "verify_ok": ok, "verify_message": message})
    return {"ok": ok, "message": message}

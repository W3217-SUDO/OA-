"""智能体设置 › 云端智能体：启用火山方舟 Managed Agents、填方舟 API Key、选模型、测试连接（陶威 11-03）。

只有系统管理员能看能改；API Key 加密保存，任何接口都不回显。
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud_agent.config import CONFIG_KEY, MODELS, load, resolve
from app.config import settings
from app.database import get_db
from app.harness_agent.model_providers import seal_key
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix + "/agent-admin/cloud-runtime")


class CloudInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    model: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    memory: bool = True
    api_key: str = Field(default="", max_length=500)  # 留空表示不改
    plan_key: str = Field(default="", max_length=500)  # Agent Plan 专属 Key，留空表示不改
    datapro: bool = True
    doubao_search: bool = True


def _require_admin(identity: dict) -> None:
    from app.core.permissions import _require_actual_system_admin
    try:
        _require_actual_system_admin(identity)
    except HTTPException as exc:
        raise HTTPException(403, "云端智能体配置只有系统管理员可以查看和修改") from exc


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _public(value: dict) -> dict:
    return {"enabled": bool(value.get("enabled")), "model": value.get("model", ""), "memory": bool(value.get("memory", True)),
            "key_set": bool(value.get("encrypted_key")), "models": MODELS,
            "plan_key_set": bool(value.get("encrypted_plan_key")), "datapro": bool(value.get("datapro", True)),
            "doubao_search": bool(value.get("doubao_search", True)), "revision": value.get("revision", 0),
            "updated_by": value.get("updated_by", ""), "updated_at": value.get("updated_at", ""),
            "verified_at": value.get("verified_at", ""), "verify_ok": value.get("verify_ok"),
            "verify_message": value.get("verify_message", "")}


async def _save(db: AsyncSession, record, value: dict) -> None:
    from app.models import SystemConfig

    if record is None:
        record = SystemConfig(key=CONFIG_KEY, label="云端智能体", group="智能体",
                              description="智能体设置 › 云端智能体（火山方舟 Managed Agents）；API Key 加密保存、不回显", value={})
    record.value = value
    record.updated_by = value.get("updated_by", "")
    db.add(record)
    await db.commit()


@router.get("")
async def get_cloud_runtime(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    _, value = await load(db)
    return _public(value)


@router.put("")
async def update_cloud_runtime(body: CloudInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    record, value = await load(db, lock=True)
    changed = {**value, "enabled": body.enabled, "model": body.model.strip(), "memory": body.memory,
               "datapro": body.datapro, "doubao_search": body.doubao_search,
               "updated_by": identity["username"], "updated_at": _now(), "revision": int(value.get("revision") or 0) + 1}
    if body.api_key.strip():
        changed.update({"encrypted_key": seal_key(body.api_key.strip()), "verified_at": "", "verify_ok": None, "verify_message": ""})
    if body.plan_key.strip():
        changed["encrypted_plan_key"] = seal_key(body.plan_key.strip())
    if body.model.strip() != value.get("model"):
        changed.update({"verified_at": "", "verify_ok": None, "verify_message": ""})
    if changed["enabled"] and not (changed.get("encrypted_key") and changed["model"]):
        raise HTTPException(422, "启用云端智能体前请先填写方舟 API Key 和模型")
    await _save(db, record, changed)
    return _public(changed)


async def probe(api_key: str, model: str, transport=None) -> tuple[bool, str]:
    """用 Key 建一个临时 Agent 再删掉：同时验证 Key、Managed Agents 是否开通和模型是否开通；不调用模型，不产生模型费用。"""
    from app.cloud_agent.client import ArkClient, ArkError
    from app.cloud_agent.runtime import agent_body

    try:
        async with ArkClient(api_key, transport=transport) as client:
            created = await client.request("POST", "/agents", json_body={"name": "huzhi-oa-probe", **agent_body(model, [])})
            await client.request("DELETE", "/agents/" + created["id"])
    except ArkError as exc:
        hint = {"ManagedAgentNotOpen": "账号还没开通 Managed Agents"}.get(exc.code, "")
        if not hint and "not open" in exc.message:
            hint = "模型还没在方舟“开通管理”里开通"
        elif not hint and exc.status == 401:
            hint = "API Key 无效"
        return False, "，".join(part for part in (f"HTTP {exc.status}", hint, exc.code) if part)
    except Exception as exc:  # 网络错误等
        return False, "连接失败：" + type(exc).__name__
    return True, "连接正常：Managed Agents 已开通，模型可用"


@router.post("/test")
async def test_cloud_runtime(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    _, value = await load(db)
    current = resolve(value)
    if not (current.api_key and current.model):
        raise HTTPException(422, "请先填写方舟 API Key 和模型")
    ok, message = await probe(current.api_key, current.model)
    record, value = await load(db, lock=True)
    if record is not None:
        await _save(db, record, {**value, "verified_at": _now(), "verify_ok": ok, "verify_message": message})
    return {"ok": ok, "message": message}

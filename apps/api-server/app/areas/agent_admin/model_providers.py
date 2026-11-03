"""智能体设置 › DSH API 配置：模型服务商的增删改、切换当前使用和测试连接（陶威 11-03）。

只有系统管理员能看能改；API Key 加密保存，任何接口都不回显。删除只做逻辑删除。
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.harness_agent.model_providers import (
    CONFIG_KEY, PROVIDER_TYPES, SERVER_ID, load, provider_by_id, resolve_provider, seal_key,
)
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix + "/agent-admin/model-providers")
ProviderType = Literal["deepseek", "qwen", "zhipu", "moonshot", "ark", "anthropic", "openai_compatible"]


class ProviderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=60)
    type: ProviderType
    base_url: str = Field(min_length=1, max_length=300)
    model: str = Field(min_length=1, max_length=120)
    api_key: str = Field(default="", max_length=500)  # 编辑时留空表示不改


class ActiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)


def _require_admin(identity: dict) -> None:
    from app.core.permissions import _require_actual_system_admin
    try:
        _require_actual_system_admin(identity)
    except HTTPException as exc:
        raise HTTPException(403, "DSH API 配置只有系统管理员可以查看和修改") from exc


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _check_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise HTTPException(422, "接口地址必须是 https:// 开头的完整地址")
    return url


def _public(value: dict) -> dict:
    """页面用的视图：不含 Key 原文和密文。"""
    items = []
    for item in value["providers"]:
        if item.get("deleted_at"):
            continue
        server_key = item.get("key_source") == "server" and not item.get("encrypted_key")
        items.append({
            "id": item["id"], "name": item.get("name", ""), "type": item.get("type", "openai_compatible"),
            "base_url": item.get("base_url", ""), "model": item.get("model", ""),
            "key_set": bool(item.get("encrypted_key")) or (server_key and bool(settings.langgraph_api_key.strip())),
            "key_source": "server" if server_key else "page",
            "updated_by": item.get("updated_by", ""), "updated_at": item.get("updated_at", ""),
            "verified_at": item.get("verified_at", ""), "verify_message": item.get("verify_message", ""),
            "verify_ok": item.get("verify_ok"),
        })
    return {"active_id": value.get("active_id", SERVER_ID), "providers": items, "revision": value.get("revision", 0),
            "types": [{"value": code, **item} for code, item in PROVIDER_TYPES.items()]}


async def _save(db: AsyncSession, record, value: dict, username: str) -> dict:
    from app.models import SystemConfig

    value = {**value, "revision": int(value.get("revision") or 0) + 1}
    if record is None:
        record = SystemConfig(key=CONFIG_KEY, label="DSH 模型服务商", group="智能体",
                              description="智能体设置 › DSH API 配置；API Key 加密保存、不回显", value={})
    record.value = value
    record.updated_by = username
    db.add(record)
    await db.commit()
    return _public(value)


@router.get("")
async def list_providers(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    _, value = await load(db)
    return _public(value)


@router.post("")
async def create_provider(body: ProviderInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    if not body.api_key.strip():
        raise HTTPException(422, "新增服务商请填写 API Key")
    record, value = await load(db, lock=True)
    item = {"id": "p-" + uuid4().hex[:12], "name": body.name.strip(), "type": body.type, "base_url": _check_base_url(body.base_url),
            "model": body.model.strip(), "key_source": "page", "encrypted_key": seal_key(body.api_key.strip()),
            "updated_by": identity["username"], "updated_at": _now()}
    return await _save(db, record, {**value, "providers": [*value["providers"], item]}, identity["username"])


@router.put("/{provider_id}")
async def update_provider(provider_id: str, body: ProviderInput, identity: dict = Depends(current_identity),
                          db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    record, value = await load(db, lock=True)
    current = provider_by_id(value, provider_id)
    changed = {**current, "name": body.name.strip(), "type": body.type, "base_url": _check_base_url(body.base_url),
               "model": body.model.strip(), "updated_by": identity["username"], "updated_at": _now(),
               "verified_at": "", "verify_message": "", "verify_ok": None}
    if body.api_key.strip():
        changed.update({"key_source": "page", "encrypted_key": seal_key(body.api_key.strip())})
    providers = [changed if item["id"] == provider_id else item for item in value["providers"]]
    return await _save(db, record, {**value, "providers": providers}, identity["username"])


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    record, value = await load(db, lock=True)
    provider_by_id(value, provider_id)
    if value.get("active_id") == provider_id:
        raise HTTPException(409, "当前使用的服务商不能删除，请先切换到其他服务商")
    # 逻辑删除：保留记录，只标记删除时间和操作人。
    providers = [{**item, "deleted_at": _now(), "deleted_by": identity["username"]} if item["id"] == provider_id else item
                 for item in value["providers"]]
    return await _save(db, record, {**value, "providers": providers}, identity["username"])


@router.post("/activate")
async def set_active(body: ActiveInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    record, value = await load(db, lock=True)
    if not resolve_provider(value, body.id).configured:
        raise HTTPException(422, "这个服务商的接口地址、模型或 API Key 没填完整，不能设为当前使用")
    return await _save(db, record, {**value, "active_id": body.id}, identity["username"])


async def _probe(api: str, base_url: str, model: str, api_key: str) -> tuple[bool, str]:
    """发一次最短的对话请求（max_tokens=1）验证地址、Key 和模型；只返回是否可用，不返回模型内容。"""
    if api == "anthropic-messages":
        url = base_url + ("/messages" if base_url.endswith("/v1") else "/v1/messages")
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    else:
        url = base_url + "/chat/completions"
        headers = {"Authorization": "Bearer " + api_key}
    body = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        return False, "连接失败：" + type(exc).__name__
    elapsed = int((time.perf_counter() - started) * 1000)
    if response.status_code < 300:
        return True, f"连接正常，用时 {elapsed} 毫秒"
    hint = {401: "API Key 无效", 403: "没有权限或余额不足", 404: "接口地址或模型名不对", 429: "请求太频繁或额度用完"}.get(response.status_code, "")
    try:
        detail = response.json()
        detail = detail.get("error", detail) if isinstance(detail, dict) else detail
        detail = detail.get("message", "") if isinstance(detail, dict) else str(detail)
    except ValueError:
        detail = ""
    return False, "，".join(part for part in (f"HTTP {response.status_code}", hint, str(detail)[:200]) if part)


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_admin(identity)
    _, value = await load(db)
    active = resolve_provider(value, provider_id)
    if not active.configured:
        raise HTTPException(422, "接口地址、模型或 API Key 没填完整")
    ok, message = await _probe(active.api, active.base_url, active.model, active.api_key)
    record, value = await load(db, lock=True)
    if record is not None:
        providers = [{**item, "verified_at": _now(), "verify_message": message, "verify_ok": ok} if item["id"] == provider_id else item
                     for item in value["providers"]]
        record.value = {**value, "providers": providers}
        db.add(record)
        await db.commit()
    return {"ok": ok, "message": message}

"""DSH 模型服务商（陶威 11-03：智能体设置里配置 DSH API，可以切换服务商）。

服务商列表和“当前使用”存在系统配置 agent_model_providers 里，API Key 加密保存、不回显。
每次智能体请求都按当前使用的服务商取接口地址、模型和 Key，切换后新的请求马上生效，不用重启。
还没在页面保存过时，用服务器私有配置（LANGGRAPH_*）作为第一个服务商“服务器配置”，Key 仍取服务器配置，上线不断。
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

CONFIG_KEY = "agent_model_providers"
SERVER_ID = "server"
# 类型 → DSH（pi-ai）的接口协议和默认值。接口地址、模型、Key 都由管理员自己填、自己改，这里只是预填；
# models 是下拉里的常用模型，也可以手填任意模型 ID。DSH 支持 OpenAI 兼容（openai-completions）和 Anthropic 格式。
PROVIDER_TYPES = {
    "ark": {"label": "火山方舟（Ark）", "api": "openai-completions", "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3",
            "model": "ark-code-latest",
            "models": ["ark-code-latest", "doubao-seed-1-6-250615", "doubao-seed-1-6-thinking-250715", "deepseek-v3-1-250821", "kimi-k2-250905"]},
    "deepseek": {"label": "DeepSeek", "api": "openai-completions", "base_url": "https://api.deepseek.com", "model": "deepseek-chat",
                 "models": ["deepseek-chat", "deepseek-reasoner", "deepseek-flash"]},
    "qwen": {"label": "通义千问（阿里云百炼）", "api": "openai-completions",
             "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "models": ["qwen-plus", "qwen-max", "qwen-turbo"]},
    "zhipu": {"label": "智谱 GLM", "api": "openai-completions", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4.5",
              "models": ["glm-4.5", "glm-4.5-air"]},
    "moonshot": {"label": "Moonshot（Kimi）", "api": "openai-completions", "base_url": "https://api.moonshot.cn/v1",
                 "model": "kimi-k2-0905-preview", "models": ["kimi-k2-0905-preview", "moonshot-v1-32k"]},
    "anthropic": {"label": "Anthropic（Claude）", "api": "anthropic-messages", "base_url": "https://api.anthropic.com",
                  "model": "claude-sonnet-5-5", "models": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"]},
    "openai_compatible": {"label": "其他 OpenAI 兼容接口", "api": "openai-completions", "base_url": "", "model": "", "models": []},
}


@dataclass(frozen=True)
class ActiveModel:
    id: str
    name: str
    type: str
    api: str
    base_url: str
    model: str
    api_key: str

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model and self.api_key)

    def fingerprint(self) -> str:
        """常驻会话按它判断要不要重建：切换服务商、改地址/模型/Key 后都重建。"""
        material = json.dumps([self.id, self.api, self.base_url, self.model, hashlib.sha256(self.api_key.encode()).hexdigest()])
        return hashlib.sha256(material.encode()).hexdigest()


def _cipher() -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"oa.agent.model-provider.v1").derive(settings.secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def seal_key(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def _unseal(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise HTTPException(409, "模型服务商的 API Key 解密失败，请系统管理员重新填写") from exc


def guess_type(base_url: str) -> str:
    host = (urlsplit(base_url).hostname or "").lower()
    for code, item in PROVIDER_TYPES.items():
        default_host = urlsplit(item["base_url"]).hostname
        if default_host and host == default_host:
            return code
    if host.startswith("ark.") and host.endswith(".volces.com"):
        return "ark"
    return "openai_compatible"


def server_provider() -> dict:
    """服务器私有配置，作为第一个服务商；Key 留在服务器配置里，不写进数据库。"""
    kind = guess_type(settings.langgraph_api_base_url)
    return {"id": SERVER_ID, "name": "服务器配置（" + PROVIDER_TYPES[kind]["label"] + "）", "type": kind,
            "base_url": settings.langgraph_api_base_url.strip(), "model": settings.langgraph_model.strip(),
            "key_source": "server", "encrypted_key": ""}


async def load(db: AsyncSession, *, lock: bool = False):
    """返回 (记录, 配置)。没有记录时返回只含服务器配置的默认值（不写库）。"""
    from app.models import SystemConfig

    statement = select(SystemConfig).where(SystemConfig.key == CONFIG_KEY)
    record = await db.scalar(statement.with_for_update() if lock else statement)
    value = dict(record.value or {}) if record else {}
    if not value.get("providers"):
        value = {"active_id": SERVER_ID, "providers": [server_provider()], "revision": 0}
    return record, value


def _resolve(item: dict) -> ActiveModel:
    kind = item.get("type") if item.get("type") in PROVIDER_TYPES else "openai_compatible"
    if item.get("key_source") == "server" and not item.get("encrypted_key"):
        api_key = settings.langgraph_api_key.strip()
    else:
        api_key = _unseal(item["encrypted_key"]) if item.get("encrypted_key") else ""
    return ActiveModel(id=item["id"], name=item.get("name") or item["id"], type=kind, api=PROVIDER_TYPES[kind]["api"],
                       base_url=str(item.get("base_url") or "").strip().rstrip("/"), model=str(item.get("model") or "").strip(),
                       api_key=api_key)


def provider_by_id(value: dict, provider_id: str) -> dict:
    item = next((item for item in value["providers"] if item["id"] == provider_id and not item.get("deleted_at")), None)
    if item is None:
        raise HTTPException(404, "模型服务商不存在或已删除")
    return item


def resolve_provider(value: dict, provider_id: str) -> ActiveModel:
    return _resolve(provider_by_id(value, provider_id))


def active_from_settings() -> ActiveModel:
    return _resolve(server_provider())


async def active_model(db: AsyncSession | None) -> ActiveModel:
    if db is None:  # 没有数据库会话的调用（如运行库自检）按服务器配置
        return active_from_settings()
    _, value = await load(db)
    item = next((item for item in value["providers"] if item["id"] == value.get("active_id") and not item.get("deleted_at")), None)
    return _resolve(item or server_provider())


def supports_response_modes(model: ActiveModel) -> bool:
    # 仅向已经确认支持 thinking 的官方模型传参，不影响其他 OpenAI 兼容服务。
    host = urlsplit(model.base_url).hostname or ""
    ark = host.startswith("ark.") and host.endswith(".volces.com") and model.model == "ark-code-latest"
    deepseek = host == "api.deepseek.com" and model.model == "deepseek-flash"
    return ark or deepseek

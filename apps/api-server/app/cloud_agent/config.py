"""云端智能体配置：是否启用、方舟 API Key、模型。存在系统配置 agent_cloud_runtime 里，Key 加密保存、不回显。

启用后个人助手和案件智能体都走火山 Managed Agents；关闭时仍走服务器上的 DSH。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.harness_agent.model_providers import _unseal

CONFIG_KEY = "agent_cloud_runtime"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "deepseek-v4-1-flash-261017"
# 控制台“创建 Agent”里能选的常用模型（模型 ID 带版本号，需先在方舟“开通管理”里开通）。
MODELS = ["deepseek-v4-1-flash-261017", "doubao-seed-2-1-pro-260915", "deepseek-v4-pro-ga-260813",
          "deepseek-v4-flash-ga-260731", "doubao-seed-2-1-lite-260915"]


@dataclass(frozen=True)
class CloudSettings:
    enabled: bool
    api_key: str
    model: str
    memory: bool

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.api_key and self.model)

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps([self.model, hashlib.sha256(self.api_key.encode()).hexdigest()]).encode()).hexdigest()


async def load(db: AsyncSession, *, lock: bool = False):
    """返回 (记录, 配置)。没有记录时返回未启用的默认值（不写库）。"""
    from app.models import SystemConfig

    statement = select(SystemConfig).where(SystemConfig.key == CONFIG_KEY)
    record = await db.scalar(statement.with_for_update() if lock else statement)
    raw = record.value if record is not None else None
    value = dict(raw) if isinstance(raw, dict) else {}
    value.setdefault("enabled", False)
    value.setdefault("model", DEFAULT_MODEL)
    value.setdefault("memory", True)
    value.setdefault("encrypted_key", "")
    value.setdefault("revision", 0)
    return record, value


def resolve(value: dict) -> CloudSettings:
    api_key = _unseal(value["encrypted_key"]) if value.get("encrypted_key") else ""
    return CloudSettings(enabled=bool(value.get("enabled")), api_key=api_key,
                         model=str(value.get("model") or "").strip(), memory=bool(value.get("memory", True)))


async def active(db) -> CloudSettings | None:
    """启用且配置完整时返回配置；否则 None（继续走 DSH）。没有数据库会话时视为未启用。"""
    if db is None:
        return None
    _, value = await load(db)
    if not value.get("enabled"):
        return None
    settings = resolve(value)
    return settings if settings.ready else None

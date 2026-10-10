"""工具参数、内部状态记录和敏感返回值的边界。"""

import re
from urllib.parse import quote

from fastapi import HTTPException

from app.config import settings
from app.core.constants import RECORD_MODULE_MENU_ROOTS
from app.models import BusinessRecord


_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|passphrase|secret|credential|^authorization$|access[_-]?token|"
    r"refresh[_-]?token|api[_-]?key|private[_-]?key|signature|signed[_-]?url|"
    r"ossaccesskeyid|word_editor_lock_token|^token$|^pass$)", re.IGNORECASE,
)
_SIGNED_VALUE = re.compile(r"(?:[?&](?:Signature|OSSAccessKeyId|X-Amz-Signature|access_token)=|Bearer\s+)", re.IGNORECASE)
_JWT_VALUE = re.compile(r"\beyJ[\w-]+\.eyJ[\w-]+\.[\w-]+\b")


def reject_credentials(value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                raise HTTPException(422, "工具参数不能包含登录凭据、密码、密钥或签名地址，请使用原人工入口")
            if key in {"key", "config_key", "parameter_key"} and isinstance(item, str) and _SENSITIVE_KEY.search(item):
                raise HTTPException(422, "凭据配置必须通过原人工入口办理")
            reject_credentials(item)
    elif isinstance(value, list):
        for item in value:
            reject_credentials(item)
    elif isinstance(value, str) and (_SIGNED_VALUE.search(value) or _JWT_VALUE.search(value)):
        raise HTTPException(422, "工具参数不能包含登录凭据或签名地址")


def safe_result(value, bearer: str = ""):
    if isinstance(value, dict):
        credential_config = any(
            isinstance(value.get(key), str) and _SENSITIVE_KEY.search(value[key])
            for key in ("key", "config_key", "parameter_key")
        )
        return {key: safe_result(item, bearer) for key, item in value.items()
                if not _SENSITIVE_KEY.search(str(key))
                and not (credential_config and key in {"value", "content", "data", "default_value"})}
    if isinstance(value, list):
        return [safe_result(item, bearer) for item in value]
    if isinstance(value, str) and (_SIGNED_VALUE.search(value) or _JWT_VALUE.search(value) or (bearer and bearer in value)):
        return "敏感凭据已移除，请通过原 OA 人工入口查看"
    return value


def render_path(spec, params: dict) -> str:
    path = spec.path
    for name, value in params["path"].items():
        encoded = quote(str(value), safe="")
        if str(value) in {".", ".."}:
            raise HTTPException(422, "路径参数不能为相对目录")
        path = path.replace("{" + name + "}", encoded)
        path = re.sub(r"\{" + re.escape(name) + r":[^}]+\}", lambda _: encoded, path)
    if "{" in path or not path.startswith(settings.api_prefix + "/") or path.startswith("//"):
        raise HTTPException(422, "工具路径不属于已注册的 OA 接口")
    return path


async def require_business_record_target(spec, params: dict, db) -> None:
    relative = spec.path.removeprefix(settings.api_prefix)
    if relative != "/records" and not relative.startswith("/records/"):
        return
    # 通用记录不能读写智能体审批、会话和审计底座，更不能通过未知模块创建旁路。
    modules = []
    for source in (params["query"], params.get("body")):
        if isinstance(source, dict) and "module" in source:
            modules.append(source["module"])
    record_id = params["path"].get("record_id")
    if record_id is not None:
        record = await db.get(BusinessRecord, record_id)
        if record is None:
            raise HTTPException(404, "业务记录不存在")
        modules.append(record.module)
    if not modules:
        raise HTTPException(422, "通用记录工具必须明确有效业务模块")
    for module in modules:
        if not isinstance(module, str) or module not in RECORD_MODULE_MENU_ROOTS or module.startswith("agent"):
            raise HTTPException(403, "智能体不得通过通用记录访问内部状态或未知业务模块")

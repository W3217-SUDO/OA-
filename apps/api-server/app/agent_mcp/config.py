"""MCP 网关沿用 OA 环境文件的受信来源配置。"""

from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings

from app.config import Settings


class AgentMcpSettings(BaseSettings):
    agent_mcp_public_base_url: str = ""
    agent_mcp_allowed_origins: str = ""
    agent_mcp_export_root: str = ""
    agent_mcp_export_ttl_seconds: int = Field(default=900, gt=0)
    model_config = Settings.model_config


mcp_settings = AgentMcpSettings()


def trusted_origins() -> list[str]:
    configured = [
        mcp_settings.agent_mcp_public_base_url.strip().rstrip("/"),
        *(value.strip().rstrip("/") for value in mcp_settings.agent_mcp_allowed_origins.split(",")),
    ]
    origins = ["http://localhost", "http://localhost:*", "http://127.0.0.1", "http://127.0.0.1:*"]
    for origin in configured:
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
            or "*" in origin
        ):
            raise ValueError("MCP 受信来源必须为无路径、凭据和通配符的 OA HTTP(S) origin")
        origins.append(origin)
    return list(dict.fromkeys(origins))


def origin_allowed(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        return False
    for allowed in trusted_origins():
        if origin == allowed:
            return True
        if allowed.endswith(":*"):
            base = urlsplit(allowed[:-2])
            if (
                parsed.scheme == base.scheme and parsed.hostname == base.hostname
                and port is not None and not parsed.username and not parsed.password
                and not parsed.path and not parsed.query and not parsed.fragment
            ):
                return True
    return False


def oa_base_url() -> str:
    trusted_origins()
    return mcp_settings.agent_mcp_public_base_url.strip().rstrip("/") or "http://localhost"

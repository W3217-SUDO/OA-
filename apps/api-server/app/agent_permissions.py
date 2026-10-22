"""智能体全局管理的个人动作授权，不授予系统管理员或他人个人库权限。"""
from fastapi import HTTPException

AGENT_GLOBAL_MANAGE_ACTION = "agent.settings.global.manage"
# 允许用本人账号生成 MCP 个人访问令牌（只读），让自己电脑上的本地 agent 连接 OA；系统管理员默认拥有。
MCP_PERSONAL_TOKEN_ACTION = "agent.mcp.personal_token"
USER_ACTION_KEYS = frozenset({AGENT_GLOBAL_MANAGE_ACTION, MCP_PERSONAL_TOKEN_ACTION})


def personal_action_keys(overrides: dict) -> list[str]:
    keys = overrides.get("action_keys", [])
    if not isinstance(keys, list) or any(not isinstance(key, str) or key not in USER_ACTION_KEYS for key in keys):
        raise HTTPException(409, "用户个人动作授权无效，请由系统管理员核对")
    return list(dict.fromkeys(keys))


def is_actual_system_admin(identity: dict) -> bool:
    from app.core.permissions import _require_actual_system_admin
    try:
        _require_actual_system_admin(identity)
    except HTTPException as exc:
        if exc.status_code != 403:
            raise
        return False
    return True


def can_use_mcp_personal_token(identity: dict) -> bool:
    return is_actual_system_admin(identity) or MCP_PERSONAL_TOKEN_ACTION in identity.get("_user_action_keys", [])


def can_manage_agent_settings(identity: dict) -> bool:
    return is_actual_system_admin(identity) or AGENT_GLOBAL_MANAGE_ACTION in identity.get("_user_action_keys", [])


def require_agent_settings_management(identity: dict) -> None:
    if not can_manage_agent_settings(identity):
        raise HTTPException(403, "当前账号没有全所智能体技能和连接器管理权限")

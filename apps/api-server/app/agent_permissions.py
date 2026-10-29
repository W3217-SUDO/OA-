"""智能体全局管理的个人动作授权，不授予系统管理员或他人个人库权限。"""
import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)

AGENT_GLOBAL_MANAGE_ACTION = "agent.settings.global.manage"
# 允许用本人账号生成 MCP 个人访问令牌（只读），让自己电脑上的本地 agent 连接 OA；系统管理员默认拥有。
MCP_PERSONAL_TOKEN_ACTION = "agent.mcp.personal_token"
# 允许生成“读写”令牌：本地 agent 可新增/修改/删除，确认由本地 agent 负责；系统管理员默认拥有。
MCP_PERSONAL_TOKEN_WRITE_ACTION = "agent.mcp.personal_token.write"
# 财务回款/付款/费用的编辑、删除也可以在员工管理里按人勾选（用户 2026-10-28 要求）。
FINANCE_USER_ACTION_KEYS = frozenset({
    "finance.receipt.update", "finance.receipt.delete", "finance.payment.update",
    "finance.payment.delete", "finance.fee.update", "finance.fee.delete",
    # BUG20261028012：回款领取、待分配回款、已分配回款页面各自的删除。
    "finance.receipt.claim.delete", "finance.receipt.pending.delete", "finance.receipt.allocated.delete",
})
# 可以在员工管理里给别人勾选上面 6 个财务动作（只这 6 项，不含其他权限；用户 2026-10-28 要求给范明明）。
FINANCE_CONFIGURE_ACTION = "finance.actions.configure"
USER_ACTION_KEYS = frozenset({AGENT_GLOBAL_MANAGE_ACTION, MCP_PERSONAL_TOKEN_ACTION, MCP_PERSONAL_TOKEN_WRITE_ACTION,
                              FINANCE_CONFIGURE_ACTION, *FINANCE_USER_ACTION_KEYS})


def personal_action_keys(overrides: dict) -> list[str]:
    # 读权限时不认识的个人动作只忽略并记日志，不再整号 409：数据比代码先写入（如 2026-10-29 shenhe 登录不了）时账号仍能用。
    # 保存时仍由 update_user_permission_overrides 严格校验。
    keys = overrides.get("action_keys", [])
    if not isinstance(keys, list):
        logger.warning("个人动作授权结构无效，已忽略：%r", keys)
        return []
    unknown = [key for key in keys if not isinstance(key, str) or key not in USER_ACTION_KEYS]
    if unknown:
        logger.warning("忽略不认识的个人动作授权：%s", unknown)
    return list(dict.fromkeys(key for key in keys if isinstance(key, str) and key in USER_ACTION_KEYS))


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


def can_write_with_mcp_token(identity: dict) -> bool:
    return is_actual_system_admin(identity) or MCP_PERSONAL_TOKEN_WRITE_ACTION in identity.get("_user_action_keys", [])


def can_manage_agent_settings(identity: dict) -> bool:
    return is_actual_system_admin(identity) or AGENT_GLOBAL_MANAGE_ACTION in identity.get("_user_action_keys", [])


def require_agent_settings_management(identity: dict) -> None:
    if not can_manage_agent_settings(identity):
        raise HTTPException(403, "当前账号没有全所智能体技能和连接器管理权限")

"""用户权限覆盖变更与审计，调用方负责鉴权及事务提交。"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_permissions import FINANCE_USER_ACTION_KEYS, USER_ACTION_KEYS
from app.api_schemas.identity import UserPermissionOverrideUpdate
from app.core.constants import FIELD_KEYS, MENU_KEYS, ROLE_DATA_SCOPES, SYSTEM_MENU_ROUTE_KEYS
from app.models import SystemMenu, User


async def update_user_permission_overrides(
    user_id: int,
    body: UserPermissionOverrideUpdate,
    db: AsyncSession,
    *,
    actor: str,
    authorization_source: str,
) -> User:
    """仅供已鉴权入口调用；维护调用必须传入实际操作者及明确授权来源。"""
    from app.core.permissions import _system_user_role_ids, _user_permission_overrides
    from app.core.system import _system_audit

    if not actor.strip() or not authorization_source.strip():
        raise ValueError("权限变更必须记录实际操作者和授权来源")
    if body.clear_menu_keys and (body.clear or body.menu_keys is not None):
        raise HTTPException(422, "恢复岗位菜单授权不能同时清除全部授权或设置用户菜单")
    user = await db.scalar(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    )
    if user is None:
        raise HTTPException(404, "用户不存在")
    if "admin" in _system_user_role_ids(user):
        raise HTTPException(422, "系统管理员保持完整权限，不能设置用户级权限覆盖")
    previous_overrides = dict(_user_permission_overrides(user))
    if body.action_keys is not None:
        invalid_actions = sorted(set(body.action_keys) - USER_ACTION_KEYS)
        if invalid_actions:
            raise HTTPException(422, f"无效个人动作权限：{', '.join(invalid_actions)}")
        if body.clear:
            raise HTTPException(422, "清除全部授权不能同时设置个人动作权限")
    if body.action_denies is not None:
        invalid_denies = sorted(set(body.action_denies) - FINANCE_USER_ACTION_KEYS)
        if invalid_denies:
            raise HTTPException(422, f"只能取消财务编辑、删除动作：{', '.join(invalid_denies)}")
        if body.clear:
            raise HTTPException(422, "清除全部授权不能同时设置个人动作权限")
    profile = dict(user.profile or {})
    if body.clear:
        profile.pop("permission_overrides", None)
    else:
        stored_overrides = profile.get("permission_overrides", {})
        if not isinstance(stored_overrides, dict):
            raise HTTPException(409, "用户权限覆盖结构无效，请由系统管理员核对")
        # 原样保留未指定的覆盖项和其他资料，动作更新不重新计算菜单或角色。
        overrides = dict(stored_overrides)
        if body.action_keys is not None:
            overrides["action_keys"] = list(dict.fromkeys(body.action_keys))
        if body.action_denies is not None:
            overrides["action_denies"] = list(dict.fromkeys(body.action_denies))
        if body.clear_menu_keys:
            overrides.pop("menu_keys", None)
        if body.menu_keys is not None:
            menu_keys = list(dict.fromkeys(body.menu_keys))
            legacy_keys = set((await db.scalars(select(SystemMenu.key).where(~SystemMenu.key.in_(SYSTEM_MENU_ROUTE_KEYS)))).all())
            # 控制台是所有账号的基础页面，页面授权编辑器保存时总会带上它，不算无效。
            invalid = sorted(set(menu_keys) - (set(MENU_KEYS) | legacy_keys | {"dashboard"}))
            if invalid:
                raise HTTPException(422, f"无效菜单权限：{', '.join(invalid)}")
            if "user-center" not in menu_keys:
                raise HTTPException(422, "用户中心为基础权限，不能移除")
            overrides["menu_keys"] = menu_keys
        if body.field_keys is not None:
            field_keys = list(dict.fromkeys(body.field_keys))
            invalid_fields = sorted(set(field_keys) - set(FIELD_KEYS))
            if invalid_fields:
                raise HTTPException(422, f"无效字段权限：{', '.join(invalid_fields)}")
            overrides["field_keys"] = field_keys
        if body.data_scope is not None:
            data_scope = body.data_scope.strip()
            if data_scope not in ROLE_DATA_SCOPES:
                raise HTTPException(422, "数据范围无效")
            overrides["data_scope"] = data_scope
        profile["permission_overrides"] = overrides
    user.profile = profile
    await _system_audit(db, {"username": actor}, "更新用户权限覆盖", f"用户:{user.username}", {
        "user_id": user.id,
        "authorization_source": authorization_source,
        "previous_overrides": previous_overrides,
        "overrides": _user_permission_overrides(user),
    })
    await db.flush()
    return user

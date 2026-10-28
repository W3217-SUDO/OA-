"""财务中心回款/付款/费用的编辑、删除授权（用户 2026-10-28 定）。

1. 页面能看到即拥有该页的操作：能打开回款管理就能编辑、删除回款；能打开付款管理（不含“我的请款单”）
   就能编辑、删除付款包；能打开费用查询就能编辑、删除费用。
2. 员工管理里可以按人勾选或取消：取消的优先于页面可见；角色配置里勾选的仍有效。
3. 真实管理者默认全部允许。只认账号真实可见的页面，不认 current_identity 的临时提升（它不区分是哪个页面）；
   能看哪些记录仍按数据范围。
"""
from app.agent_permissions import FINANCE_CONFIGURE_ACTION, FINANCE_USER_ACTION_KEYS
from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS
from app.core.dependencies import AsyncSession, BusinessRecord, HTTPException, User, select

FINANCE_ACTION_LABELS = {code: label for code, _menu, label in FINANCE_EDIT_DELETE_ACTIONS}
# 动作前缀 → 打开哪些页面（菜单键前缀）即拥有该动作；“我的…”个人页面只是申请入口，不算。
FINANCE_ACTION_PAGE_PREFIXES = {
    "finance.receipt.": ("finance-receipts",),
    "finance.payment.": ("finance-payment",),
    "finance.fee.": ("finance-fee-query",),
}
# 申请人对自己尚未审批通过的费用申请仍可修改、删除（这是申请流程本身，不是改财务数据）。
OWN_EDITABLE_FEE_STATUSES = frozenset({"草稿", "已退回", "已驳回"})


def page_granted_finance_actions(menu_keys) -> list[str]:
    """账号可见页面带来的财务动作。"""
    menus = [str(key) for key in menu_keys or [] if not str(key).endswith("-mine")]
    granted = []
    for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS:
        prefixes = next(pages for action, pages in FINANCE_ACTION_PAGE_PREFIXES.items() if code.startswith(action))
        if any(menu.startswith(prefix) for menu in menus for prefix in prefixes):
            granted.append(code)
    return granted


def granted_action_keys(permission: dict) -> list[str]:
    """角色勾选 + 员工管理按人勾选 + 可见页面带来的动作，去掉按人取消的；登录返回、/auth/me 和后端校验都用它。"""
    denied = set(permission.get("user_action_denies") or [])
    keys = [*(permission.get("action_keys") or []), *(permission.get("user_action_keys") or []),
            *page_granted_finance_actions(permission.get("menu_keys"))]
    return [key for key in dict.fromkeys(keys) if key not in denied]


async def configured_action_keys(username: str, db: AsyncSession) -> list[str]:
    from app.core.permissions import _system_user_role_ids, _user_permission_payload
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active:
        return []
    if "admin" in _system_user_role_ids(user):
        return ["*"]
    return granted_action_keys(await _user_permission_payload(user, db))


async def finance_action_granted(identity: dict, db: AsyncSession, code: str) -> bool:
    keys = set(await configured_action_keys(str(identity.get("username") or ""), db))
    return "*" in keys or code in keys


async def can_configure_finance_actions(identity: dict, db: AsyncSession) -> bool:
    """真实管理者，或被授权“给别人配置财务操作”的账号（如范明明）。"""
    from app.agent_permissions import is_actual_system_admin
    if is_actual_system_admin(identity):
        return True
    return FINANCE_CONFIGURE_ACTION in await configured_action_keys(str(identity.get("username") or ""), db)


async def user_finance_actions(user: User, db: AsyncSession) -> list[str]:
    keys = set(await configured_action_keys(user.username, db))
    return [code for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS if "*" in keys or code in keys]


async def set_user_finance_actions(user_id: int, checked: list[str], db: AsyncSession, *, actor: str, source: str) -> User:
    """按勾选结果保存某人的 6 个财务动作：勾上的记为按人授权，没勾的记为按人取消；其他个人授权不动。"""
    from app.api_schemas.identity import UserPermissionOverrideUpdate
    from app.core.permissions import _user_permission_overrides
    from app.core.user_permission_overrides import update_user_permission_overrides
    invalid = sorted(set(checked) - FINANCE_USER_ACTION_KEYS)
    if invalid:
        raise HTTPException(422, f"无效财务动作：{', '.join(invalid)}")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    others = [key for key in _user_permission_overrides(user).get("action_keys") or [] if key not in FINANCE_USER_ACTION_KEYS]
    granted = [code for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS if code in checked]
    denied = [code for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS if code not in checked]
    return await update_user_permission_overrides(
        user_id, UserPermissionOverrideUpdate(action_keys=[*others, *granted], action_denies=denied), db,
        actor=actor, authorization_source=source,
    )


async def require_finance_action(identity: dict, db: AsyncSession, code: str) -> None:
    if not await finance_action_granted(identity, db, code):
        label = FINANCE_ACTION_LABELS.get(code, "该操作")
        raise HTTPException(status_code=403, detail=f"当前账号没有“{label}”权限，请联系管理者在员工管理里开通")


def is_own_unapproved_fee(item: BusinessRecord, identity: dict) -> bool:
    data = item.data or {}
    username = str(identity.get("username") or "")
    return bool(username) and item.status in OWN_EDITABLE_FEE_STATUSES and username in {
        str(item.owner or ""), str(data.get("applicant") or ""), str(data.get("created_by") or ""),
    }


async def require_fee_action(item: BusinessRecord, identity: dict, db: AsyncSession, code: str) -> None:
    if not is_own_unapproved_fee(item, identity):
        await require_finance_action(identity, db, code)

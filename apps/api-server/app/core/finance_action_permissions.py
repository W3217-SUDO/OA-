"""财务中心回款/付款/费用的编辑、删除授权（用户 2026-10-28 定）。

1. 只有管理页面带出操作（陶威 2026-10-28 改）：能打开“回款管理”才能编辑、删除回款，能打开“付款打包-管理”
   才能编辑、删除付款包，能打开“请款单审批”才能编辑、删除费用。律师能看回款领取、到账查询、付款单查询、
   费用查询等页面，但这些页面不带编辑删除。
2. 角色权限里按角色取消（BUG20261028012，陶威 2026-10-28 17:09/17:15）：页面默认带全部功能（上线时所有角色一次性全勾），
   管理员在角色权限里取消的该角色就没有；角色勾选也只在能打开对应管理页面时生效。
   员工管理里按人勾选或取消优先于角色。
3. 真实管理者默认全部允许。只认账号真实可见的页面，不认 current_identity 的临时提升（它不区分是哪个页面）；
   能看哪些记录仍按数据范围。
"""
from app.agent_permissions import FINANCE_CONFIGURE_ACTION, FINANCE_USER_ACTION_KEYS
from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS
from app.core.dependencies import AsyncSession, BusinessRecord, HTTPException, User, select

FINANCE_ACTION_LABELS = {code: label for code, _menu, label in FINANCE_EDIT_DELETE_ACTIONS}
PLATFORM_RECEIPT_PAGES = {
    "platform-finance-overview-manage": "finance-receipts-manage", "platform-finance-overview-claim": "finance-receipts-claim",
    "platform-finance-overview-pending": "finance-receipts-pending", "platform-finance-overview-allocated": "finance-receipts-allocated",
}
# 回款领取、待分配回款、已分配回款各自的删除只管本页显示的回款（按状态）；回款管理的删除管全部。
RECEIPT_PAGE_DELETE_BY_STATUS = {
    "待认领": "finance.receipt.claim.delete", "待分配": "finance.receipt.pending.delete",
    "部分分配": "finance.receipt.pending.delete", "已分配": "finance.receipt.allocated.delete",
}
# 申请人对自己尚未审批通过的费用申请仍可修改、删除（这是申请流程本身，不是改财务数据）。
OWN_EDITABLE_FEE_STATUSES = frozenset({"草稿", "已退回", "已驳回"})


def page_granted_finance_actions(menu_keys) -> list[str]:
    """账号可见的管理页面带来的财务动作（页面即 FINANCE_EDIT_DELETE_ACTIONS 的第二列）。"""
    menus = {str(key) for key in menu_keys or []}
    # BUG20261028012：平台财务中心的回款管理/领取/待分配/已分配和财务中心同名页面带同一组开关。
    for platform, firm in PLATFORM_RECEIPT_PAGES.items():
        if platform in menus:
            menus.add(firm)
    return [code for code, menu, _label in FINANCE_EDIT_DELETE_ACTIONS if menu in menus]


def granted_action_keys(permission: dict) -> list[str]:
    """角色勾选（财务编辑删除须能打开对应管理页面）+ 员工管理按人勾选，去掉按人取消的；登录返回、/auth/me 和后端校验都用它。"""
    denied = set(permission.get("user_action_denies") or [])
    page_codes = set(page_granted_finance_actions(permission.get("menu_keys")))
    role_keys = [key for key in permission.get("action_keys") or [] if key not in FINANCE_ACTION_LABELS or key in page_codes]
    keys = [*role_keys, *(permission.get("user_action_keys") or [])]
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


async def require_receipt_delete(identity: dict, db: AsyncSession, status: str) -> None:
    """删除回款：有回款管理的删除，或有该回款所在页面（回款领取/待分配/已分配）的删除。"""
    page_code = RECEIPT_PAGE_DELETE_BY_STATUS.get(str(status or ""))
    if page_code and await finance_action_granted(identity, db, page_code):
        return
    await require_finance_action(identity, db, "finance.receipt.delete")


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

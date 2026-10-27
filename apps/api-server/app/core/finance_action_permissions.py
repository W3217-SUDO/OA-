"""财务中心回款/付款/费用的编辑、删除按角色配置的动作授权。

页面可见时身份会被临时提升为全部动作（见 security.current_identity），这里绕开提升，
只认账号真实角色、岗位和角色配置里勾选的动作；真实管理者角色默认全部允许。
"""
from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS
from app.core.dependencies import AsyncSession, BusinessRecord, HTTPException, User, select

FINANCE_ACTION_LABELS = {code: label for code, _menu, label in FINANCE_EDIT_DELETE_ACTIONS}
# 申请人对自己尚未审批通过的费用申请仍可修改、删除（这是申请流程本身，不是改财务数据）。
OWN_EDITABLE_FEE_STATUSES = frozenset({"草稿", "已退回", "已驳回"})


async def configured_action_keys(username: str, db: AsyncSession) -> list[str]:
    from app.core.permissions import _system_user_role_ids, _user_permission_payload
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active:
        return []
    if "admin" in _system_user_role_ids(user):
        return ["*"]
    return list((await _user_permission_payload(user, db)).get("action_keys") or [])


async def finance_action_granted(identity: dict, db: AsyncSession, code: str) -> bool:
    keys = set(await configured_action_keys(str(identity.get("username") or ""), db))
    return "*" in keys or code in keys


async def require_finance_action(identity: dict, db: AsyncSession, code: str) -> None:
    if not await finance_action_granted(identity, db, code):
        label = FINANCE_ACTION_LABELS.get(code, "该操作")
        raise HTTPException(status_code=403, detail=f"当前账号没有“{label}”权限，请联系管理者在角色配置中开通")


def is_own_unapproved_fee(item: BusinessRecord, identity: dict) -> bool:
    data = item.data or {}
    username = str(identity.get("username") or "")
    return bool(username) and item.status in OWN_EDITABLE_FEE_STATUSES and username in {
        str(item.owner or ""), str(data.get("applicant") or ""), str(data.get("created_by") or ""),
    }


async def require_fee_action(item: BusinessRecord, identity: dict, db: AsyncSession, code: str) -> None:
    if not is_own_unapproved_fee(item, identity):
        await require_finance_action(identity, db, code)

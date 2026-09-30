"""待处理开票的列表和动作使用同一真实角色与财务板块授权。"""
from fastapi import HTTPException
from sqlalchemy import select
from app.models import RolePermission, User
from app.security import user_role_ids


def invoice_finance_scope(invoice) -> str:
    data = invoice.data or {}
    return "platform" if (data.get("finance_scope") == "platform"
                          or data.get("accounting_center") == "平台财务中心"
                          or data.get("contract_body") == "平台") else "firm"


async def invoice_permissions(identity, db) -> dict:
    from app.core.permissions import (_configured_user_job_role_name, _job_role_for_name,
                                      _user_permission_overrides, _user_permission_payload, _user_has_job_permission)
    username = str(identity.get("username") or "")
    cached = identity.get("_invoice_permissions")
    if cached and cached.get("username") == username:
        return cached
    user = await db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if not user:
        raise HTTPException(401, "当前用户不存在或已停用")
    roles = set(user_role_ids(user))
    payload = await _user_permission_payload(user, db)
    menus = set(payload.get("menu_keys") or [])
    overrides = _user_permission_overrides(user)
    assigned_role = _configured_user_job_role_name(user)
    if "menu_keys" in overrides:
        explicit_menus = set(overrides["menu_keys"])
    elif assigned_role:
        job = await _job_role_for_name(assigned_role, db)
        explicit_menus = set(job.permissions or []) if job else set()
    else:
        configured = (await db.scalars(select(RolePermission).where(RolePermission.role.in_(roles)))).all()
        explicit_menus = {key for item in configured for key in (item.menu_keys or [])}
    job_grant = await _user_has_job_permission(user, "开票审批", db)
    result = {"username": username}
    for scope, prefix in (("firm", "finance"), ("platform", "platform-finance")):
        # 普通角色的默认财务根菜单不是审核授权，必须有实际配置的处理叶子或岗位动作。
        delegated = f"{prefix}-invoice-pending" in explicit_menus and f"{prefix}-invoice-pending" in menus
        # 岗位动作仍受其财务板块菜单范围约束。
        delegated = delegated or (job_grant and any(key == prefix or key.startswith(prefix + "-") for key in menus))
        result[scope] = {"review": bool(roles & {"admin", "manager", "auditor"}) or delegated,
                         "issue": bool(roles & {"admin", "manager"}) or delegated}
    identity["_invoice_permissions"] = result
    return result


async def require_invoice_action(invoice, action, identity, db):
    permission = await invoice_permissions(identity, db)
    if not permission[invoice_finance_scope(invoice)][action]:
        raise HTTPException(403, "当前账号没有该财务板块的开票处理权限")

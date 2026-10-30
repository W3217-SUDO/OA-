"""BUG20261030007 起页面只认人员角色：没设人员角色的账号只有公共页面，不再拿账号角色（普通用户等）的页面。

老测试按“账号角色给页面”搭的数据：这里给没设人员角色的非管理员账号挂一个同内容的测试人员角色
（页面、功能、字段、数据范围都照抄账号角色），测试原来要验证的业务规则不变。可重复调用，账号角色改了会跟着更新。
"""
from sqlalchemy import select

from app.core.constants import CASE_ACTIONS_EXPLICIT_MARKER, MENUS_EXACT_MARKER
from app.core.permissions import _configured_user_job_role_name, _permission_payload_for_roles, _system_user_role_ids
from app.data_models.identity import JobRole
from app.models import User

TEST_ROLE_PREFIX = "TEST-SYSROLE-"


async def bind_system_role_pages(sessions=None, db=None) -> None:
    """传 sessions 时开新会话；测试里已开着会话就传 db=db（写完提交并让会话重新读账号）。"""
    if db is not None:
        await _bind(db)
        for obj in list(db.identity_map.values()):
            if isinstance(obj, (User, JobRole)):
                await db.refresh(obj)
        return
    async with sessions() as session:
        await _bind(session)


async def _bind(db) -> None:
    if True:
        roles = {role.code: role for role in (await db.scalars(select(JobRole))).all()}
        for user in (await db.scalars(select(User))).all():
            role_ids = _system_user_role_ids(user)
            current = _configured_user_job_role_name(user)
            if "admin" in role_ids or (current and not current.startswith(TEST_ROLE_PREFIX)):
                continue
            payload = await _permission_payload_for_roles(role_ids, db)
            code = TEST_ROLE_PREFIX + "-".join(role_ids).upper()
            permissions = [*payload["menu_keys"], *(f"action:{key}" for key in payload["action_keys"]), CASE_ACTIONS_EXPLICIT_MARKER, MENUS_EXACT_MARKER]
            role = roles.get(code)
            if role is None:
                role = JobRole(code=code, name=code)
                db.add(role)
                roles[code] = role
            role.permissions = permissions
            role.field_keys = list(payload["field_keys"])
            role.field_keys_configured = True
            role.data_scope = payload["data_scope"]
            role.is_active = True
            if current != code:
                user.profile = {**(user.profile or {}), "permission_role_code": code}
        await db.commit()

"""501580：系统中心“自动任务”“逾期扣款”两个设置（陶国南 11-05 确认）。

每个设置列出全部部门和全部人事角色，默认都勾选；只存取消勾选的部门/角色，
这样以后新加的部门、角色默认仍是勾选（一切照旧）。人的部门或角色任一被取消，
就排除：“自动任务”里排除的人不再收到系统自动任务，“逾期扣款”里排除的人任务超期
不再记超期绩效。只管以后，已发的任务、已记的绩效不追溯。
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_models.identity import User

AUTOMATIC_TASK_SCOPE_KEY = "automatic_task_scope"
OVERDUE_PENALTY_SCOPE_KEY = "task_overdue_penalty_scope"
DEFAULT_SCOPE = {"excluded_departments": [], "excluded_roles": []}

SCOPES = {
    "automatic-task": {"key": AUTOMATIC_TASK_SCOPE_KEY, "title": "自动任务"},
    "overdue-penalty": {"key": OVERDUE_PENALTY_SCOPE_KEY, "title": "逾期扣款"},
}


def validate_scope(value) -> dict:
    if not isinstance(value, dict) or set(value) - set(DEFAULT_SCOPE):
        raise HTTPException(status_code=422, detail="设置格式不正确")
    cleaned = {}
    for field in DEFAULT_SCOPE:
        items = value.get(field) or []
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise HTTPException(status_code=422, detail="设置格式不正确")
        cleaned[field] = sorted({item.strip() for item in items if item.strip()})
    return cleaned


def _normalize(value) -> dict:
    try:
        return validate_scope(value if isinstance(value, dict) else {})
    except HTTPException:
        return dict(DEFAULT_SCOPE)


async def load_scope(db: AsyncSession, key: str) -> dict:
    from app.data_models.parameters import SystemConfig

    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    return _normalize(item.value if item else None)


async def user_role_names(user: User, db: AsyncSession) -> set[str]:
    from app.core.permissions import _configured_user_job_role_name, _job_role_for_name

    name = _configured_user_job_role_name(user)
    if not name:
        return set()
    names = {name}
    job_role = await _job_role_for_name(name, db)
    if job_role:
        names |= {job_role.code, job_role.name}
    return names


async def user_excluded(user: User | None, scope: dict, db: AsyncSession) -> bool:
    if user is None:
        return False
    departments = set(scope.get("excluded_departments") or [])
    roles = set(scope.get("excluded_roles") or [])
    if not departments and not roles:
        return False
    if departments and str(user.department or "").strip() in departments:
        return True
    return bool(roles and roles & await user_role_names(user, db))


async def username_excluded(username: str | None, scope: dict, db: AsyncSession, cache: dict | None = None) -> bool:
    if not username or not (scope.get("excluded_departments") or scope.get("excluded_roles")):
        return False
    if cache is not None and username in cache:
        return cache[username]
    user = await db.scalar(select(User).where(User.username == username))
    result = await user_excluded(user, scope, db)
    if cache is not None:
        cache[username] = result
    return result


async def scope_options(db: AsyncSession) -> dict:
    from app.data_models.identity import Department, JobRole

    departments = (await db.scalars(select(Department).where(Department.is_active.is_(True)).order_by(Department.sort_order, Department.id))).all()
    roles = (await db.scalars(select(JobRole).where(JobRole.is_active.is_(True)).order_by(JobRole.sort_order, JobRole.id))).all()
    return {
        "departments": [{"name": item.name} for item in departments],
        "roles": [{"code": item.code, "name": item.name} for item in roles],
    }

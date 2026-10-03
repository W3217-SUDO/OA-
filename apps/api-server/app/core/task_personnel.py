"""自动任务的人员识别与停用账号交接。"""

from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import logger
from app.models import Department, User


_SNAPSHOT_KEY = "automatic_task_personnel_snapshot"


@dataclass
class _PersonnelSnapshot:
    by_reference: dict[str, list[User]]
    by_username: dict[str, User]
    departments: dict[str, Department]


@asynccontextmanager
async def automatic_task_personnel_scope(db: AsyncSession):
    """每轮巡检独立读取人员，结束即释放，不缓存到下一轮或用户请求。"""
    if _SNAPSHOT_KEY in db.info:
        raise RuntimeError("自动任务人员快照不能在同一会话重复进入")
    users = list((await db.scalars(select(User).order_by(User.id))).all())
    departments = (await db.scalars(select(Department).where(Department.is_active.is_(True)))).all()
    by_reference = {}
    for user in users:
        for reference in {user.username, user.display_name}:
            by_reference.setdefault(reference, []).append(user)
    by_department = {}
    for department in departments:
        by_department.setdefault(department.name, department)
    db.info[_SNAPSHOT_KEY] = _PersonnelSnapshot(
        by_reference, {user.username: user for user in users}, by_department,
    )
    try:
        yield
    finally:
        del db.info[_SNAPSHOT_KEY]


async def resolve_automatic_task_user(values: object, db: AsyncSession) -> User | None:
    """优先保留在职人员；停用人员仅交给其所属部门的在职负责人。"""
    raw_values = values if isinstance(values, list) else [values]
    references = list(dict.fromkeys(str(value or "").strip() for value in raw_values if str(value or "").strip()))
    departed = []
    unresolved = []
    snapshot = db.info.get(_SNAPSHOT_KEY)
    for reference in references:
        if snapshot is not None:
            users = snapshot.by_reference.get(reference, [])
        else:
            users = list((await db.scalars(select(User).where(
                or_(User.username == reference, User.display_name == reference),
            ).order_by(User.id))).all())
        user = next((item for item in users if item.username == reference), None)
        if user is None and len(users) == 1:
            user = users[0]
        if user is None:
            unresolved.append(reference)
        elif user.is_active:
            return user
        else:
            departed.append(user)

    for user in departed:
        if snapshot is not None:
            department = snapshot.departments.get(user.department)
            manager = snapshot.by_username.get(department.manager) if department and department.manager else None
            if manager is not None and not manager.is_active:
                manager = None
        else:
            department = await db.scalar(select(Department).where(
                Department.name == user.department, Department.is_active.is_(True),
            ))
            manager = await db.scalar(select(User).where(
                User.username == department.manager, User.is_active.is_(True),
            )) if department and department.manager else None
        if manager:
            logger.debug("automatic task personnel reassigned: departed=%s manager=%s", user.username, manager.username)
            return manager
        logger.warning(
            "automatic task personnel unresolved: user=%s department=%s reason=no_active_department_manager",
            user.username, user.department,
        )
    if unresolved:
        logger.warning("automatic task personnel unresolved: references=%s reason=missing_or_ambiguous_account", unresolved)
    return None

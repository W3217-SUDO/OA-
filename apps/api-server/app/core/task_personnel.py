"""自动任务的人员识别与停用账号交接。"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import logger
from app.models import Department, User


async def resolve_automatic_task_user(values: object, db: AsyncSession) -> User | None:
    """优先保留在职人员；停用人员仅交给其所属部门的在职负责人。"""
    raw_values = values if isinstance(values, list) else [values]
    references = list(dict.fromkeys(str(value or "").strip() for value in raw_values if str(value or "").strip()))
    departed = []
    unresolved = []
    for reference in references:
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

"""BUG20261031002 第③步：“本部门数据”按部门树和挂靠人计算能看到哪些部门。

- 每人都能看自己所在部门；
- 挂在自己名下（挂靠人）的下级部门，以及它们再往下的各级部门；
- 自己担任负责人的部门，以及它们再往下的各级部门；
- 同部门其他人看不到别人名下的下级部门；
- 没设挂靠人的下级部门，跟着上级部门走：能看上级部门的人都能看（与改版前一致）。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department


def visible_department_names_from(departments: list[Department], username: str, own_department: str) -> set[str]:
    key = (username or "").strip().lower()
    names = {own_department} if (own_department or "").strip() else set()
    children: dict[int, list[Department]] = {}
    for item in departments:
        if item.parent_department_id:
            children.setdefault(item.parent_department_id, []).append(item)
    seen: set[int] = set()

    def walk(item: Department, whole_branch: bool) -> None:
        if item.id in seen:
            return
        seen.add(item.id)
        names.add(item.name)
        for child in children.get(item.id, []):
            # 负责人/挂靠人看整枝；普通成员只顺着没设挂靠人的下级部门往下看。
            if whole_branch or not (child.owner_username or "").strip():
                walk(child, whole_branch)

    for item in departments:
        if key and key in {(item.owner_username or "").strip().lower(), (item.manager or "").strip().lower()}:
            walk(item, True)
    for item in departments:
        if item.name == own_department:
            walk(item, False)
    return names


async def visible_department_names(username: str, own_department: str, db: AsyncSession) -> set[str]:
    departments = list((await db.scalars(select(Department).where(Department.is_active.is_(True)))).all())
    return visible_department_names_from(departments, username, own_department)

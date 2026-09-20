"""部门案件按组织人员的律师职责归属查询。"""
from sqlalchemy import false, or_, select
from fastapi import HTTPException
from app.models import BusinessRecord, Department, User


async def department_case_condition(identity, db):
    from app.core.permissions import _system_user_role_ids, _user_permission_payload
    user = await db.scalar(select(User).where(User.username == identity['username'], User.is_active.is_(True)))
    if user is None:
        raise HTTPException(401, '当前用户不存在或已停用')
    permission = await _user_permission_payload(user, db)
    if 'admin' not in _system_user_role_ids(user) and not any(
        str(key) == 'case-dept' or str(key).startswith('case-dept-') for key in permission['menu_keys']
    ):
        raise HTTPException(403, '当前角色没有部门案件权限')
    departments = list((await db.scalars(select(Department).where(Department.is_active.is_(True)))).all())
    roots = {item.id for item in departments if item.name == user.department}
    if not roots:
        return false()
    while True:
        expanded = roots | {item.id for item in departments if item.parent_department_id in roots}
        if expanded == roots:
            break
        roots = expanded
    names = {item.name for item in departments if item.id in roots}
    users = list((await db.scalars(select(User).where(User.department.in_(names), User.is_active.is_(True)))).all())
    usernames = {item.username for item in users}
    if not usernames:
        return false()
    data = BusinessRecord.data
    scalars = ('hearing_lawyer_username', 'court_lawyer_username', 'handling_lawyer_username', 'assistant_username')
    arrays = ('hearing_lawyer_usernames', 'handling_lawyer_usernames', 'assistant_usernames')
    return or_(
        *(data[key].as_string().in_(usernames) for key in scalars),
        *(data[key].as_string().contains(f'"{username}"') for key in arrays for username in usernames),
        *(data['legacy_record'][key].as_string().in_(usernames) for key in ('CourtLawyer', 'CaseLawyer', 'CaseAssistant')),
    )

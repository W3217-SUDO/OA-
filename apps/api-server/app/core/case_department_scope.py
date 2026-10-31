"""部门案件按组织人员的律师职责归属查询。"""
from sqlalchemy import cast, false, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import aliased
from fastapi import HTTPException
from app.models import BusinessRecord, User

_REGEX_SPECIAL = set(".^$*+?()[]{}|\\")


def _like_regex(value: str) -> str:
    """把 LIKE 片段（% 任意串、_ 单字符、\\ 转义）改写为等价的正则片段。"""
    parts, index = [], 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            index += 1
            char = value[index]
            parts.append("\\" + char if char in _REGEX_SPECIAL else char)
        elif char == "%":
            parts.append(".*")
        elif char == "_":
            parts.append(".")
        else:
            parts.append("\\" + char if char in _REGEX_SPECIAL else char)
        index += 1
    return "".join(parts)


def _array_contains_any(column, usernames, dialect):
    """与逐人 LIKE '%"用户名"%' 等价；PostgreSQL 上合成一条正则，每个字段只解析一次 JSON。"""
    if dialect == "postgresql":
        return column.regexp_match('"(' + "|".join(_like_regex(name) for name in sorted(usernames)) + ')"')
    return or_(*(column.contains(f'"{username}"') for username in usernames))


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
    # BUG20261031002：本部门 + 挂在自己名下/自己负责的下级部门，同部门同事看不到别人名下的下级部门。
    from app.core.department_visibility import visible_department_names
    names = await visible_department_names(user.username, user.department, db)
    if not names:
        return false()
    users = list((await db.scalars(select(User).where(User.department.in_(names), User.is_active.is_(True)))).all())
    usernames = {item.username for item in users}
    if not usernames:
        return false()
    scalars = ('hearing_lawyer_username', 'court_lawyer_username', 'handling_lawyer_username', 'assistant_username')
    arrays = ('hearing_lawyer_usernames', 'handling_lawyer_usernames', 'assistant_usernames')
    legacy = ('CourtLawyer', 'CaseLawyer', 'CaseAssistant')
    if db.get_bind().dialect.name != 'postgresql':
        data = BusinessRecord.data
        return or_(
            *(data[key].as_string().in_(usernames) for key in scalars),
            *(_array_contains_any(data[key].as_string(), usernames, 'sqlite') for key in arrays),
            *(data['legacy_record'][key].as_string().in_(usernames) for key in legacy),
        )
    # json 列每读一个键都要重新解压并解析整份文档；先逐行转成 jsonb 一次，十个键的读取就不再重复解析。
    # OFFSET 0 阻止优化器把子查询展开回各个条件里（展开后每个条件又会各自转换一次）。
    case = aliased(BusinessRecord)
    document = select(cast(case.data, JSONB).label('doc')).correlate(case).offset(0).lateral('case_doc')
    doc = document.c.doc
    matched = select(case.id).join(document, true()).where(case.module == 'case', or_(
        *(doc[key].astext.in_(usernames) for key in scalars),
        *(_array_contains_any(doc[key].astext, usernames, 'postgresql') for key in arrays),
        *(doc[('legacy_record', key)].astext.in_(usernames) for key in legacy),
    ))
    return BusinessRecord.id.in_(matched)

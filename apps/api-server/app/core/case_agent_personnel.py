"""智能体经办律师输入校验与案件团队投影。"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cases import _case_team_payload, _resolve_active_case_people
from app.core.contracts import _contract_person_values


def _case_agent_people_values(value: object, field_name: str) -> list[str]:
    values = value if isinstance(value, list) else [value]
    if not 1 <= len(values) <= 20 or any(
        not isinstance(item, str) or not 1 <= len(item.strip()) <= 128 for item in values
    ):
        raise HTTPException(status_code=422, detail=f"{field_name}必须包含 1 至 20 名有效人员，且每项必须为非空字符串")
    return list(dict.fromkeys(item.strip() for item in values))


async def _case_agent_handling_lawyer_data(case_data: dict, changes: dict, db: AsyncSession) -> dict:
    fields = {
        "handling_lawyer_usernames": "经办律师账号",
        "handling_lawyers": "经办律师",
        "case_lawyer": "兼容经办律师账号",
        "case_lawyer_name": "兼容经办律师姓名",
    }
    invalid = sorted(set(changes) - fields.keys())
    if invalid:
        raise HTTPException(status_code=422, detail=f"智能体无权修改人员字段：{', '.join(invalid)}")
    inputs = {
        field: _case_agent_people_values(changes[field], label)
        for field, label in fields.items() if field in changes
    }
    if not inputs:
        raise HTTPException(status_code=422, detail="请至少指定一名经办律师")
    resolved = {}
    for field, values in inputs.items():
        names, usernames = await _resolve_active_case_people(values, db, field_name=fields[field])
        if len(names) != len(usernames):
            raise HTTPException(status_code=422, detail=f"{fields[field]}不能重复指定同一人员")
        if field in {"handling_lawyer_usernames", "case_lawyer"} and values != usernames:
            raise HTTPException(status_code=422, detail=f"{fields[field]}必须使用有效登录账号")
        resolved[field] = (names, usernames)
    handling_lawyers, handling_usernames = next(iter(resolved.values()))
    for field, (_, usernames) in resolved.items():
        # 单值旧别名只代表首位经办律师，多值别名必须与完整有序列表一致。
        expected = handling_usernames[:1] if field.startswith("case_lawyer") and len(usernames) == 1 else handling_usernames
        if usernames != expected:
            raise HTTPException(status_code=422, detail="经办律师姓名、账号或兼容字段的人员与顺序不一致")
    updated = _case_team_payload(
        case_data, handling_lawyers, handling_usernames,
        [*_contract_person_values(case_data.get("assistants")), *_contract_person_values(case_data.get("assistant"))],
        [*_contract_person_values(case_data.get("assistant_usernames")), *_contract_person_values(case_data.get("assistant_username"))],
    )
    for field, values in (("case_lawyer", handling_usernames), ("case_lawyer_name", handling_lawyers)):
        if field in case_data:
            updated[field] = list(values) if isinstance(case_data[field], list) else values[0]
    return updated

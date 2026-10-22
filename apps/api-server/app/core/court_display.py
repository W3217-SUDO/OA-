"""法院权威名称解析及独立展示状态，不修改案件保存值。"""

from fastapi import HTTPException
from sqlalchemy import select

from app.models import SystemParameter


async def court_names_by_code(db) -> dict[str, str]:
    # 历史案件仍须解析已停用法院，不能使用新建表单的启用过滤。
    courts = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "court"))).all()
    return {str(item.code).strip().casefold(): str(item.name or "").strip() for item in courts}


def court_name(value: str, names_by_code: dict[str, str], case_no: str) -> str:
    value = value.strip()
    if not value:
        return ""
    name = names_by_code.get(value.casefold())
    if name:
        return name
    # 代码只能由权威参数解析；历史名称字段中的中文法院全称保持原值。
    is_saved_name = value in names_by_code.values() or (
        any("\u4e00" <= char <= "\u9fff" for char in value)
        and value.endswith(("法院", "法庭", "仲裁委员会"))
    )
    if value.casefold() not in names_by_code and is_saved_name:
        return value
    raise HTTPException(422, f"案件 {case_no} 的法院代码或名称 {value} 无法解析，请先完善法院参数")


def case_court_displays(data: dict, names_by_code: dict[str, str], case_no: str) -> dict:
    fields = {
        "court": ("court", "first_court_name", "first_instance_court"),
        "first": ("first_court_name", "first_instance_court", "court"),
        "second": ("second_court_name", "second_instance_court"),
        "execution": ("execution_court_name", "execution_instance_court"),
        "retrial": ("retrial_court_name", "last_instance_court"),
    }
    displays = {}
    for level, keys in fields.items():
        raw = next((str(data[key]).strip() for key in keys if data.get(key)), "")
        try:
            name = court_name(raw, names_by_code, case_no)
        except HTTPException as exc:
            # 展示错误限定在该字段；不能因一条未知代码使整页案件加载失败。
            if exc.status_code != 422:
                raise
            displays[level] = {"status": "unresolved", "raw": raw, "name": "", "error": exc.detail}
        else:
            displays[level] = {"status": "resolved" if name else "empty", "raw": raw, "name": name, "error": ""}
    return displays

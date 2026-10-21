"""新建案件的必填信息核对：智能体提交前先对照，缺什么当场告诉用户，不等保存失败才发现。"""
from app.core.constants import CASE_CLIENT_POSITIONS_BY_TYPE, CASE_CREATABLE_TYPES


def missing_case_create_fields(body: dict) -> list[str]:
    """按新建案件接口的规则列出还缺或不合规的信息；全部满足时返回空列表。"""
    missing: list[str] = []
    text = lambda key: str(body.get(key) or "").strip()
    case_type = text("case_type")
    if not text("title"):
        missing.append("案件名称")
    if case_type not in CASE_CREATABLE_TYPES:
        missing.append("案件类型（只能是：" + "、".join(sorted(CASE_CREATABLE_TYPES)) + "）")
    elif case_type == "法律顾问":
        if not text("counsel_type"):
            missing.append("顾问类型")
        start, end = body.get("counsel_start"), body.get("counsel_end")
        if not start or not end:
            missing.append("顾问期限（开始日期和结束日期都要填）")
        elif str(start) > str(end):
            missing.append("顾问期限有误：结束日期不能早于开始日期")
    else:
        if not text("cause_or_charge"):
            missing.append("案由或罪名")
        allowed = CASE_CLIENT_POSITIONS_BY_TYPE.get(case_type)
        if allowed and text("client_position") not in allowed:
            missing.append("客户诉讼地位（可选：" + "、".join(sorted(allowed)) + "）")
        if text("counsel_type") or body.get("counsel_start") or body.get("counsel_end"):
            missing.append("顾问类型和顾问期限只适用于法律顾问案件，请去掉")
    lawyers = [str(item or "").strip() for item in (body.get("handling_lawyers") or []) if str(item or "").strip()]
    if not lawyers:
        missing.append("经办律师")
    return missing

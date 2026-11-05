"""取案由（陶国南 11-05 13:10：系统里有的案由都要带出来）。所有文书模板统一用这一套，别各写一份。

顺序：案件基本信息的案由 → 当前审级法院信息里的案由 → 旧系统迁来的案由（legacy_record.CauseName）
→ 最后才按案件的权利类型推一个默认案由（商标 → 侵害商标权纠纷 等，只用于民事案件，律师可改）。
案由树里的编号（如“十五、不正当竞争纠纷”）去掉。
"""
from __future__ import annotations

import re

CAUSE_NUMBER = re.compile(r"^\s*(?:[一二三四五六七八九十百]+|\d+)[、.．]\s*")
CASE_CAUSE_KEYS = ("cause_or_charge", "cause", "cause_of_action", "cause_name", "charge")
# 侦查/调查模块里的权利类型编号（app/areas/investigation/router.py）。
RIGHT_TYPE_CAUSES = {"110010": "侵害商标权纠纷", "110020": "侵害专利权纠纷", "110030": "侵害著作权纠纷", "110040": "不正当竞争纠纷"}


def _stage_prefixes(status: str) -> tuple[str, ...]:
    """当前审级在前，其后退回一审（与文书模板取法院、案号的顺序一致）。"""
    if "执行" in status:
        return ("execution", "first")
    if "再审" in status:
        return ("retrial", "last", "first")
    if "二审" in status:
        return ("second", "first")
    return ("first",)


def _clean(value) -> str:
    text = str(value or "").strip()
    return CAUSE_NUMBER.sub("", text) if text and text.lower() not in ("none", "null") else ""


def case_cause_with_source(data: dict, status: str = "", *, infer: bool = True) -> tuple[str, str]:
    """返回（案由, 来源）。来源：案件 / 法院信息 / 旧系统 / 按权利类型推定 / 空。"""
    data = data or {}
    for key in CASE_CAUSE_KEYS:
        if value := _clean(data.get(key)):
            return value, "案件"
    for prefix in _stage_prefixes(status or ""):
        for key in (f"{prefix}_court_cause", f"{prefix}_instance_cause", f"{prefix}_court_cause_name"):
            if value := _clean(data.get(key)):
                return value, "法院信息"
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    for key in ("CauseName", "Cause", "CauseOfAction", "Reason"):
        if value := _clean(legacy.get(key)):
            return value, "旧系统"
    if infer and "民事" in str(data.get("case_type") or ""):
        right = str(data.get("case_right_type_id") or data.get("right_type_id") or legacy.get("CaseRightTypeId") or "")
        if right in RIGHT_TYPE_CAUSES:
            return RIGHT_TYPE_CAUSES[right], "按权利类型推定"
    return "", ""


def case_cause(data: dict, status: str = "", *, infer: bool = True) -> str:
    return case_cause_with_source(data, status, infer=infer)[0]

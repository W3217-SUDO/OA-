"""案件人员多人串拆分（501293）：迁移数据里多人存成 "sugq,sugq,sugq" 这样的串。"""
import re

CASE_PERSON_SPLIT = re.compile(r"[,，、;；|]+")


def split_case_people(*values: object) -> list[str]:
    """人员字段可能是列表或多人串，拆开去重，保持顺序。"""
    out: list[str] = []
    for value in values:
        for item in (value if isinstance(value, (list, tuple)) else [value]):
            out.extend(part.strip() for part in CASE_PERSON_SPLIT.split(str(item or "")) if part.strip())
    return list(dict.fromkeys(out))

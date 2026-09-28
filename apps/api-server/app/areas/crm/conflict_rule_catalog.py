"""经来源核对的上海利益冲突规则目录。"""

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path


_CATALOG_PATH = Path(__file__).with_name("conflict_rules_20260928.json")
_EXPECTED_IDS = {
    *(f"R-A{number:02d}" for number in range(1, 5)),
    *(f"R-B{number:02d}" for number in range(1, 6)),
    *(f"R-C{number:02d}" for number in range(1, 5)),
    *(f"R-D{number:02d}" for number in range(1, 7)),
    *(f"R-E{number:02d}" for number in range(1, 6)),
    "R-F01",
}


@lru_cache(maxsize=1)
def _catalog() -> dict:
    catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    rules = catalog["rules"]
    ids = [rule["id"] for rule in rules]
    if len(ids) != len(_EXPECTED_IDS) or set(ids) != _EXPECTED_IDS:
        raise ValueError("利益冲突规则目录的编号必须完整且唯一")
    if sum(rule["outcome_if_confirmed"] == "BLOCK" for rule in rules) != 13:
        raise ValueError("A至E类绝对禁止规则数量与来源不符")
    if sum(rule["outcome_if_confirmed"] == "WAIVER_REQUIRED" for rule in rules) != 11:
        raise ValueError("相对禁止规则数量与来源不符")
    special = [rule for rule in rules if rule["outcome_if_confirmed"] == "SPECIAL"]
    if len(special) != 1 or special[0]["id"] != "R-F01":
        raise ValueError("破产管理人专项规则与来源不符")
    if {branch["action"] for branch in special[0]["branches"]} != {
        "DISCLOSURE_REQUIRED", "CONFLICT_RECORDED", "BLOCK"
    }:
        raise ValueError("破产管理人专项处理分支不完整")
    required_fields = {"id", "category", "title", "outcome_if_confirmed", "legal_basis", "trigger", "required_facts", "manual_boundary"}
    if any(not required_fields.issubset(rule) for rule in rules):
        raise ValueError("利益冲突规则目录缺少必要字段")
    if catalog["automation_status"] != "MANUAL_REVIEW_ONLY":
        raise ValueError("规则目录尚不能启用自动判定")
    return catalog


def get_conflict_rule_catalog() -> dict:
    """返回独立副本，避免请求处理改变已审定的目录内容。"""
    return deepcopy(_catalog())

"""自动利益冲突审查总开关的状态与启用门禁。"""

from fastapi import HTTPException


CONFIG_KEY = "conflict_auto_review"
NOT_READY_REASON = "自动利冲审查尚未接入，当前仅支持人工核查"


def auto_review_status(value: dict | None) -> dict:
    """区分配置值与实际执行状态，避免把规则目录误认为自动审查。"""
    enabled = isinstance(value, dict) and value.get("enabled") is True
    return {
        "enabled": enabled,
        "ready": False,
        "effective": False,
        "reason": NOT_READY_REASON,
    }


def require_auto_review_ready(enabled: bool) -> None:
    if enabled:
        raise HTTPException(status_code=409, detail=NOT_READY_REASON)

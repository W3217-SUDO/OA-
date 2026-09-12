"""Evidence-bounded legacy task-type rules used by task handoff only.

``SkipDays`` is a handoff deadline ceiling in the legacy TaskNodeService.
It is deliberately not used as an automatic-task scheduling interval.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


# BAS_Case_TaskType rows verified in legacy-auto-task-rules-20260913.md.
LEGACY_TASK_TYPE_SKIP_DAYS: dict[int, int] = {
    100015: 15, 100016: 30, 100020: 30, 101002: 30, 101011: 30,
    101020: 30, 101023: 15, 101024: 30, 102017: 30, 102023: 15,
    102024: 30, 103015: 30, 103023: 15, 103024: 30, 104011: 30,
    104012: 30, 104014: 30, 104015: 30, 106012: 30, 1001001: 365,
    1001002: 30, 1001003: 15, 1001004: 15, 1001005: 30, 1010131: 30,
    1001003001: 15, 1001003002: 15, 1001003003: 15,
}


def _positive_int(value: Any) -> int | None:
    try:
        normalized = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return normalized if normalized > 0 else None


def _known_legacy_type_id(value: Any) -> int | None:
    normalized = _positive_int(value)
    return normalized if normalized in LEGACY_TASK_TYPE_SKIP_DAYS else None


def _projected_legacy_type_id(task_data: Mapping[str, Any]) -> int | None:
    for key in ("legacy_task_type_id", "TaskTypeId", "task_type_id"):
        type_id = _known_legacy_type_id(task_data.get(key))
        if type_id:
            return type_id
    projection = task_data.get("legacy_task_type")
    if isinstance(projection, Mapping):
        for key in ("id", "Id", "type_id", "TypeId"):
            type_id = _known_legacy_type_id(projection.get(key))
            if type_id:
                return type_id
    return None


def _auto_task_legacy_type_id(auto_task_type: Any) -> int | None:
    value = str(auto_task_type or "").strip()
    exact = {
        "document_preparation_stage": 101011,
        "execution_follow_up": 104012,
        "execution_end_follow_up": 104015,
        "first_mediation_closed_archive": 101024,
        "first_mediation_closed_reminder": 101024,
        "filing_follow_up": 1010131,
        "payment_received_30d_archive": 1001003,
        "preservation_deadline": 1001001,
    }
    if value in exact:
        return exact[value]
    prefixes = {
        "refund_application:": 1001004,
        "agency_fee_collection:": 1001005,
        "notary_audit:": 101002,
    }
    for prefix, type_id in prefixes.items():
        if value.startswith(prefix):
            return type_id
    for prefix in ("mediation_follow_up_", "settlement_archive_", "close_case_"):
        if value.startswith(prefix):
            return _known_legacy_type_id(value.removeprefix(prefix))
    return None


def legacy_task_type_id(task_data: Mapping[str, Any]) -> int | None:
    """Return an evidenced legacy type id, without guessing for unknown tasks."""
    return _projected_legacy_type_id(task_data) or _auto_task_legacy_type_id(task_data.get("auto_task_type"))


def _projection_skip_days(task_data: Mapping[str, Any], type_id: int) -> int | None:
    projection = task_data.get("legacy_task_type")
    if not isinstance(projection, Mapping):
        return None
    projected_type_id = _projected_legacy_type_id({"legacy_task_type": projection})
    if projected_type_id != type_id:
        return None
    for key in ("skip_days", "SkipDays"):
        days = _positive_int(projection.get(key))
        if days:
            return days
    return None


def _configured_skip_days(type_id: int, parameters: Iterable[Any]) -> int | None:
    """Read an optional explicitly-scoped ``legacy_task_type`` override.

    The parameter code itself must be the verified legacy type id.  Do not
    infer it from generic task parameters or an ``extra`` payload: that would
    let unrelated configuration accidentally alter a known task's deadline.
    """
    for parameter in parameters:
        if not getattr(parameter, "is_active", False):
            continue
        if str(getattr(parameter, "category", "")) != "legacy_task_type":
            continue
        extra = getattr(parameter, "extra", {}) or {}
        if not isinstance(extra, Mapping):
            continue
        parameter_type = _known_legacy_type_id(getattr(parameter, "code", ""))
        if parameter_type != type_id:
            continue
        for key in ("skip_days", "SkipDays"):
            days = _positive_int(extra.get(key))
            if days:
                return days
    return None


def handoff_skip_days(task_data: Mapping[str, Any], parameters: Iterable[Any] = ()) -> int | None:
    """Resolve only an evidenced handoff ceiling; unknown task types return None."""
    type_id = legacy_task_type_id(task_data)
    if not type_id:
        return None
    return (
        _configured_skip_days(type_id, parameters)
        or _projection_skip_days(task_data, type_id)
        or LEGACY_TASK_TYPE_SKIP_DAYS[type_id]
    )

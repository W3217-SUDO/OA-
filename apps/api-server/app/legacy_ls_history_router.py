"""Read-only API slice for the isolated legacy LS litigation carrier.

Integration is intentionally explicit: include ``router`` for admin-only
access, or call ``create_legacy_ls_history_router`` with a resolver that maps
the current user's already-visible ordinary cases to *explicitly stored*
``legacy_ls_case_id`` values.  There is no CaseNo, person-name, or text-based
fallback because that would broaden historical access without evidence.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .security import current_identity


LegacyLsVisibilityResolver = Callable[[dict[str, Any], AsyncSession], Awaitable[set[int]]]


async def _no_non_admin_legacy_ls_access(identity: dict[str, Any], db: AsyncSession) -> set[int]:
    """Fail closed until the application supplies a verified legacy-ID mapping."""

    return set()


def _snapshot(row: Any) -> dict[str, Any]:
    raw = row["source_snapshot"]
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="LS historical carrier contains an invalid source snapshot") from error
    if not isinstance(value, dict):
        raise HTTPException(status_code=503, detail="LS historical carrier contains an invalid source snapshot")
    return value


def _case_projection(row: Any) -> dict[str, Any]:
    source = _snapshot(row)
    return {
        "legacy_case_id": int(row["legacy_case_id"]),
        "case_no": source.get("CaseNo") or "",
        "case_phase_id": source.get("CasePhaseId"),
        "pre_case_phase_id": source.get("PreCasePhaseId"),
        "case_type_id": source.get("CaseTypeId"),
        "cause_id": source.get("CauseId"),
        "case_level": source.get("CaseLevel"),
        "case_submitter": source.get("CaseSubmitter") or "",
        "case_submit_date": source.get("CaseSubmitDate"),
        "case_origin_people": source.get("CaseOriginPeople") or "",
        "case_officer": source.get("CaseOfficer") or "",
        "contract_no": source.get("ContractNo") or "",
        "deadline": source.get("Deadline"),
        "reminder_date": source.get("ReminderDate"),
        "create_user": source.get("CreateUser") or "",
        "create_time": source.get("CreateTime"),
        "change_user": source.get("ChangeUser") or "",
        "change_time": source.get("ChangeTime"),
        "relationship_status": row["relationship_status"],
        "phase_history_row_count": int(row["phase_history_row_count"]),
        "current_case_record_id": row.get("current_case_record_id"),
        "current_case_mapping_state": row.get("current_case_mapping_state", "target_catalog_unavailable"),
        "contract_mapping_state": row.get("contract_mapping_state", "source_contract_absent"),
    }


def _phase_projection(row: Any) -> dict[str, Any]:
    source = _snapshot(row)
    return {
        "legacy_phase_id": int(row["legacy_phase_id"]),
        "legacy_case_id": int(row["legacy_case_id"]),
        "last_phase_id": source.get("LastPhaseId"),
        "current_phase_id": source.get("CurrentPhaseId"),
        "content": source.get("Content") or "",
        "create_user": source.get("CreateUser") or "",
        "create_time": source.get("CreateTime"),
        "change_user": source.get("ChangeUser") or "",
        "change_time": source.get("ChangeTime"),
        "relationship_status": row["relationship_status"],
    }


def _relation_projection(row: Any) -> dict[str, Any]:
    return {
        "relation_key": row["relation_key"],
        "source_table": row["source_table"],
        "source_primary_key": row["source_primary_key"],
        "entity_type": row["entity_type"],
        "legacy_case_id": int(row["legacy_case_id"]),
        "relationship_status": row["relationship_status"],
        "current_business_record_id": row.get("current_business_record_id"),
        "current_mapping_state": row.get("current_mapping_state", "target_catalog_unavailable"),
        "source": _snapshot(row),
    }


def _visibility_sql(identity: dict[str, Any], allowed_ids: set[int]) -> tuple[str, dict[str, Any]]:
    if identity.get("role") == "admin":
        return "1=1", {}
    if not allowed_ids:
        return "1=0", {}
    names = [f"legacy_case_id_{index}" for index, _ in enumerate(sorted(allowed_ids))]
    return f"legacy_case_id IN ({','.join(f':{name}' for name in names)})", {
        name: case_id for name, case_id in zip(names, sorted(allowed_ids))
    }


async def _visible_case_row(
    db: AsyncSession,
    identity: dict[str, Any],
    allowed_ids: set[int],
    legacy_case_id: int,
) -> Any:
    visibility_sql, visibility_params = _visibility_sql(identity, allowed_ids)
    try:
        result = await db.execute(text(f"""
            SELECT legacy_case_id, relationship_status, phase_history_row_count, current_case_record_id,
                   current_case_mapping_state, contract_mapping_state, source_snapshot
            FROM legacy_ls_cases
            WHERE legacy_case_id=:requested_case_id AND {visibility_sql}
        """), {"requested_case_id": legacy_case_id, **visibility_params})
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="LS historical carrier is unavailable") from error
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="LS historical case was not found")
    return row


def create_legacy_ls_history_router(
    *,
    visible_legacy_case_ids: LegacyLsVisibilityResolver = _no_non_admin_legacy_ls_access,
) -> APIRouter:
    """Create GET-only routes with an explicit, fail-closed non-admin scope."""

    router = APIRouter(prefix="/legacy-ls-history", tags=["legacy-ls-history"])

    async def allowed_ids(identity: dict[str, Any], db: AsyncSession) -> set[int]:
        if identity.get("role") == "admin":
            return set()
        return {int(value) for value in await visible_legacy_case_ids(identity, db)}

    @router.get("/cases")
    async def list_legacy_ls_cases(
        keyword: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        permitted = await allowed_ids(identity, db)
        visibility_sql, visibility_params = _visibility_sql(identity, permitted)
        params: dict[str, Any] = {
            **visibility_params,
            "keyword": f"%{keyword.strip()}%",
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        try:
            count = await db.execute(text(f"""
                SELECT COUNT(*) AS total FROM legacy_ls_cases
                WHERE {visibility_sql} AND (:keyword='%%' OR source_snapshot LIKE :keyword)
            """), params)
            rows = await db.execute(text(f"""
                SELECT legacy_case_id, relationship_status, phase_history_row_count, current_case_record_id,
                       current_case_mapping_state, contract_mapping_state, source_snapshot
                FROM legacy_ls_cases
                WHERE {visibility_sql} AND (:keyword='%%' OR source_snapshot LIKE :keyword)
                ORDER BY legacy_case_id DESC LIMIT :limit OFFSET :offset
            """), params)
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="LS historical carrier is unavailable") from error
        total = int(count.scalar_one())
        return {
            "items": [_case_projection(row) for row in rows.mappings().all()],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }

    @router.get("/cases/{legacy_case_id}")
    async def get_legacy_ls_case(
        legacy_case_id: int,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        row = await _visible_case_row(db, identity, await allowed_ids(identity, db), legacy_case_id)
        try:
            result = await db.execute(text("""
                SELECT relation_key, source_table, source_primary_key, entity_type,
                       legacy_case_id, relationship_status, current_business_record_id,
                       current_mapping_state, source_snapshot
                FROM legacy_ls_case_relations
                WHERE legacy_case_id=:legacy_case_id
                ORDER BY entity_type, source_table, source_primary_key
            """), {"legacy_case_id": legacy_case_id})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="LS historical relation carrier is unavailable") from error
        relations = [_relation_projection(item) for item in result.mappings().all()]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in relations:
            grouped.setdefault(item["entity_type"], []).append(item)
        return {"case": _case_projection(row), "relations": grouped}

    @router.get("/current-records/{current_record_id}")
    async def get_legacy_ls_case_by_current_record(
        current_record_id: int,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        """Find the sole carrier row explicitly mapped to an opened current case."""

        permitted = await allowed_ids(identity, db)
        visibility_sql, visibility_params = _visibility_sql(identity, permitted)
        try:
            result = await db.execute(text(f"""
                SELECT legacy_case_id FROM legacy_ls_cases
                WHERE current_case_record_id=:current_record_id AND {visibility_sql}
            """), {"current_record_id": current_record_id, **visibility_params})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="LS historical carrier is unavailable") from error
        rows = result.scalars().all()
        if len(rows) != 1:
            raise HTTPException(status_code=404, detail="No unique LS history is mapped to this current case")
        return {"legacy_case_id": int(rows[0])}

    @router.get("/cases/{legacy_case_id}/timeline")
    async def get_legacy_ls_case_timeline(
        legacy_case_id: int,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        await _visible_case_row(db, identity, await allowed_ids(identity, db), legacy_case_id)
        try:
            result = await db.execute(text("""
                SELECT legacy_phase_id, legacy_case_id, relationship_status, source_snapshot
                FROM legacy_ls_case_phases
                WHERE legacy_case_id=:legacy_case_id
            """), {"legacy_case_id": legacy_case_id})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="LS historical carrier is unavailable") from error
        items = [_phase_projection(row) for row in result.mappings().all()]
        items.sort(key=lambda item: (str(item["create_time"] or item["change_time"] or ""), item["legacy_phase_id"]))
        return {"legacy_case_id": legacy_case_id, "items": items, "total": len(items)}

    return router


router = create_legacy_ls_history_router()

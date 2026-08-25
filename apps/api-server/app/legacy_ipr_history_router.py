"""GET-only API for materialized legacy IPR master-case history.

The host application mounts this router only against the local, materialized
ledger tables. It never reads the old SQL Server and returns unavailable data
as a 503 rather than fabricating current customer links.
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


LegacyIprVisibilityResolver = Callable[[dict[str, Any], AsyncSession], Awaitable[set[int]]]


async def _no_non_admin_ipr_history_access(identity: dict[str, Any], db: AsyncSession) -> set[int]:
    """Deny non-admin history access until the host supplies a proven mapping."""
    return set()


def _json_object(value: Any, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail=f"IPR historical {label} is invalid") from error
    if not isinstance(decoded, dict):
        raise HTTPException(status_code=503, detail=f"IPR historical {label} is invalid")
    return decoded


def _case_projection(row: Any) -> dict[str, Any]:
    source = _json_object(row["source_snapshot"], "case snapshot")
    return {
        "legacy_case_id": int(row["legacy_case_id"]),
        "case_no": row["legacy_case_no"] or source.get("CaseNo") or "",
        "title": source.get("CaseName") or "",
        "case_type": source.get("CaseTypeName") or "",
        "case_phase_id": source.get("CasePhaseId"),
        "applicant": source.get("ApplicantName") or "",
        "contract_no": source.get("ContractNo") or "",
        "deadline": source.get("Deadline"),
        "relationship_state": row["migration_state"],
        "current_case_record_id": row["target_case_record_id"],
    }


def _customer_projection(row: Any) -> dict[str, Any]:
    relation = _json_object(row["source_snapshot"], "customer relation snapshot")
    current_id = row["current_customer_record_id"]
    legacy_customer_id = row["legacy_customer_id"]
    is_primary = str(relation.get("FirstApplicantId") or relation.get("CasePrimaryCustomerId") or "") == str(legacy_customer_id)
    return {
        "legacy_customer_id": legacy_customer_id,
        "legacy_customer_no": row["legacy_customer_no"] or relation.get("CustomerNo") or "",
        "legacy_customer_name": row["legacy_customer_name"] or relation.get("CustomerName") or "",
        "relationship_state": row["relation_state"],
        "identity_state": row["identity_state"] or "legacy_only",
        "is_primary": is_primary,
        "current_customer_record_id": current_id,
        "current_customer_link": {"record_id": int(current_id)} if current_id is not None else None,
    }


def _contact_projection(row: Any) -> dict[str, Any]:
    relation = _json_object(row["source_snapshot"], "contact relation snapshot")
    current_id = row["current_customer_record_id"]
    return {
        "legacy_contact_id": row["legacy_contact_id"],
        "legacy_customer_id": row["legacy_customer_id"],
        "legacy_contact_name": row["legacy_contact_name"] or relation.get("Contacts") or "",
        "email": relation.get("Email") or "",
        "mobilephone": relation.get("Mobilephone") or "",
        "contact_role": row["relation_role"],
        "relationship_state": row["relation_state"],
        "identity_state": row["identity_state"] or "legacy_only",
        "current_customer_record_id": current_id,
        "current_customer_link": {"record_id": int(current_id)} if current_id is not None else None,
    }


def _visibility_sql(identity: dict[str, Any], allowed_ids: set[int]) -> tuple[str, dict[str, Any]]:
    if identity.get("role") == "admin":
        return "1=1", {}
    if not allowed_ids:
        return "1=0", {}
    names = [f"legacy_case_id_{index}" for index, _ in enumerate(sorted(allowed_ids))]
    return f"legacy_case_id IN ({','.join(f':{name}' for name in names)})", {
        name: value for name, value in zip(names, sorted(allowed_ids))
    }


def create_legacy_ipr_history_router(
    *,
    visible_legacy_case_ids: LegacyIprVisibilityResolver = _no_non_admin_ipr_history_access,
) -> APIRouter:
    """Create GET-only history endpoints with fail-closed visibility."""

    router = APIRouter(prefix="/legacy-ipr-history", tags=["legacy-ipr-history"])

    async def permitted_ids(identity: dict[str, Any], db: AsyncSession) -> set[int]:
        if identity.get("role") == "admin":
            return set()
        return {int(value) for value in await visible_legacy_case_ids(identity, db)}

    async def case_row(legacy_case_id: int, identity: dict[str, Any], db: AsyncSession) -> Any:
        allowed = await permitted_ids(identity, db)
        visible_sql, visible_params = _visibility_sql(identity, allowed)
        try:
            result = await db.execute(text(f"""
                SELECT legacy_case_id, legacy_case_no, target_case_record_id, migration_state, source_snapshot
                FROM legacy_ipr_case_migrations
                WHERE legacy_case_id=:legacy_case_id AND {visible_sql}
            """), {"legacy_case_id": legacy_case_id, **visible_params})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="IPR historical carrier is unavailable") from error
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="IPR historical case was not found")
        return row

    @router.get("/cases")
    async def list_legacy_ipr_cases(
        keyword: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        identity: dict = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        allowed = await permitted_ids(identity, db)
        visible_sql, visible_params = _visibility_sql(identity, allowed)
        params = {**visible_params, "keyword": f"%{keyword.strip()}%", "limit": page_size, "offset": (page - 1) * page_size}
        try:
            count = await db.execute(text(f"""
                SELECT COUNT(*) AS total FROM legacy_ipr_case_migrations
                WHERE {visible_sql} AND (:keyword='%%' OR source_snapshot LIKE :keyword)
            """), params)
            rows = await db.execute(text(f"""
                SELECT legacy_case_id, legacy_case_no, target_case_record_id, migration_state, source_snapshot
                FROM legacy_ipr_case_migrations
                WHERE {visible_sql} AND (:keyword='%%' OR source_snapshot LIKE :keyword)
                ORDER BY legacy_case_id DESC LIMIT :limit OFFSET :offset
            """), params)
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="IPR historical carrier is unavailable") from error
        total = int(count.scalar_one())
        return {"items": [_case_projection(row) for row in rows.mappings().all()], "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}

    @router.get("/cases/{legacy_case_id}")
    async def get_legacy_ipr_case(
        legacy_case_id: int,
        identity: dict = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        case = await case_row(legacy_case_id, identity, db)
        try:
            customer_rows = await db.execute(text("""
                SELECT r.legacy_customer_id, r.relation_state, r.source_snapshot,
                       i.legacy_customer_no, i.legacy_customer_name, i.current_customer_record_id, i.identity_state
                FROM legacy_ipr_case_relation_ledger AS r
                LEFT JOIN legacy_customer_identity AS i ON i.legacy_customer_id=r.legacy_customer_identity_id
                WHERE r.entity_type='case_customer' AND r.legacy_case_id=:legacy_case_id
                ORDER BY r.legacy_customer_id
            """), {"legacy_case_id": legacy_case_id})
            contact_rows = await db.execute(text("""
                SELECT r.legacy_contact_id, r.legacy_customer_id, r.relation_role, r.relation_state, r.source_snapshot,
                       i.legacy_contact_name, i.current_customer_record_id, i.identity_state
                FROM legacy_ipr_case_relation_ledger AS r
                LEFT JOIN legacy_customer_contact_identity AS i
                  ON i.legacy_customer_id=r.legacy_customer_identity_id AND i.legacy_contact_id=r.legacy_contact_identity_id
                WHERE r.entity_type='case_customer_contact' AND r.legacy_case_id=:legacy_case_id
                ORDER BY r.legacy_customer_id, r.legacy_contact_id
            """), {"legacy_case_id": legacy_case_id})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="IPR historical carrier is unavailable") from error
        return {
            "case": _case_projection(case),
            "historical_customers": [_customer_projection(row) for row in customer_rows.mappings().all()],
            "historical_contacts": [_contact_projection(row) for row in contact_rows.mappings().all()],
        }

    return router


router = create_legacy_ipr_history_router()

"""GET-only access to the isolated FCM historical-contract carrier.

Integration stays explicit: include ``router`` from the application entrypoint
only after the history tables have been materialized.  Administrators can audit
all history; every non-admin request fails closed until the host application
supplies an evidence-backed history-parent visibility resolver.
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


LegacyContractVisibilityResolver = Callable[[dict[str, Any], AsyncSession], Awaitable[set[str]]]


async def _no_non_admin_history_access(identity: dict[str, Any], db: AsyncSession) -> set[str]:
    return set()


def _json(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Historical contract carrier contains an invalid JSON snapshot") from error


def _parent_projection(row: Any) -> dict[str, Any]:
    return {
        "history_parent_key": row["history_parent_key"],
        "legacy_contract_ids": _json(row["legacy_contract_ids"]),
        "legacy_contract_guids": _json(row["legacy_contract_guids"]),
        "legacy_contract_nos": _json(row["legacy_contract_nos"]),
        "legacy_customer_nos": _json(row["legacy_customer_nos"]),
        "relationship_state": row["relationship_state"],
        "source_parent_target_states": _json(row["source_parent_target_states"]),
        "source_relation_counts": _json(row["source_relation_counts"]),
    }


def _approval_projection(row: Any) -> dict[str, Any]:
    source = _json(row["legacy_payload"])
    return {
        "legacy_audit_id": int(row["legacy_audit_id"]),
        "legacy_contract_no": row["legacy_contract_no"],
        "relationship_state": row["relationship_state"],
        "audit_status": source.get("AuditStatus"),
        "auditor": source.get("Auditor") or "",
        "audit_date": source.get("AuditDate"),
        "audit_content": source.get("AuditContent") or "",
    }


def _attachment_projection(row: Any) -> dict[str, Any]:
    source = _json(row["legacy_payload"])
    return {
        "legacy_file_id": int(row["legacy_file_id"]),
        "legacy_file_guid": row["legacy_file_guid"],
        "file_name": source.get("FileName") or "",
        "file_size": source.get("FileSize"),
        "upload_user": source.get("UploadUser") or "",
        "upload_time": source.get("UploadTime"),
        "metadata_state": row["attachment_metadata_state"],
        "relationship_state": row["relationship_state"],
        "download_available": False,
        "download_reason": "Legacy physical file is unavailable; metadata is retained for audit only.",
    }


def _log_projection(row: Any) -> dict[str, Any]:
    source = _json(row["legacy_payload"])
    return {
        "legacy_event_id": int(row["legacy_event_id"]),
        "relationship_state": row["relationship_state"],
        "content": source.get("Content") or "",
        "operator": source.get("Operator") or "",
        "operate_time": source.get("OperateTime"),
    }


def _case_projection(row: Any) -> dict[str, Any]:
    source = _json(row["legacy_payload"])
    return {
        "legacy_case_source": row["legacy_case_source"],
        "legacy_case_id": int(row["legacy_case_id"]),
        "legacy_case_no": row["legacy_case_no"],
        "legacy_contract_no": row["legacy_contract_no"],
        "legacy_customer_no": row["legacy_customer_no"],
        "case_record_id": row["case_record_id"],
        "contract_record_id": row["contract_record_id"],
        "relationship_state": row["relationship_state"],
        "case_name": source.get("CaseName") or "",
        "case_phase_id": source.get("CasePhaseId"),
        "business_owner": source.get("BusinessOwner") or "",
    }


def _visibility_sql(identity: dict[str, Any], allowed_keys: set[str]) -> tuple[str, dict[str, Any]]:
    if identity.get("role") == "admin":
        return "1=1", {}
    if not allowed_keys:
        return "1=0", {}
    names = [f"history_parent_{index}" for index, _ in enumerate(sorted(allowed_keys))]
    return f"history_parent_key IN ({','.join(f':{name}' for name in names)})", {
        name: key for name, key in zip(names, sorted(allowed_keys))
    }


def create_legacy_contract_history_router(
    *,
    visible_history_parent_keys: LegacyContractVisibilityResolver = _no_non_admin_history_access,
) -> APIRouter:
    router = APIRouter(prefix="/legacy-contract-history", tags=["legacy-contract-history"])

    async def allowed_keys(identity: dict[str, Any], db: AsyncSession) -> set[str]:
        if identity.get("role") == "admin":
            return set()
        return {str(value) for value in await visible_history_parent_keys(identity, db) if str(value)}

    async def visible_parent(
        history_parent_key: str, identity: dict[str, Any], db: AsyncSession,
    ) -> Any:
        visibility_sql, visibility_params = _visibility_sql(identity, await allowed_keys(identity, db))
        try:
            result = await db.execute(text(f"""
                SELECT history_parent_key, legacy_contract_ids, legacy_contract_guids, legacy_contract_nos, legacy_customer_nos,
                       relationship_state, source_parent_target_states, source_relation_counts
                FROM legacy_contract_parents
                WHERE history_parent_key=:history_parent_key AND {visibility_sql}
            """), {"history_parent_key": history_parent_key, **visibility_params})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Historical contract carrier is unavailable") from error
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Historical contract parent was not found")
        return row

    @router.get("/parents")
    async def list_parents(
        keyword: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        visibility_sql, visibility_params = _visibility_sql(identity, await allowed_keys(identity, db))
        params = {**visibility_params, "keyword": f"%{keyword.strip()}%", "limit": page_size, "offset": (page - 1) * page_size}
        try:
            count = await db.execute(text(f"""
                SELECT COUNT(*) FROM legacy_contract_parents
                WHERE {visibility_sql} AND (:keyword='%%' OR source_snapshot LIKE :keyword)
            """), params)
            result = await db.execute(text(f"""
                SELECT history_parent_key, legacy_contract_ids, legacy_contract_guids, legacy_contract_nos, legacy_customer_nos,
                       relationship_state, source_parent_target_states, source_relation_counts
                FROM legacy_contract_parents
                WHERE {visibility_sql} AND (:keyword='%%' OR source_snapshot LIKE :keyword)
                ORDER BY history_parent_key DESC LIMIT :limit OFFSET :offset
            """), params)
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Historical contract carrier is unavailable") from error
        total = int(count.scalar_one())
        return {"items": [_parent_projection(row) for row in result.mappings().all()], "page": page, "page_size": page_size, "total": total}

    @router.get("/parents/{history_parent_key}")
    async def get_parent(
        history_parent_key: str,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        parent = await visible_parent(history_parent_key, identity, db)
        try:
            approvals = await db.execute(text("SELECT legacy_audit_id, legacy_contract_no, relationship_state, legacy_payload FROM legacy_contract_approvals WHERE history_parent_key=:key ORDER BY legacy_audit_id"), {"key": history_parent_key})
            attachments = await db.execute(text("SELECT legacy_file_id, legacy_file_guid, relationship_state, attachment_metadata_state, legacy_payload FROM legacy_contract_attachments WHERE history_parent_key=:key ORDER BY legacy_file_id"), {"key": history_parent_key})
            logs = await db.execute(text("SELECT legacy_event_id, relationship_state, legacy_payload FROM legacy_contract_logs WHERE history_parent_key=:key ORDER BY legacy_event_id"), {"key": history_parent_key})
            cases = await db.execute(text("""
                SELECT legacy_case_source, legacy_case_id, legacy_case_no, legacy_contract_no,
                       legacy_customer_no, case_record_id, contract_record_id, relationship_state, legacy_payload
                FROM legacy_contract_cases WHERE history_parent_key=:key
                ORDER BY legacy_case_source, legacy_case_id
            """), {"key": history_parent_key})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Historical contract carrier is unavailable") from error
        return {
            "parent": _parent_projection(parent),
            "approvals": [_approval_projection(row) for row in approvals.mappings().all()],
            "attachments": [_attachment_projection(row) for row in attachments.mappings().all()],
            "logs": [_log_projection(row) for row in logs.mappings().all()],
            "cases": [_case_projection(row) for row in cases.mappings().all()],
        }

    async def parents_for_alias(
        alias_kind: str,
        alias_value: str,
        identity: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        normalized = alias_value.strip().upper()
        if not normalized:
            return {"items": [], "total": 0}
        visibility_sql, visibility_params = _visibility_sql(identity, await allowed_keys(identity, db))
        try:
            result = await db.execute(text(f"""
                SELECT DISTINCT parent.history_parent_key, parent.legacy_contract_ids, parent.legacy_contract_guids,
                       parent.legacy_contract_nos, parent.legacy_customer_nos, parent.relationship_state,
                       parent.source_parent_target_states, parent.source_relation_counts
                FROM legacy_contract_parent_aliases alias
                JOIN legacy_contract_parents parent ON parent.history_parent_key=alias.history_parent_key
                WHERE alias.source_system='GDCRM' AND alias.alias_kind=:alias_kind AND alias.alias_value=:alias_value
                  AND {visibility_sql}
                ORDER BY parent.history_parent_key DESC
            """), {"alias_kind": alias_kind, "alias_value": normalized, **visibility_params})
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Historical contract carrier is unavailable") from error
        items = [_parent_projection(row) for row in result.mappings().all()]
        return {"items": items, "total": len(items)}

    @router.get("/contracts/{contract_no}")
    async def get_contract_history(
        contract_no: str,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        return await parents_for_alias("contract_no", contract_no, identity, db)

    @router.get("/customers/{customer_no}/contracts")
    async def get_customer_contract_history(
        customer_no: str,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        return await parents_for_alias("customer_no", customer_no, identity, db)

    @router.get("/cases/{legacy_case_source}/{legacy_case_id}/contract")
    async def get_case_contract(
        legacy_case_source: str,
        legacy_case_id: int,
        identity: dict[str, Any] = Depends(current_identity),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        visibility_sql, visibility_params = _visibility_sql(identity, await allowed_keys(identity, db))
        try:
            result = await db.execute(text(f"""
                SELECT c.legacy_case_source, c.legacy_case_id, c.legacy_case_no, c.legacy_contract_no,
                       c.legacy_customer_no, c.case_record_id, c.contract_record_id, c.relationship_state, c.legacy_payload,
                       c.history_parent_key
                FROM legacy_contract_cases c
                WHERE c.legacy_case_source=:legacy_case_source AND c.legacy_case_id=:legacy_case_id
                  AND c.history_parent_key IS NOT NULL
                  AND c.history_parent_key IN (
                      SELECT history_parent_key FROM legacy_contract_parents WHERE {visibility_sql}
                  )
            """), {
                "legacy_case_source": legacy_case_source,
                "legacy_case_id": legacy_case_id,
                **visibility_params,
            })
        except SQLAlchemyError as error:
            raise HTTPException(status_code=503, detail="Historical contract carrier is unavailable") from error
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Historical case-to-contract relation was not found")
        parent = await visible_parent(row["history_parent_key"], identity, db)
        return {"case": _case_projection(row), "parent": _parent_projection(parent)}

    return router


router = create_legacy_contract_history_router()

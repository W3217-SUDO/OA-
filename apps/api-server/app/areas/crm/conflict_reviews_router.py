"""利益冲突审核专用入口，提交人的反馈和审批人的逐条结论独立留痕。"""

from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.conflict_review import (
    ATTACHMENT_CATEGORY, CLEAR_STATUSES, REVIEW_MODULE, assess_conflict_review,
    can_review_conflicts, ensure_conflict_review_visible, get_conflict_review_gate,
    lock_review_source, now_text, review_enabled, review_history, review_payload,
    review_summary, save_review_revision, source_review, valid_review_attachments,
)
from app.core.conflict_review_facts import collect_conflict_facts
from app.core.conflict_review_rules import evaluate_conflict_facts
from app.core.constants import UPLOAD_ROOT
from app.core.dependencies import current_identity, get_db
from app.models import BusinessRecord, FileAttachment, SystemConfig, WorkflowEvent


router = APIRouter(prefix=f"{settings.api_prefix}/conflict-reviews")


class FeedbackInput(BaseModel):
    rule_id: str = Field(default="", max_length=32)
    action: Literal["false_positive", "waiver", "stop"]
    reason: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=30)
    revision: int = Field(ge=1)


class DecisionInput(BaseModel):
    rule_id: str = Field(min_length=1, max_length=32)
    decision: Literal["false_positive", "waiver", "reject"]
    reason: str = Field(min_length=1, max_length=4000)
    fingerprint: str = Field(min_length=64, max_length=64)
    revision: int = Field(ge=1)


async def _source_for_reader(record_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_case_read_visible, _ensure_contract_approval_access, _ensure_record_visible,
        _require_record_module_menu, _seal_application_capabilities,
    )
    record = await db.get(BusinessRecord, record_id)
    if not record or record.module not in {"case", "ipr_case", "contract", "seal"}:
        raise HTTPException(status_code=404, detail="合同、案件或用印记录不存在")
    if await can_review_conflicts(identity, db):
        return record
    if record.module == "case":
        return await _ensure_case_read_visible(record_id, identity, db)
    if record.module == "contract":
        return await _ensure_contract_approval_access(record_id, identity, db)
    if record.module == "seal":
        capabilities = await _seal_application_capabilities(record, identity, db)
        if any(capabilities.get(key) for key in ("approve", "reject", "stamp")):
            return record
    await _require_record_module_menu(record.module, identity, db, action="查看")
    return await _ensure_record_visible(record_id, identity, db)


async def _record_state(record: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    gate = await get_conflict_review_gate(record, db)
    summary = gate["review"]
    review = await db.get(BusinessRecord, summary["id"]) if summary else await source_review(record.id, db)
    payload = await review_payload(review, identity, db) if review else None
    if payload and summary:
        payload.update({key: summary[key] for key in ("status", "blocking", "kind", "summary")})
        if summary["status"] == "expired":
            payload.update({"can_feedback": False, "can_review": False})
    enabled = await review_enabled(db)
    can_check = bool((enabled or review) and (not review or review.status not in {"stopped", "rejected"}))
    message = gate["message"]
    if can_check and gate["record_id"] != record.id:
        try:
            await _source_for_reader(gate["record_id"], identity, db)
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
            can_check = False
            message += "；请由来源业务提交人或有权审批人重新核查"
    return {"review": payload, "blocking": gate["blocking"], "enabled": enabled,
            "can_view": bool(payload and payload["can_view"]),
            "can_check": can_check, "record_id": gate["record_id"], "message": message}


@router.get("")
async def list_conflict_reviews(view: Literal["my", "queue"] = "my", status: str = "", kind: str = "",
                                page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                                identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    reviewer = await can_review_conflicts(identity, db)
    if view == "queue" and not reviewer:
        raise HTTPException(status_code=403, detail="当前账号没有利益冲突审批权限")
    conditions = [BusinessRecord.module == REVIEW_MODULE]
    if view == "my":
        conditions.append(BusinessRecord.owner == identity["username"])
    if status:
        conditions.append(BusinessRecord.status == status)
    rows = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    if kind:
        rows = [row for row in rows if review_summary(row)["kind"] == kind]
    total = len(rows)
    return {"items": [await review_payload(row, identity, db, include_materials=False) for row in rows[(page - 1) * page_size:page * page_size]],
            "total": total, "page": page, "page_size": page_size, "can_review": reviewer}


@router.get("/record/{record_id}")
async def conflict_review_for_record(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await _record_state(await _source_for_reader(record_id, identity, db), identity, db)


@router.post("/record/{record_id}/check")
async def check_record_conflicts(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    source = await _source_for_reader(record_id, identity, db)
    existing = await source_review(source.id, db)
    if not await review_enabled(db) and not existing:
        raise HTTPException(status_code=409, detail="自动利益冲突审查尚未开启，请由本公司管理员配置")
    await assess_conflict_review(source, identity, db, trigger="manual_recheck")
    await db.commit()
    return await _record_state(source, identity, db)


@router.get("/{review_id}")
async def get_conflict_review(review_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    review = await ensure_conflict_review_visible(review_id, identity, db)
    payload = await review_payload(review, identity, db)
    source = await db.get(BusinessRecord, int((review.data or {}).get("source_record_id") or 0))
    payload["can_check"] = False
    if source and review.status not in {"stopped", "rejected"}:
        try:
            await _source_for_reader(source.id, identity, db)
            payload["can_check"] = True
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
        latest = evaluate_conflict_facts(await collect_conflict_facts(source, db))
        if latest["fingerprint"] != payload["fingerprint"]:
            payload.update({"status": "expired", "blocking": True, "summary": "判定事实已变化，请重新进行利益冲突审查", "can_feedback": False, "can_review": False})
    return payload


async def _locked_pending(review_id: int, identity: dict, db: AsyncSession, revision: int | None = None, *, check_fresh: bool = True) -> tuple[BusinessRecord, BusinessRecord]:
    review = await ensure_conflict_review_visible(review_id, identity, db)
    source_id = int((review.data or {}).get("source_record_id") or 0)
    await lock_review_source(source_id, db)
    await db.refresh(review)
    source = await db.get(BusinessRecord, source_id)
    if not source:
        raise HTTPException(status_code=409, detail="来源业务已不存在，不能处理此审查")
    if review.status != "pending":
        raise HTTPException(status_code=409, detail="当前审查已处理或已停止代理，请刷新查看结果")
    if revision is not None and revision != int((review.data or {}).get("revision") or 1):
        raise HTTPException(status_code=409, detail="审查意见已更新，请刷新后再操作")
    await db.refresh(source)
    current = evaluate_conflict_facts(await collect_conflict_facts(source, db)) if check_fresh else None
    if current and current["fingerprint"] != (review.data or {}).get("fingerprint"):
        raise HTTPException(status_code=409, detail={"code": "CONFLICT_REVIEW_REQUIRED", "message": "判定事实已变化，请先重新审查", "record_id": source.id, "review_id": review.id, "conflict_review": {**review_summary(review), "status": "expired", "blocking": True}})
    return review, source


def _pending_finding(data: dict, rule_id: str) -> tuple[list[dict], dict]:
    findings = [dict(item) for item in data.get("findings") or []]
    finding = next((item for item in findings if item["rule_id"] == rule_id), None)
    if not finding:
        raise HTTPException(status_code=404, detail="审查规则疑点不存在")
    if finding.get("status") != "pending":
        raise HTTPException(status_code=409, detail="该条规则已审核，请刷新查看最新结论")
    return findings, finding


@router.post("/{review_id}/feedback")
async def feedback_conflict_review(review_id: int, body: FeedbackInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    review = await ensure_conflict_review_visible(review_id, identity, db)
    if review.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有本次审查提交人可以反馈或停止代理")
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="必须填写理由或说明")
    review, source = await _locked_pending(review_id, identity, db, body.revision, check_fresh=body.action != "stop")
    data = dict(review.data or {})
    event = {"action": body.action, "rule_id": body.rule_id, "reason": reason, "by": identity["username"], "at": now_text(), "attachment_ids": list(dict.fromkeys(body.attachment_ids))}
    if body.action == "stop":
        new_status = "stopped"
    else:
        findings, finding = _pending_finding(data, body.rule_id)
        if body.action == "waiver":
            if finding["kind"] != "relative":
                raise HTTPException(status_code=422, detail="只有相对利益冲突可以提交书面豁免，绝对禁止不能豁免")
            await valid_review_attachments(review, body.attachment_ids, db)
        elif body.attachment_ids:
            await valid_review_attachments(review, body.attachment_ids, db)
        finding["feedback"] = event
        data["findings"] = findings
        new_status = "pending"
    data["history"] = review_history(data, event)
    await save_review_revision(review, data, new_status, db)
    source.data = {**(source.data or {}), "conflict_review": review_summary(review)}
    db.add(WorkflowEvent(record_id=review.id, action="停止代理" if body.action == "stop" else "提交利冲反馈", from_status="pending", to_status=new_status, operator=identity["username"], comment=f"{body.rule_id}：{reason}"))
    await db.commit()
    return await review_payload(review, identity, db)


@router.post("/{review_id}/decision")
async def decide_conflict_review(review_id: int, body: DecisionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if not await can_review_conflicts(identity, db):
        raise HTTPException(status_code=403, detail="当前账号没有利益冲突审批权限")
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="必须填写审核意见")
    review, source = await _locked_pending(review_id, identity, db, body.revision)
    data = dict(review.data or {})
    if body.fingerprint != data.get("fingerprint"):
        raise HTTPException(status_code=409, detail="审查事实版本已更新，请刷新后重新核实")
    findings, finding = _pending_finding(data, body.rule_id)
    if body.decision == "waiver":
        if finding["kind"] != "relative":
            raise HTTPException(status_code=422, detail="绝对禁止及专项规则不得按相对豁免放行")
        feedback = finding.get("feedback") or {}
        if feedback.get("action") != "waiver" or not str(feedback.get("reason") or "").strip():
            raise HTTPException(status_code=422, detail="提交人尚未提交本条规则的书面豁免及说明")
        await valid_review_attachments(review, feedback.get("attachment_ids") or [], db)
    decision = {"decision": body.decision, "reason": reason, "by": identity["username"], "at": now_text()}
    finding["decision"] = decision
    finding["status"] = {"false_positive": "approved_false_positive", "waiver": "approved_waiver", "reject": "rejected"}[body.decision]
    new_status = "rejected" if body.decision == "reject" else "pending"
    if all(item["status"] in CLEAR_STATUSES for item in findings):
        new_status = "approved_waiver" if any(item["status"] == "approved_waiver" for item in findings) else "approved_false_positive"
    data.update({"findings": findings, "history": review_history(data, {"action": "审核结论", "rule_id": body.rule_id, **decision})})
    await save_review_revision(review, data, new_status, db)
    source.data = {**(source.data or {}), "conflict_review": review_summary(review)}
    db.add(WorkflowEvent(record_id=review.id, action="利益冲突审核", from_status="pending", to_status=new_status, operator=identity["username"], comment=f"{body.rule_id}：{body.decision}；{reason}"))
    await db.commit()
    return await review_payload(review, identity, db)


@router.post("/{review_id}/attachments", status_code=201)
async def upload_conflict_attachment(review_id: int, file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    review, _source = await _locked_pending(review_id, identity, db)
    if review.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有提交人可以上传书面材料")
    original_name = Path(str(file.filename or "").replace("\\", "/")).name
    if not original_name or len(original_name) > 255:
        raise HTTPException(status_code=422, detail="附件名称不能为空且不能超过255个字符")
    config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "application_settings"))
    limit_mb = int((config.value or {}).get("attachment_limit_mb") or 20) if config else 20
    content = await file.read(limit_mb * 1024 * 1024 + 1)
    if not content or len(content) > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=422, detail=f"材料不能为空且不能超过{limit_mb}MB")
    target = UPLOAD_ROOT / f"{uuid4().hex}{Path(original_name).suffix.lower()}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        target.write_bytes(content)
        item = FileAttachment(record_id=review.id, category=ATTACHMENT_CATEGORY, original_name=original_name, stored_name=target.name,
                              content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=(review.data or {})["fingerprint"])
        db.add(item)
        await db.flush()
        db.add(WorkflowEvent(record_id=review.id, action="上传利冲书面材料", from_status=review.status, to_status=review.status, operator=identity["username"], comment=original_name))
        await db.commit()
        await db.refresh(item)
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    return {"id": item.id, "original_name": item.original_name, "size": item.size, "download_url": f"{settings.api_prefix}/conflict-reviews/{review.id}/attachments/{item.id}/download"}


@router.get("/{review_id}/attachments/{attachment_id}/download")
async def download_conflict_attachment(review_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.storage import _attachment_storage_path
    await ensure_conflict_review_visible(review_id, identity, db)
    item = await db.get(FileAttachment, attachment_id)
    if not item or item.record_id != review_id or item.category != ATTACHMENT_CATEGORY:
        raise HTTPException(status_code=404, detail="本次审查附件不存在")
    path = _attachment_storage_path(item)
    if not path:
        raise HTTPException(status_code=404, detail="书面材料文件不存在")
    return FileResponse(path, media_type=item.content_type, filename=item.original_name)

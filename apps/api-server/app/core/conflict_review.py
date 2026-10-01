"""利冲审查状态、真实授权和业务门禁；不提交调用方的业务事务。"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.conflict_review_facts import collect_conflict_facts, related_conflict_sources
from app.core.conflict_review_rules import evaluate_conflict_facts
from app.models import BusinessRecord, FileAttachment, SystemConfig, User, WorkflowEvent


CONFIG_KEY = "conflict_auto_review"
REVIEW_MODULE = "conflict_review"
REVIEW_ACTION = "conflict.review.approve"
ATTACHMENT_CATEGORY = "利益冲突书面材料"
CLEAR_STATUSES = {"clear", "approved_false_positive", "approved_waiver"}
TERMINAL_STATUSES = {"rejected", "stopped"}


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def can_manage_auto_review(identity: dict) -> bool:
    """与系统配置接口的实际管理员或系统菜单授权保持一致。"""
    actual_roles = {str(role) for role in identity.get("_actual_role_ids") or []}
    menu_keys = {str(key) for key in identity.get("menu_keys") or []}
    return "admin" in actual_roles or any(
        key == "system" or key.startswith("system-") for key in menu_keys
    )


def auto_review_status(value: dict | None) -> dict:
    enabled = isinstance(value, dict) and value.get("enabled") is True
    return {"enabled": enabled, "ready": True, "effective": enabled,
            "reason": "自动检索与人工核查流程已接入，资料不足须人工核实；关闭开关不解除已有阻断"}


async def review_enabled(db: AsyncSession) -> bool:
    config = await db.scalar(select(SystemConfig).where(SystemConfig.key == CONFIG_KEY))
    return auto_review_status(config.value if config else None)["enabled"]


async def can_review_conflicts(identity: dict, db: AsyncSession) -> bool:
    from app.core.permissions import _user_permission_payload
    username = str(identity.get("username") or "")
    cached = identity.get("_conflict_review_permission")
    if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == username:
        return cached[1] is True
    user = await db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if not user:
        identity["_conflict_review_permission"] = (username, False)
        return False
    permission = await _user_permission_payload(user, db)
    keys = set(permission.get("action_keys") or [])
    allowed = "*" in keys or REVIEW_ACTION in keys
    identity["_conflict_review_permission"] = (username, allowed)
    return allowed


async def ensure_conflict_review_visible(review_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    review = await db.get(BusinessRecord, review_id)
    if not review or review.module != REVIEW_MODULE:
        raise HTTPException(status_code=404, detail="利益冲突审查不存在")
    if review.owner != identity.get("username") and not await can_review_conflicts(identity, db):
        raise HTTPException(status_code=403, detail="仅提交人或获授权的利益冲突审批人员可以查看审查材料")
    return review


async def source_review(record_id: int, db: AsyncSession) -> BusinessRecord | None:
    return await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == REVIEW_MODULE, BusinessRecord.serial_no == f"LCS-{record_id}",
    ).execution_options(populate_existing=True))


def review_summary(review: BusinessRecord) -> dict:
    data = review.data or {}
    findings = data.get("findings") or []
    unresolved = [item for item in findings if item.get("status") not in CLEAR_STATUSES]
    kinds = {item.get("kind") for item in (unresolved or findings)}
    kind = "absolute" if "absolute" in kinds else "relative" if "relative" in kinds else "special"
    blocking = review.status not in CLEAR_STATUSES
    titles = [str(item.get("title") or "") for item in unresolved]
    label = "绝对利益冲突疑点" if kind == "absolute" else "相对利益冲突疑点" if kind == "relative" else "利益冲突专项事实待核实"
    return {
        "id": review.id, "source_record_id": data.get("source_record_id"), "source_module": data.get("source_module"),
        "source_title": data.get("source_title"), "source_no": data.get("source_no"),
        "status": review.status, "kind": kind, "blocking": blocking, "fingerprint": data.get("fingerprint", ""),
        "revision": int(data.get("revision") or 1), "findings": [{key: value for key, value in item.items() if key not in {"feedback", "decision"}} for item in findings],
        "summary": ("已停止代理" if review.status == "stopped" else "利益冲突审核不通过" if review.status == "rejected" else f"{label}：{'；'.join(titles[:3])}" if blocking else "利益冲突审查已通过"),
    }


async def lock_review_source(record_id: int, db: AsyncSession) -> None:
    """锁定稳定来源行，覆盖首次创建和不同审查员并发修改JSON的事务窗口。"""
    await db.execute(update(BusinessRecord).where(BusinessRecord.id == record_id).values(updated_at=BusinessRecord.updated_at))


async def save_review_revision(review: BusinessRecord, data: dict, new_status: str, db: AsyncSession) -> None:
    expected = int((review.data or {}).get("revision") or 1)
    next_data = {**data, "revision": expected + 1}
    result = await db.execute(update(BusinessRecord).where(
        BusinessRecord.id == review.id, BusinessRecord.module == REVIEW_MODULE,
        BusinessRecord.data["revision"].as_integer() == expected,
    ).values(data=next_data, status=new_status).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="该审查已被其他人员处理，请刷新后再操作")
    await db.refresh(review)


def review_history(data: dict, event: dict) -> list[dict]:
    return [*(data.get("history") or []), {**event, "at": now_text(), "fingerprint": data.get("fingerprint", "")}]


async def assess_conflict_review(record: BusinessRecord, identity: dict, db: AsyncSession, trigger: str = "case_save") -> dict | None:
    """评估已保存或已flush的来源，创建/更新审查并投影摘要；调用方负责一次性提交。"""
    if record.module not in {"contract", "case", "ipr_case", "seal"}:
        raise HTTPException(status_code=422, detail="该业务类型不支持利益冲突自动审查")
    if not record.id:
        await db.flush()
    existing = await source_review(record.id, db)
    if not await review_enabled(db) and not existing:
        record.data = {key: value for key, value in (record.data or {}).items() if key != "conflict_review"}
        gate = await get_conflict_review_gate(record, db, existing_only=True)
        if gate["review"]:
            record.data = {**(record.data or {}), "conflict_review": gate["review"]}
        return gate["review"]
    if record.module == "seal" and len(await related_conflict_sources(record, db)) == 1 and not existing:
        return None
    await lock_review_source(record.id, db)
    existing = await source_review(record.id, db)
    if existing and existing.status in TERMINAL_STATUSES:
        record.data = {**(record.data or {}), "conflict_review": review_summary(existing)}
        return review_summary(existing)
    assessment = evaluate_conflict_facts(await collect_conflict_facts(record, db))
    if existing and (existing.data or {}).get("fingerprint") == assessment["fingerprint"]:
        review = existing
    else:
        previous = dict(existing.data or {}) if existing else {}
        if existing:
            submitter = existing.owner
        elif trigger == "case_save" and record.module in {"case", "ipr_case"}:
            # 复制、线索转案等来源可能保留旧提交人，首次保存使用本次实际操作人。
            submitter = identity["username"]
        else:
            submitter = await source_submitter(record, db)
        findings = assessment["findings"]
        new_ids = {item["rule_id"] for item in findings}
        # 改类型或删当事人不能让尚未解除的原绝对疑点从审查中消失。
        findings.extend({**item, "status": "pending", "feedback": None, "decision": None,
                         "reason": "此前审查疑点在资料变更后仍需明确核实：" + str(item.get("reason") or "")}
                        for item in previous.get("findings") or [] if item["rule_id"] not in new_ids and item.get("status") not in CLEAR_STATUSES)
        data = {
            **assessment, "findings": findings, "source_record_id": record.id, "source_module": record.module,
            "source_title": record.title, "source_no": record.serial_no, "trigger": trigger,
            "submitter": submitter, "revision": 1,
            "history": review_history(previous, {"action": "资料变化重新审查" if existing else "自动发起审查", "by": identity["username"],
                                           **({"previous_findings": previous.get("findings") or []} if existing else {})}),
        }
        if existing:
            await save_review_revision(existing, data, "pending" if findings else "clear", db)
            review = existing
        else:
            review = BusinessRecord(module=REVIEW_MODULE, serial_no=f"LCS-{record.id}", title=f"利益冲突审查：{record.title}"[:255],
                                    customer=record.customer, department=record.department, owner=submitter,
                                    status="pending" if findings else "clear", data=data)
            db.add(review)
            await db.flush()
        db.add(WorkflowEvent(record_id=review.id, action="自动利益冲突审查", to_status=review.status, operator=identity["username"], comment=f"触发：{trigger}；来源：{record.serial_no}"))
    gate = await get_conflict_review_gate(record, db, check_fresh=False)
    summary = gate["review"] or review_summary(review)
    record.data = {**(record.data or {}), "conflict_review": summary}
    return summary


async def source_submitter(record: BusinessRecord, db: AsyncSession) -> str:
    """审批人触发同步用印或历史重查时，反馈权仍属于原业务提交人。"""
    source = record
    if record.module == "seal" and (record.data or {}).get("use_type") == "合同用印":
        sources = await related_conflict_sources(record, db)
        contract = next((item for item in sources if item.module == "contract"), None)
        if contract:
            source = contract
    data = source.data or {}
    key = "submitted_by" if source.module == "contract" else "case_creation_submitted_by" if source.module == "case" else ""
    candidate = str(data.get(key) or source.owner or "").strip()
    if not candidate or not await db.scalar(select(User.id).where(User.username == candidate)):
        raise HTTPException(status_code=409, detail="来源业务未登记有效提交人，请先修正负责人资料")
    return candidate


async def get_conflict_review_gate(record: BusinessRecord, db: AsyncSession, action: str = "继续办理", *, check_fresh: bool = True, existing_only: bool = False) -> dict:
    """只读计算当前及关联业务阻断；不创建审查、不提交或回滚任何事务。"""
    enabled = await review_enabled(db)
    own_review = await source_review(record.id, db)
    sources = await related_conflict_sources(record, db, strict=(enabled and not existing_only) or own_review is not None)
    own_summary = None
    for source in sources:
        review = await source_review(source.id, db)
        if not review:
            continue
        summary = review_summary(review)
        if source.id == record.id:
            own_summary = summary
        if check_fresh and review.status not in TERMINAL_STATUSES and (not existing_only or not summary["blocking"]):
            latest = evaluate_conflict_facts(await collect_conflict_facts(source, db))
            if latest["fingerprint"] != summary["fingerprint"]:
                stale = {**summary, "status": "expired", "blocking": True, "summary": "判定事实已变化，请重新进行利益冲突审查"}
                return {"blocking": True, "review": stale, "record_id": source.id, "message": f"判定事实已变化，请重新审查后{action}"}
        if summary["blocking"]:
            return {"blocking": True, "review": summary, "record_id": source.id, "message": f"{summary['summary']}，暂不能{action}"}
    if not own_review and enabled and not existing_only and not (record.module == "seal" and len(sources) == 1):
        return {"blocking": True, "review": None, "record_id": record.id, "message": f"请先保存资料并完成利益冲突审查后{action}"}
    return {"blocking": False, "review": own_summary, "record_id": record.id, "message": ""}


async def require_conflict_clear(record: BusinessRecord, db: AsyncSession, action: str = "继续办理", *, existing_only: bool = False) -> None:
    gate = await get_conflict_review_gate(record, db, action, existing_only=existing_only)
    if gate["blocking"]:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT_REVIEW_REQUIRED", "message": gate["message"],
                            "record_id": gate["record_id"], "review_id": (gate["review"] or {}).get("id"), "conflict_review": gate["review"]})


async def valid_review_attachments(review: BusinessRecord, ids: list[int], db: AsyncSession) -> list[FileAttachment]:
    from app.core.storage import _attachment_storage_path
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids:
        raise HTTPException(status_code=422, detail="相对冲突豁免必须上传书面豁免材料")
    items = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(unique_ids)))).all())
    if len(items) != len(unique_ids) or any(item.record_id != review.id or item.category != ATTACHMENT_CATEGORY or item.uploader != review.owner or item.remark != (review.data or {}).get("fingerprint") or item.size <= 0 or _attachment_storage_path(item) is None for item in items):
        raise HTTPException(status_code=422, detail="书面材料必须是提交人在本次审查上传的有效文件")
    return items


async def review_payload(review: BusinessRecord, identity: dict, db: AsyncSession, *, include_materials: bool = True) -> dict:
    from app.config import settings
    data = review.data or {}
    reviewer = await can_review_conflicts(identity, db)
    own = review.owner == identity.get("username")
    summary = review_summary(review)
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == review.id, FileAttachment.category == ATTACHMENT_CATEGORY).order_by(FileAttachment.id))).all()) if include_materials and (reviewer or own) else []
    return {
        **summary, "submitter": review.owner, "missing_facts": data.get("missing_facts") or [],
        "findings": (data.get("findings") or []) if own or reviewer else summary["findings"],
        "history": (data.get("history") or []) if include_materials and (reviewer or own) else [],
        "attachments": [{"id": item.id, "original_name": item.original_name, "size": item.size,
                         "current": item.remark == data.get("fingerprint"),
                         "download_url": f"{settings.api_prefix}/conflict-reviews/{review.id}/attachments/{item.id}/download"} for item in attachments],
        "can_feedback": own and review.status == "pending", "can_review": reviewer and review.status == "pending",
        "can_view_detail": own or reviewer, "can_view": own or reviewer,
        "created_at": review.created_at, "updated_at": review.updated_at,
    }

"""本地测试清理路由，不注册到生产 ASGI 应用。"""

from fastapi import APIRouter

from tests.environment import validate_loaded_test_settings, validate_test_environment

validate_test_environment()

from app.config import settings

validate_loaded_test_settings(settings)

from app.core.constants import UPLOAD_ROOT
from app.core.dependencies import (
    AgentDocument, AsyncSession, BusinessRecord, CaseAssistedFee,
    ContractApprovalStep, Depends, FileAttachment, FinanceTransaction,
    HTTPException, HearingSchedule, IprCaseFileCustomImportBatch,
    IprCaseFileCustomImportCandidate, IprOfficialImportBatch,
    IprOfficialImportCandidate, Path, Response, WorkflowEvent,
    current_identity, delete, get_db, json, select, status,
)

router = APIRouter()


@router.delete(
    f"{settings.api_prefix}/testing/ipr-case-file-custom-import-batches/{{batch_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_test_ipr_case_file_custom_import_batch(batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Precise cleanup for test batches only; never exposed through the production workflow."""
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以清理测试导入批次")
    batch = await db.get(IprCaseFileCustomImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="测试自定义导入批次不存在")
    source_path = Path(batch.source_path)
    smoke_filename = (
        batch.source_filename.startswith("SMOKEA0000000001W0000000001-")
        or batch.source_filename == "A0000000001W0000000001.txt"
    )
    smoke_source = (
        smoke_filename
        and source_path.is_file()
        and UPLOAD_ROOT.resolve() in source_path.resolve().parents
        and source_path.read_bytes() in {b"SMOKE custom import source", b"SMOKE custom import valid source"}
    )
    if not batch.is_test and not smoke_source:
        raise HTTPException(status_code=404, detail="测试自定义导入批次不存在")
    candidates = list((await db.scalars(select(IprCaseFileCustomImportCandidate).where(IprCaseFileCustomImportCandidate.batch_id == batch.id))).all())
    attachment_ids = [row.attachment_id for row in candidates if row.attachment_id]
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all()) if attachment_ids else []
    for attachment in attachments:
        path = Path(attachment.path)
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink(missing_ok=True)
        await db.delete(attachment)
    if source_path.is_file() and UPLOAD_ROOT.resolve() in source_path.resolve().parents:
        source_path.unlink(missing_ok=True)
    await db.execute(delete(IprCaseFileCustomImportCandidate).where(IprCaseFileCustomImportCandidate.batch_id == batch.id))
    await db.delete(batch); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.delete(
    f"{settings.api_prefix}/testing/ipr-official-import-batches/{{batch_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_smoke_ipr_official_import_batch(
    batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Remove one explicitly marked local smoke import batch and its generated records.

    Candidate imports intentionally create no formal record until confirmation.  The
    smoke suite does confirm candidates to prove that boundary, so it needs a
    narrowly scoped cleanup path that also removes the retained source CSV.  This
    endpoint is unavailable in production and accepts only a file name from the
    suite's fixed ``smoke-`` namespace; it cannot delete normal import batches.
    """
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以清理本地冒烟导入批次")
    batch = await db.get(IprOfficialImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="官文导入批次不存在")
    if not (batch.source_filename.lower().startswith("smoke-") or batch.source_filename.lower().startswith(".tmp-codex-")):
        raise HTTPException(status_code=403, detail="只能清理带明确 SMOKE 或 CODEX 文件名标识的本地导入批次")
    source_path = Path(batch.source_path)
    candidates = list((await db.scalars(
        select(IprOfficialImportCandidate).where(IprOfficialImportCandidate.batch_id == batch.id)
    )).all())
    record_ids = [candidate.official_record_id for candidate in candidates if candidate.official_record_id]
    if record_ids:
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(record_ids)))).all())
        attachment_paths = [Path(item.path) for item in attachments]
        for attachment in attachments:
            await db.delete(attachment)
        await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id.in_(record_ids)))
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(record_ids)))
        await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(record_ids), BusinessRecord.module == "ipr_official_file"))
    else:
        attachment_paths = []
    await db.execute(delete(IprOfficialImportCandidate).where(IprOfficialImportCandidate.batch_id == batch.id))
    await db.delete(batch)
    await db.commit()
    for path in [source_path, *attachment_paths]:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.delete(
    f"{settings.api_prefix}/testing/cases/{{case_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_smoke_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Non-production cleanup for records created by the end-to-end smoke suite only."""
    from app.core.cases import (
        _delete_case_events_for_case_cleanup,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可清理本地冒烟案件")
    record = await db.get(BusinessRecord, case_id)
    if not record:
        raise HTTPException(status_code=404, detail="案件不存在")
    if record.module != "case":
        raise HTTPException(status_code=422, detail="该测试清理入口仅支持案件")
    if not (record.serial_no.startswith("SMOKE-") or record.title.startswith("SMOKE")):
        raise HTTPException(status_code=403, detail="只能清理本地冒烟测试案件")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == case_id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    related_tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.data["case_id"].as_integer() == case_id))).all())
    for task in related_tasks:
        await _delete_task_notifications(task.id, db)
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
        await db.delete(task)
    await db.execute(delete(CaseAssistedFee).where(CaseAssistedFee.case_record_id == case_id))
    await db.execute(delete(HearingSchedule).where(HearingSchedule.case_record_id == case_id))
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == case_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == case_id))
    await _delete_case_events_for_case_cleanup(case_id, db)
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.delete(
    f"{settings.api_prefix}/testing/records/{{record_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_smoke_record(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Non-production cleanup that cannot be used for ordinary or historical records."""
    from app.core.cases import (
        _delete_case_events_for_case_cleanup,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可清理本地冒烟记录")
    record = await db.get(BusinessRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    explicit_test_marker = (
        record.serial_no.startswith("SMOKE-")
        or "SMOKE" in record.title.upper()
        or "冒烟" in record.title
        # UI-driven cross-role acceptance records use this exact, deliberately
        # narrow marker.  It keeps cleanup available for terminal task flows
        # which have no business-page delete action, without admitting normal
        # records that merely contain a generic "验收" label.
        or "UI任务流转验收-" in record.title
        # Contact-edit page evidence uses this equally narrow, fixed UI marker.
        or "UI临时联系人验收-" in record.title
        # Employee-account lifecycle page evidence has no normal physical-delete
        # action: the account must first be offboarded through HR, then this
        # exact local-only marker permits precise acceptance cleanup.
        or "页面验收临时员工" in record.title
        or "SMOKE" in (record.customer or "").upper()
        or "冒烟" in (record.customer or "")
        or record.owner.lower().startswith("smoke_")
        or "smoke_" in json.dumps(record.data or {}, ensure_ascii=False).lower()
        or record.title.startswith("CODEX-")
    )
    if not explicit_test_marker:
        raise HTTPException(status_code=403, detail="只能清理带明确测试标识的本地冒烟记录")
    if record.module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查不能通过通用清理入口删除")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record_id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    if record.module == "case":
        related_tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.data["case_id"].as_integer() == record.id))).all())
        for task in related_tasks:
            await _delete_task_notifications(task.id, db)
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
            await db.delete(task)
        await db.execute(delete(CaseAssistedFee).where(CaseAssistedFee.case_record_id == record.id))
        await _delete_case_events_for_case_cleanup(record.id, db)
        await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == record_id))
    await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == record_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == record_id))
    if record.module == "task":
        await _delete_task_notifications(record_id, db)
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.delete(f"{settings.api_prefix}/testing/agent-documents/{{document_id}}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_smoke_agent_document(document_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Remove explicit smoke-only AI jobs when normal audit retention blocks deletion."""
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可清理本地冒烟智能文档")
    item = await db.get(AgentDocument, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="智能文档任务不存在")
    if "SMOKE" not in item.title.upper() and "冒烟" not in item.title:
        raise HTTPException(status_code=403, detail="只能清理带明确测试标识的本地智能文档")
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

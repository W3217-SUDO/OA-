"""CPC basic patent-application snapshots.

The legacy CPC controller produced a package after its own pre-check.  The
official CPC package specification is not available in this repository, so
this module deliberately produces a clearly labelled basic-information
snapshot instead of claiming CPC filing compatibility.
"""

from __future__ import annotations

from datetime import date, datetime
import io
import json
from pathlib import Path
from typing import Awaitable, Callable
from uuid import uuid4
import zipfile

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import BusinessRecord, FileAttachment, WorkflowEvent
from .security import current_identity


CPC_APPLICATION_CATEGORY = "CPC专利申报信息快照"
CPC_APPLICATION_REMARK = "系统生成：CPC基础申报信息快照（非官方CPC申报格式）"
CPC_APPLICATION_CONTENT_TYPE = "application/zip"
CPC_APPLICATION_FORMAT = "CPC基础申报信息快照（非官方CPC申报格式）"


def is_cpc_application_attachment(item: FileAttachment) -> bool:
    return item.category == CPC_APPLICATION_CATEGORY and item.remark == CPC_APPLICATION_REMARK


def _is_patent_case(record: BusinessRecord) -> bool:
    return str((record.data or {}).get("case_kind") or "").strip().casefold() in {"专利", "patent"}


def _snapshot_content(record: BusinessRecord, generated_by: str) -> bytes:
    data = record.data or {}
    applicant = str(data.get("applicant") or "").strip()
    title = str(record.title or "").strip()
    missing = []
    if not title:
        missing.append("案件名称")
    if not applicant:
        missing.append("申请人")
    if missing:
        raise HTTPException(status_code=422, detail=f"生成CPC基础申报信息前请补充：{'、'.join(missing)}")

    fields = (
        ("文件说明", CPC_APPLICATION_FORMAT),
        ("案件编号", record.serial_no),
        ("发明名称/案件名称", title),
        ("申请人", applicant),
        ("客户", record.customer),
        ("申请号", data.get("application_no") or ""),
        ("申请类型", data.get("application_type") or ""),
        ("申请日", data.get("application_date") or ""),
        ("发明人", data.get("inventor") or ""),
        ("代理人", data.get("agent") or ""),
        ("撰稿人", data.get("writer") or ""),
        ("案件负责人", data.get("case_manager") or record.owner or ""),
        ("生成时间", datetime.now().isoformat(timespec="seconds")),
        ("生成人", generated_by),
    )
    information = ("\n".join(f"{label}：{str(value).strip()}" for label, value in fields) + "\n").encode("utf-8")
    application_fields = {
        key: data.get(key) or ""
        for key in ("applicant", "application_no", "application_type", "application_date", "inventor", "agent", "writer", "case_manager")
    }
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("CPC基础申报信息.txt", information)
        archive.writestr("CPC基础申报信息.json", json.dumps({
            "format": CPC_APPLICATION_FORMAT,
            "case_id": record.id,
            "case_no": record.serial_no,
            "title": record.title,
            "customer": record.customer,
            "application": application_fields,
        }, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    return package.getvalue()


def _public_item(item: FileAttachment, record: BusinessRecord) -> dict:
    return {
        "id": item.id,
        "case_id": record.id,
        "case_no": record.serial_no,
        "original_name": item.original_name,
        "content_type": item.content_type,
        "size": item.size,
        "created_at": item.created_at,
        "created_by": item.uploader,
        "status": "已生成",
        "format": CPC_APPLICATION_FORMAT,
        "download_url": f"{settings.api_prefix}/ipr/cases/{record.id}/cpc-applications/{item.id}/download",
    }


def create_ipr_cpc_router(
    *,
    ensure_visible: Callable[[int, dict, AsyncSession], Awaitable[BusinessRecord]],
    ensure_write: Callable[[int, dict, AsyncSession], Awaitable[BusinessRecord]],
    upload_root: Callable[[], Path],
) -> APIRouter:
    router = APIRouter(tags=["IPR CPC"])

    async def visible_patent_case(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
        record = await ensure_visible(case_id, identity, db)
        if not _is_patent_case(record):
            raise HTTPException(status_code=422, detail="CPC申报仅适用于专利案件")
        return record

    @router.post("/ipr/cases/{case_id}/cpc-applications", status_code=status.HTTP_201_CREATED)
    async def generate_cpc_application(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
        record = await ensure_write(case_id, identity, db)
        if not _is_patent_case(record):
            raise HTTPException(status_code=422, detail="CPC申报仅适用于专利案件")
        content = _snapshot_content(record, identity["username"])
        stored_name = f"{uuid4().hex}.zip"
        target = upload_root() / stored_name
        attachment = FileAttachment(
            record_id=record.id,
            category=CPC_APPLICATION_CATEGORY,
            original_name=f"{record.serial_no}-CPC基础申报信息-{date.today():%Y%m%d}.zip",
            stored_name=stored_name,
            content_type=CPC_APPLICATION_CONTENT_TYPE,
            size=len(content),
            path=str(target),
            uploader=identity["username"],
            remark=CPC_APPLICATION_REMARK,
            document_date=date.today(),
            is_locked=True,
            locked_at=datetime.now(),
            locked_by=identity["username"],
        )
        try:
            target.write_bytes(content)
            db.add(attachment)
            await db.flush()
            db.add(WorkflowEvent(
                record_id=record.id,
                action="生成CPC基础申报信息快照",
                from_status=record.status,
                to_status=record.status,
                operator=identity["username"],
                comment=f"申报记录#{attachment.id}；{CPC_APPLICATION_FORMAT}",
            ))
            await db.commit()
        except Exception:
            await db.rollback()
            target.unlink(missing_ok=True)
            raise
        await db.refresh(attachment)
        return _public_item(attachment, record)

    @router.get("/ipr/cases/{case_id}/cpc-applications")
    async def list_cpc_applications(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
        record = await visible_patent_case(case_id, identity, db)
        items = list((await db.scalars(
            select(FileAttachment).where(
                FileAttachment.record_id == record.id,
                FileAttachment.category == CPC_APPLICATION_CATEGORY,
                FileAttachment.remark == CPC_APPLICATION_REMARK,
            ).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
        )).all())
        return {"items": [_public_item(item, record) for item in items], "total": len(items)}

    @router.get("/ipr/cases/{case_id}/cpc-applications/{application_id}/download")
    async def download_cpc_application(case_id: int, application_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
        record = await visible_patent_case(case_id, identity, db)
        attachment = await db.scalar(select(FileAttachment).where(
            FileAttachment.id == application_id,
            FileAttachment.record_id == record.id,
            FileAttachment.category == CPC_APPLICATION_CATEGORY,
            FileAttachment.remark == CPC_APPLICATION_REMARK,
        ))
        if not attachment:
            raise HTTPException(status_code=404, detail="CPC申报记录不存在或不属于当前案件")
        path = Path(attachment.path)
        if not path.is_file() or upload_root().resolve() not in path.resolve().parents:
            raise HTTPException(status_code=404, detail="CPC申报快照文件不存在")
        return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)

    return router

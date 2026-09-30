"""系统问题反馈与截图附件。"""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UPLOAD_ROOT
from app.core.dependencies import current_identity, get_db, settings
from app.models import BusinessRecord, FileAttachment, User

router = APIRouter()


@router.post(f"{settings.api_prefix}/feedback")
async def create_feedback(
    description: str = Form(...), page: str = Form(""), screenshot: UploadFile | None = File(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    description = description.strip()
    if not 5 <= len(description) <= 2000:
        raise HTTPException(422, "问题描述需填写 5 到 2000 字")
    if len(page) > 500:
        raise HTTPException(422, "页面地址过长")
    content = b""
    suffix = ""
    if screenshot:
        suffix = Path(screenshot.filename or "").suffix.lower()
        content = await screenshot.read(10 * 1024 * 1024 + 1)
        signatures = {
            ".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            ".jpg": content.startswith(b"\xff\xd8\xff"),
            ".jpeg": content.startswith(b"\xff\xd8\xff"),
            ".webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
        }
        if not signatures.get(suffix):
            raise HTTPException(422, "截图仅支持 PNG、JPG 或 WebP 图片")
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "截图不能超过 10MB")
    stored_path = None
    try:
        record = BusinessRecord(
            module="bug_feedback", serial_no=f"BUG{uuid4().hex[:20].upper()}",
            title=description[:100], customer="", status="待处理", owner=identity["username"],
            description=description, data={"page": page.strip()},
        )
        db.add(record)
        await db.flush()
        if screenshot:
            stored_name = f"{uuid4().hex}{suffix}"
            stored_path = UPLOAD_ROOT / stored_name
            stored_path.write_bytes(content)
            db.add(FileAttachment(
                record_id=record.id, category="问题反馈截图", original_name=Path(screenshot.filename or stored_name).name,
                stored_name=stored_name, content_type=screenshot.content_type or "application/octet-stream",
                size=len(content), path=str(stored_path), uploader=identity["username"],
            ))
        await db.commit()
        return {"id": record.id, "serial_no": record.serial_no}
    except Exception:
        await db.rollback()
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise


@router.get(f"{settings.api_prefix}/feedback")
async def list_feedback(
    keyword: str = Query("", max_length=200), page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    conditions = [BusinessRecord.module == "bug_feedback"]
    if "admin" not in identity.get("_actual_role_ids", []):
        conditions.append(BusinessRecord.owner == identity["username"])
    keyword = keyword.strip()
    if keyword:
        conditions.append(or_(
            BusinessRecord.serial_no.icontains(keyword, autoescape=True),
            BusinessRecord.description.icontains(keyword, autoescape=True),
            BusinessRecord.owner.icontains(keyword, autoescape=True),
            User.display_name.icontains(keyword, autoescape=True),
            BusinessRecord.data["page"].as_string().icontains(keyword, autoescape=True),
        ))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).outerjoin(
        User, User.username == BusinessRecord.owner,
    ).where(*conditions))
    has_screenshot = select(FileAttachment.id).where(
        FileAttachment.record_id == BusinessRecord.id,
        FileAttachment.category == "问题反馈截图",
    ).exists()
    records = (await db.execute(select(BusinessRecord, User.display_name, has_screenshot).outerjoin(
        User, User.username == BusinessRecord.owner,
    ).where(*conditions).order_by(
        BusinessRecord.created_at.desc(), BusinessRecord.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all()
    return {"total": total, "page": page, "page_size": page_size, "items": [
        {"id": item.id, "serial_no": item.serial_no, "description": item.description,
         "status": item.status, "owner": item.owner, "page": (item.data or {}).get("page", ""),
         "owner_display_name": display_name or "", "has_screenshot": bool(screenshot_exists),
         "created_at": item.created_at}
        for item, display_name, screenshot_exists in records
    ]}


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}/screenshot")
async def feedback_screenshot(feedback_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    record = await db.get(BusinessRecord, feedback_id)
    if not record or record.module != "bug_feedback" or (
        "admin" not in identity.get("_actual_role_ids", []) and record.owner != identity["username"]
    ):
        raise HTTPException(404, "反馈不存在或无权查看")
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == feedback_id, FileAttachment.category == "问题反馈截图"))
    if not attachment or not Path(attachment.path).is_file():
        raise HTTPException(404, "截图不存在")
    return FileResponse(attachment.path, media_type=attachment.content_type, filename=attachment.original_name)

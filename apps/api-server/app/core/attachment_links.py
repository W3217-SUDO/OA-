"""新建合同/线索/客户/案件时一并挂上已上传的附件（G4）。

只接受本人上传、尚未关联任何业务的附件；挂接时复用原上传入口（同样的权限、类别、案件自动化等），
所以与“先建记录再上传”的两步方式结果一致。原附件保持不动（与 MCP files 参数复用附件的做法相同）。
"""

from io import BytesIO

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers, UploadFile

from app.models import FileAttachment


async def check_unlinked_attachments(attachment_ids: list[int], identity: dict, db: AsyncSession) -> list[FileAttachment]:
    """建记录前先核对，避免记录建好后才发现附件不能用。"""
    items = []
    for attachment_id in dict.fromkeys(int(value) for value in attachment_ids or []):
        item = await db.get(FileAttachment, attachment_id)
        linked = item is not None and any(getattr(item, field) is not None for field in (
            "record_id", "invoice_record_id", "communication_log_id", "law_firm_id", "finance_transaction_id"))
        if item is None or linked or item.uploader != identity["username"]:
            raise HTTPException(422, f"附件 {attachment_id} 不存在、已关联其他业务或不是本人上传；请先上传新附件再引用其 ID")
        items.append(item)
    return items


async def attach_uploaded_files(record_id: int, items: list[FileAttachment], category: str, identity: dict, db: AsyncSession,
                                *, remark: str = "") -> list[dict]:
    from app.areas.system.attachments import upload_attachment
    from app.core.storage import ensure_attachment_local
    results = []
    for item in items:
        path = await ensure_attachment_local(item)
        if path is None or not path.exists():
            raise HTTPException(409, f"附件 {item.id} 的文件不可读取，记录已保存但附件未挂上，请重新上传")
        upload = UploadFile(file=BytesIO(path.read_bytes()), filename=item.original_name,
                            headers=Headers({"content-type": item.content_type or "application/octet-stream"}))
        try:
            results.append(await upload_attachment(
                file=upload, record_id=record_id, finance_transaction_id=None, source_case_id=None, customer_guid=None,
                is_license=None, document_date=item.document_date, category=category, remark=remark or item.remark or "",
                identity=identity, db=db))
        except HTTPException as exc:
            raise HTTPException(exc.status_code, f"记录已保存（ID {record_id}），附件 {item.id} 挂接失败：{exc.detail}；"
                                                 f"已挂上 {len(results)} 个，请勿重复新建，改用附件上传接口补传") from exc
    return results

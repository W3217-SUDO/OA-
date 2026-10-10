"""案件 ONLYOFFICE 路由，独立于既有本地 Word 段落编辑接口。"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas.case_office import OfficeCallbackInput
from app.config import settings
from app.core.case_office_callbacks import handle_office_callback
from app.core.case_office_closing import close_office_session
from app.core.case_office_sessions import change_office_session, create_office_session, open_office_document
from app.core.office_editor import DOCX_CONTENT_TYPE, verify_callback
from app.database import get_db
from app.security import current_identity

router = APIRouter()


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/office-editor/session")
async def start_case_office_session(case_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await create_office_session(case_id, attachment_id, identity["username"], db)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/office-editor/session/{{session_id}}")
async def read_case_office_session(case_id: int, attachment_id: int, session_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await change_office_session(case_id, attachment_id, session_id, identity["username"], db, operation="read")


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/office-editor/session/{{session_id}}/renew")
async def renew_case_office_session(case_id: int, attachment_id: int, session_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await change_office_session(case_id, attachment_id, session_id, identity["username"], db, operation="renew")


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/office-editor/session/{{session_id}}/close")
async def close_case_office_session(case_id: int, attachment_id: int, session_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await close_office_session(case_id, attachment_id, session_id, identity["username"], db)


@router.get(f"{settings.api_prefix}/public/office-editor/document/{{token}}/{{file_name}}")
async def stream_case_office_document(token: str, file_name: str, db: AsyncSession = Depends(get_db)):
    content = await open_office_document(token, file_name, db)
    return Response(content, media_type=DOCX_CONTENT_TYPE, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post(f"{settings.api_prefix}/office-editor/callback/{{case_id}}/{{attachment_id}}/{{session_id}}")
async def save_case_office_callback(case_id: int, attachment_id: int, session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="Office 回调正文过大")
        raw.extend(chunk)
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("invalid callback body")
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(status_code=422, detail="Office 回调正文无效") from exc
    signed = verify_callback(body, request.headers.get("Authorization", ""))
    try:
        callback = OfficeCallbackInput.model_validate(signed)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Office 已签名回调参数无效") from exc
    return await handle_office_callback(case_id, attachment_id, session_id, callback, db)

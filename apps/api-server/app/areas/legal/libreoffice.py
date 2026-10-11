"""OA 会话入口及独立的受签名保护 WOPI 协议路由。"""

import copy
import secrets
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.libreoffice_config import editor_configuration
from app.core.libreoffice_files import DOCX_CONTENT_TYPE, read_document, validate_docx
from app.core.libreoffice_save import put_file, require_wopi_lock
from app.core.libreoffice_security import request_token, verify_proof
from app.core.libreoffice_sessions import close_session, create_session, get_session
from app.core.libreoffice_state import count_request, persist_context, session_context
from app.database import get_db
from app.security import current_identity

router = APIRouter()


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/libreoffice/session")
async def create_libreoffice_session(case_id: int, attachment_id: int,
                                    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await create_session(case_id, attachment_id, identity, db)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/libreoffice/sessions/{{session_id}}")
async def get_libreoffice_session(case_id: int, attachment_id: int, session_id: str,
                                 identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await get_session(case_id, attachment_id, session_id, identity, db)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/libreoffice/sessions/{{session_id}}/close")
async def close_libreoffice_session(case_id: int, attachment_id: int, session_id: str,
                                   identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await close_session(case_id, attachment_id, session_id, identity, db)


async def authenticated_wopi(request: Request, session_id: str, db):
    token, claims = request_token(request, session_id)
    await verify_proof(request, token)
    context = await session_context(claims["case_id"], claims["attachment_id"], session_id,
                                    {"username": claims["sub"]}, db, lock=True)
    if not secrets.compare_digest(context.session["token_id"], claims["jti"]):
        raise HTTPException(status_code=401, detail="WOPI 令牌已撤销")
    # 请求计数和协议状态一起提交，避免同一次请求先释放锁再用旧栅栏写入。
    count_request(context)
    return context


@router.get(f"{settings.api_prefix}/office/wopi/files/{{session_id}}")
async def check_file_info(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    context = await authenticated_wopi(request, session_id, db)
    context.session["engine_started"] = True
    if context.session["status"] == "opening":
        context.session["status"] = "active"
    await persist_context(context, db)
    return {"BaseFileName": context.item.original_name, "OwnerId": context.item.uploader,
            "Size": context.session["size"], "UserId": context.identity["username"],
            "UserFriendlyName": context.identity["display_name"], "Version": context.session["version"],
            "LastModifiedTime": context.session["modified_at"], "UserCanWrite": True,
            "ReadOnly": False, "UserCanNotWriteRelative": True, "SupportsUpdate": True,
            "SupportsLocks": True, "SupportsGetLock": True, "SupportsRename": False,
            "UserCanRename": False, "PostMessageOrigin": editor_configuration()["frontend"]}


@router.get(f"{settings.api_prefix}/office/wopi/files/{{session_id}}/contents")
async def get_file(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    context = await authenticated_wopi(request, session_id, db)
    expected = request.headers.get("x-wopi-maxexpectedsize")
    if expected is not None:
        try:
            limit = int(expected)
            if limit < 0:
                raise ValueError("negative size")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="WOPI 最大读取大小无效") from exc
        if context.session["size"] > limit:
            raise HTTPException(status_code=412, detail="文件超过客户端期望大小")
    snapshot = SimpleNamespace(**{name: getattr(context.item, name) for name in ("path", "stored_name", "original_name")})
    await persist_context(context, db)
    previous = copy.deepcopy(context.session)
    identity = context.identity
    await db.rollback()
    content = await read_document(snapshot)
    if validate_docx(content) != previous["version"]:
        raise HTTPException(status_code=409, detail="附件内容与登记版本不一致")
    context = await session_context(previous["case_id"], previous["attachment_id"], session_id, identity, db)
    if context.session["version"] != previous["version"]:
        raise HTTPException(status_code=409, detail="读取期间附件版本已变化")
    return Response(content, media_type=DOCX_CONTENT_TYPE,
                    headers={"X-WOPI-ItemVersion": previous["version"], "Cache-Control": "no-store"})


@router.post(f"{settings.api_prefix}/office/wopi/files/{{session_id}}")
async def change_file_lock(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    context = await authenticated_wopi(request, session_id, db)
    operation = request.headers.get("x-wopi-override", "")
    value = request.headers.get("x-wopi-lock", "")
    current = context.session["wopi_lock"]
    if operation == "GET_LOCK":
        await persist_context(context, db)
        return Response(status_code=200, headers={"X-WOPI-Lock": current})
    if operation not in {"LOCK", "REFRESH_LOCK", "UNLOCK"}:
        raise HTTPException(status_code=501, detail="未开放该 WOPI 写操作")
    if not value or len(value) > 256 or not value.isascii() or any(ord(char) < 32 for char in value):
        raise HTTPException(status_code=400, detail="WOPI 锁标识无效")
    old = request.headers.get("x-wopi-oldlock")
    if operation == "LOCK":
        if (old is not None and old != current) or (old is None and current and current != value):
            raise HTTPException(status_code=409, detail="文件已被另一 WOPI 锁占用", headers={"X-WOPI-Lock": current})
        context.session["wopi_lock"] = value
        context.session["engine_started"] = True
        if context.session["status"] == "opening":
            context.session["status"] = "active"
    else:
        require_wopi_lock(context, value)
    if operation == "UNLOCK":
        if context.session["pending"] or context.session["save_status"] == "error":
            raise HTTPException(status_code=409, detail="保存尚未确认，不能解锁", headers={"X-WOPI-Lock": current})
        context.session["wopi_lock"] = ""
        context.session["status"] = "closed"
    await persist_context(context, db, release=operation == "UNLOCK")
    return Response(status_code=200)


@router.post(f"{settings.api_prefix}/office/wopi/files/{{session_id}}/contents")
async def save_file(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    context = await authenticated_wopi(request, session_id, db)
    if request.headers.get("x-wopi-override") != "PUT":
        raise HTTPException(status_code=501, detail="文件内容入口仅支持 WOPI PUT")
    result, version = await put_file(context, request, db)
    return JSONResponse(result, headers={"X-WOPI-ItemVersion": version})

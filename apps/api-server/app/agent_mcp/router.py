"""前端专用的工具目录、人工决定和受保护结果下载入口。"""

import asyncio
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from app.agent_mcp.artifacts import read_resource
from app.agent_attachment_reader import read_attachment
from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.service import decide_tool_request, get_tool_request, list_tool_requests, public_tool
from app.areas.system.attachments import upload_attachment
from app.core.storage import _attachment_storage_path
from app.data_models.documents import FileAttachment
from app.config import settings
from app.database import get_db
from app.security import current_identity


router = APIRouter(prefix=settings.api_prefix + "/agent-tools", tags=["智能体工具人工确认"])


class ToolDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=1000)


@router.post("/upload", status_code=201)
async def upload_agent_attachment(
    file: UploadFile = File(...), record_id: int | None = Form(None),
    finance_transaction_id: int | None = Form(None), source_case_id: int | None = Form(None),
    customer_guid: str | None = Form(None), is_license: bool | None = Form(None),
    document_date: date | None = Form(None), category: str = Form("个人智能体材料"),
    remark: str = Form(""), identity=Depends(current_identity), db=Depends(get_db),
):
    """接收真实 multipart 文件并复用原附件存储，返回可供 MCP files 分组引用的 ID。"""
    # 该路由仅接受 UploadFile；不能把本地路径、URL 或文件内容字符串当作附件。
    if any(value is not None for value in (
        record_id, finance_transaction_id, source_case_id, customer_guid, is_license, document_date,
    )):
        raise HTTPException(status_code=422, detail="MCP 直接上传仅用于准备未关联附件；业务关联必须在 oa_call_tool 人工确认后完成")
    attachment = await upload_attachment(
        file=file, record_id=record_id, finance_transaction_id=finance_transaction_id,
        source_case_id=source_case_id, customer_guid=customer_guid, is_license=is_license,
        document_date=document_date, category=category, remark=remark,
        identity=identity, db=db,
    )
    reading: dict[str, object]
    item = await db.get(FileAttachment, int(attachment["id"]))
    path = _attachment_storage_path(item) if item else None
    if item is None or path is None:
        reading = {"status": "unavailable", "cache_hit": False, "cache_status": "disabled", "detail": "附件已保存，但当前存储位置不可读取"}
    else:
        try:
            result = await asyncio.to_thread(
                read_attachment, path, item.original_name,
                cache_scope=identity["username"], attachment_id=item.id,
            )
            reading = {
                "status": result.status, "cache_hit": result.cache_hit,
                "cache_status": result.cache_status, "page_count": result.page_count,
                "content_chars": len(result.text), "image_count": len(result.images),
                "content_sha256": result.content_sha256, "content_size": result.content_size,
            }
            if result.status not in {"parsed", "visual"} or not (result.text or result.images):
                reading["detail"] = "附件已保存，但无法读取正文或页面图像"
        except Exception:
            reading = {"status": "failed", "cache_hit": False, "cache_status": "failed", "detail": f"附件已保存，但解析失败：{item.original_name}，请检查文件是否完整或加密"}
    return {
        "attachment_id": attachment["id"],
        "attachment": attachment,
        "reading": reading,
        "next_mcp_files_argument": {"files": {"file": attachment["id"]}},
    }


@router.get("/catalog")
async def tool_catalog(_=Depends(current_identity)):
    catalog = get_catalog(get_auth_context().application)
    tools = [public_tool(spec) for spec in catalog.tools]
    grouped: dict[str, list[str]] = {}
    for tool in tools:
        grouped.setdefault(tool["domain"], []).append(tool["name"])
    return {
        "tools": tools,
        "groups": [
            {"domain": domain, "tool_count": len(names), "tool_names": names}
            for domain, names in sorted(grouped.items())
        ],
        "inventory": catalog.inventory(),
        "mcp_endpoint": settings.api_prefix + "/mcp",
    }


@router.get("/requests")
async def tool_requests(
    status: str = "pending", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity=Depends(current_identity), db=Depends(get_db),
):
    return await list_tool_requests(identity, db, status=status, page=page, page_size=page_size)


@router.get("/requests/{request_id}")
async def tool_request(request_id: str, identity=Depends(current_identity), db=Depends(get_db)):
    return await get_tool_request(request_id, identity, db)


@router.post("/requests/{request_id}/decision")
async def tool_request_decision(
    request_id: str, body: ToolDecisionInput, identity=Depends(current_identity), db=Depends(get_db),
):
    return await decide_tool_request(request_id, body.decision, identity, db, comment=body.comment)


async def _download(resource_id: str, kind: str):
    metadata, content = await read_resource(resource_id, expected_kind=kind)
    return Response(
        content, media_type=metadata["mime_type"],
        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(metadata["name"], safe=""),
                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/artifacts/{artifact_id}")
async def download_tool_artifact(artifact_id: str, _=Depends(current_identity)):
    return await _download(artifact_id, "artifact")


@router.get("/resources/{resource_id}")
async def download_tool_resource(resource_id: str, _=Depends(current_identity)):
    return await _download(resource_id, "source")


class AccessTokenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    days: int = Field(default=30, ge=1, le=90)


def _require_admin(identity: dict) -> None:
    from app.agent_permissions import can_use_mcp_personal_token
    if not can_use_mcp_personal_token(identity):
        raise HTTPException(403, "该账号没有使用 MCP 个人访问令牌的授权")


@router.get("/access-tokens")
async def access_token_list(request: Request, identity=Depends(current_identity), db=Depends(get_db)):
    _require_admin(identity)
    from app.agent_mcp import personal_tokens
    from app.agent_mcp.personal_tokens import token_tool_allowed
    from app.agent_mcp.tool_groups import BUSINESS_BUNDLES
    from app.agent_permissions import can_write_with_mcp_token
    tools = [spec for spec in get_catalog(request.app).tools if token_tool_allowed(spec) and (can_write_with_mcp_token(identity) or not spec.is_write)]
    businesses = [{"key": key, "label": label, "tool_count": sum(1 for spec in tools if spec.group_id in groups)}
                  for key, (label, groups) in BUSINESS_BUNDLES.items()]
    return {"items": await personal_tokens.list_tokens(identity, db), "can_write": can_write_with_mcp_token(identity), "businesses": businesses,
            "calls": await personal_tokens.list_calls(identity, db),
            "mcp_endpoint": settings.api_prefix + "/mcp",
            "max_days": personal_tokens.MAX_DAYS, "rate_limit_per_minute": personal_tokens.RATE_LIMIT_PER_MINUTE}


@router.post("/access-tokens", status_code=201)
async def access_token_create(body: AccessTokenInput, identity=Depends(current_identity), db=Depends(get_db)):
    _require_admin(identity)
    from app.agent_mcp import personal_tokens
    return await personal_tokens.create_token(identity, db, body.name, body.days)


@router.delete("/access-tokens/{token_id}")
async def access_token_revoke(token_id: int, identity=Depends(current_identity), db=Depends(get_db)):
    _require_admin(identity)
    from app.agent_mcp import personal_tokens
    return await personal_tokens.revoke_token(identity, db, token_id)

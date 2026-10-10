"""前端专用的工具目录、人工决定和受保护结果下载入口。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from app.agent_mcp.artifacts import read_resource
from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.service import decide_tool_request, get_tool_request, list_tool_requests, public_tool
from app.config import settings
from app.database import get_db
from app.security import current_identity


router = APIRouter(prefix=settings.api_prefix + "/agent-tools", tags=["智能体工具人工确认"])


class ToolDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=1000)


@router.get("/catalog")
async def tool_catalog(_=Depends(current_identity)):
    catalog = get_catalog(get_auth_context().application)
    return {"tools": [public_tool(spec) for spec in catalog.tools], "inventory": catalog.inventory(),
            "mcp_endpoint": settings.api_prefix + "/mcp"}


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

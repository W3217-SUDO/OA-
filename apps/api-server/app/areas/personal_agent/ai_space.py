"""个人 AI 空间专用接口；保存只由前端人工确认入口发起。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from app.agent_mcp.config import origin_allowed
from app.config import settings
from app.database import get_db
from app.security import current_identity
from app.areas.personal_agent.ai_space_service import (
    list_space_files, save_space_message, space_file_bytes, space_file_record, space_info,
)
from app.core.generated_file_records import generated_file_item


router = APIRouter(prefix=settings.api_prefix + "/personal-agent/ai-space", tags=["个人AI空间"])


class PersonalFileSaveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str = Field(min_length=1, max_length=64)
    message_index: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=255)
    expected_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class PersonalFileEditInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(max_length=2_000_000)


class PersonalOfficeOpenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class PersonalOfficeSaveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(pattern=r"^[a-f0-9]{32}$")


@router.get("")
async def get_personal_ai_space(owner_user_id: int | None = Query(None, ge=1),
                                identity=Depends(current_identity), db=Depends(get_db)):
    return await space_info(identity, db, owner_user_id)


@router.get("/files")
async def get_personal_ai_files(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                                owner_user_id: int | None = Query(None, ge=1),
                                identity=Depends(current_identity), db=Depends(get_db)):
    return await list_space_files(identity, db, page=page, page_size=page_size, owner_user_id=owner_user_id)


@router.get("/files/{file_id}")
async def get_personal_ai_file(file_id: str = Path(pattern=r"^[a-f0-9]{32}$"),
                               identity=Depends(current_identity), db=Depends(get_db)):
    return generated_file_item(await space_file_record(file_id, identity, db))


@router.get("/files/{file_id}/download")
async def download_personal_ai_file(file_id: str = Path(pattern=r"^[a-f0-9]{32}$"),
                                    identity=Depends(current_identity), db=Depends(get_db)):
    item, content = await space_file_bytes(file_id, identity, db)
    return Response(content, media_type=item["content_type"], headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(item["name"], safe=""),
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


@router.get("/files/{file_id}/content")
async def get_personal_ai_file_content(file_id: str = Path(pattern=r"^[a-f0-9]{32}$"),
                                       identity=Depends(current_identity), db=Depends(get_db)):
    from app.areas.personal_agent.ai_space_service import space_file_text

    return await space_file_text(file_id, identity, db)


@router.post("/files/{file_id}/edit", status_code=201)
async def edit_personal_ai_file(body: PersonalFileEditInput, file_id: str = Path(pattern=r"^[a-f0-9]{32}$"),
                                identity=Depends(current_identity), db=Depends(get_db)):
    from app.areas.personal_agent.ai_space_service import edit_space_file

    return await edit_space_file(file_id, body.name, body.content, identity, db)


@router.post("/files", status_code=201)
async def save_personal_ai_file(body: PersonalFileSaveInput, request: Request,
                                identity=Depends(current_identity), db=Depends(get_db)):
    if request.headers.get("x-oa-agent-confirmation") != "frontend" or not origin_allowed(request.headers.get("origin", "")):
        raise HTTPException(403, "请在 OA 前端确认保存，来源或人工确认标识无效")
    return await save_space_message(body, identity, db)


def _require_office_confirmation(request: Request):
    if request.headers.get("x-oa-agent-confirmation") != "frontend" or not origin_allowed(request.headers.get("origin", "")):
        raise HTTPException(403, "请在 OA 前端确认钉钉文件操作，来源或人工确认标识无效")


@router.post("/files/{file_id}/office/open")
async def open_personal_office_file(body: PersonalOfficeOpenInput, request: Request,
                                    file_id: str = Path(pattern=r"^[a-f0-9]{32}$"),
                                    identity=Depends(current_identity), db=Depends(get_db)):
    from app.areas.personal_agent.dingtalk_office_service import start_office_edit

    _require_office_confirmation(request)
    return await start_office_edit(file_id, body.expected_sha256, identity, db)


@router.post("/files/{file_id}/office/save", status_code=201)
async def save_personal_office_file(body: PersonalOfficeSaveInput, request: Request,
                                    file_id: str = Path(pattern=r"^[a-f0-9]{32}$"),
                                    identity=Depends(current_identity), db=Depends(get_db)):
    from app.areas.personal_agent.dingtalk_office_service import save_office_edit

    _require_office_confirmation(request)
    return await save_office_edit(file_id, body.session_id, identity, db)

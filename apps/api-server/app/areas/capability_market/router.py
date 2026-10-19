"""能力市场只读查询、人工安装与受控参考资料读取。"""
from typing import Literal
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.global_agent_skills import can_manage_global
from app.agent_permissions import require_agent_settings_management
from app.security import current_identity
from .catalog import catalog, definition, entry, install, installed_records, public_entry, summary
from .connector_routes import router as connector_router
from .connector_store import connection_states


router = APIRouter(prefix=settings.api_prefix + "/capability-market", tags=["能力中心"])
router.include_router(connector_router)


class InstallInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Literal["personal", "global"] = "personal"
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.get("")
async def capability_catalog(scope: Literal['personal', 'global'] = 'personal', identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    records = await installed_records(identity, db)
    connections = await connection_states(scope, identity, db)
    return {"items": [{**public_entry(item), "installed": [{"id": record["id"],
                "scope": "global" if record["id"].startswith("global-") else "personal"}
                for record in records if record.get("source") == item["source"]],
                "connection": connections.get(item['id'])} for item in catalog()["items"]],
            "source_commit": catalog()["source_commit"], "can_manage_global": can_manage_global(identity),
            "archive_counts": catalog().get("archive_counts")}


@router.get("/items/{item_id}")
async def capability_definition(item_id: str, _=Depends(current_identity)):
    item = entry(item_id)
    return {**public_entry(item), "instruction": definition(item)["instruction"],
            "resources": list(item["resources"]), "license_documents": item["license_documents"],
            "connection_configs": item.get("connection_configs", {}), "excluded_resources": item.get("excluded_resources", [])}


@router.get("/avatars/{item_id}")
async def capability_avatar(item_id: str, _=Depends(current_identity)):
    item = summary(item_id)
    filename = item.get("avatar_file")
    if filename not in {item_id + suffix for suffix in (".png", ".jpg", ".jpeg")}:
        raise HTTPException(404, "此能力包没有已登记头像")
    content = (Path(settings.capability_catalog_path).parent / "avatars" / filename).read_bytes()
    if hashlib.sha256(content).hexdigest() != item["avatar_sha256"]:
        raise HTTPException(409, "头像内容与导入摘要不同")
    return Response(content, media_type="image/png" if filename.endswith(".png") else "image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})


@router.post("/items/{item_id}/install")
async def install_capability(item_id: str, body: InstallInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if body.scope == "global":
        require_agent_settings_management(identity)
    item = entry(item_id)
    if item["sha256"] != body.sha256:
        raise HTTPException(409, "能力包已变化，请重新查看详情再安装")
    return await install(item, body.scope, identity, db)


@router.get("/resources/{item_id}", summary="读取能力包参考资料")
async def read_capability_resource(item_id: str, path: str = Query(min_length=1, max_length=500),
                                   offset: int = Query(default=0, ge=0), limit: int = Query(default=6000, ge=1, le=16000),
                                   identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    item = entry(item_id)
    if not any(record.get("source") == item["source"] for record in await installed_records(identity, db)):
        raise HTTPException(403, "请先安装并启用此能力包，才能读取其参考资料")
    if path not in item["resources"]:
        raise HTTPException(404, "资料不存在或不属于允许读取的文本资源")
    text = item["resources"][path]
    if offset > len(text):
        raise HTTPException(422, "读取偏移超出资料长度")
    end = min(offset + limit, len(text))
    return {"item_id": item_id, "path": path, "content": text[offset:end], "source": item["source"],
            "offset": offset, "next_offset": end if end < len(text) else None, "total_characters": len(text)}

"""Global management and scope-specific definition access."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas.agents import UserAgentSkillInput, UserAgentSkillUpdate
from app.areas.personal_agent.router import GitHubSkillInstallInput, GitHubSkillPreviewInput
from app.config import settings
from app.database import get_db
from app.global_agent_skills import (
    add_global_skill, can_manage_global, global_skill_record, global_skill_store,
    require_global_admin, save_global_skills,
)
from app.security import current_identity
from app.skill_definitions import skill_definition
from app.user_agent_skills import CUSTOM_SKILL_FILE_LIMIT, custom_skill_public, normalize_custom_skill, parse_uploaded_skill

router = APIRouter()


class GlobalSkillInput(UserAgentSkillInput):
    model_config = ConfigDict(extra="forbid")


class GlobalSkillUpdate(UserAgentSkillUpdate):
    model_config = ConfigDict(extra="forbid")


def formatted(record):
    return {**custom_skill_public(record), "scope": "global"}


@router.get(settings.api_prefix + "/agent/global-skills")
async def list_global_skills(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _, records = await global_skill_store(db)
    manager = can_manage_global(identity)
    return {"items": [formatted(record) for record in records if manager or record.get("enabled", True)],
            "scope": "global", "can_manage": manager}


@router.post(settings.api_prefix + "/agent/global-skills")
async def create_global_skill(body: GlobalSkillInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    require_global_admin(identity)
    try:
        record = await add_global_skill(body.model_dump(), identity, db)
    except ValueError as exc:
        raise HTTPException(422, f"技能字段格式不正确：{exc}") from exc
    return formatted(record)


@router.post(settings.api_prefix + "/agent/global-skills/upload")
async def upload_global_skill(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    require_global_admin(identity)
    content = await file.read(CUSTOM_SKILL_FILE_LIMIT + 1)
    try:
        parsed = parse_uploaded_skill(file.filename or "", content)
        record = await add_global_skill(parsed, identity, db, source=parsed["source"])
    except ValueError as exc:
        raise HTTPException(422, f"技能文件格式不正确：{exc}") from exc
    return formatted(record)


@router.post(settings.api_prefix + "/agent/global-skills/github/preview")
async def preview_global_github(body: GitHubSkillPreviewInput, identity: dict = Depends(current_identity)):
    require_global_admin(identity)
    from app.github_agent_skills import preview_github_skill
    return await preview_github_skill(body.url)


@router.post(settings.api_prefix + "/agent/global-skills/github/install")
async def install_global_github(body: GitHubSkillInstallInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    require_global_admin(identity)
    from app.github_agent_skills import preview_github_skill
    preview = await preview_github_skill(body.url)
    if preview["sha256"] != body.sha256:
        raise HTTPException(409, "GitHub技能内容已变化，请重新预览后安装")
    record = await add_global_skill({**preview, "category": "GitHub"}, identity, db,
                                    source=preview["source"], digest=preview["sha256"])
    return formatted(record)


@router.patch(settings.api_prefix + "/agent/global-skills/{skill_id}")
async def update_global_skill(skill_id: str, body: GlobalSkillUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    require_global_admin(identity)
    item, records = await global_skill_store(db, lock=True)
    index = next((index for index, record in enumerate(records) if record["id"] == skill_id), -1)
    if index < 0:
        raise HTTPException(404, "全局技能不存在")
    existing = records[index]
    try:
        records[index] = normalize_custom_skill({**existing, **body.model_dump(exclude_unset=True)},
                                               skill_id=skill_id, source=existing["source"])
    except ValueError as exc:
        raise HTTPException(422, f"技能字段格式不正确：{exc}") from exc
    await save_global_skills(item, records, identity, db)
    return formatted(records[index])


@router.delete(settings.api_prefix + "/agent/global-skills/{skill_id}")
async def delete_global_skill(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    require_global_admin(identity)
    item, records = await global_skill_store(db, lock=True)
    retained = [record for record in records if record["id"] != skill_id]
    if len(retained) == len(records):
        raise HTTPException(404, "全局技能不存在")
    await save_global_skills(item, retained, identity, db)
    return {"deleted": True, "skill_id": skill_id}


async def personal_record(skill_id, identity, db):
    from app.core.documents import _user_agent_skill_store
    _, records = await _user_agent_skill_store(identity["username"], db)
    record = next((record for record in records if record["id"] == skill_id), None)
    if record is None:
        raise HTTPException(404, "个人技能不存在或不属于当前账号")
    return record


@router.get(settings.api_prefix + "/agent/skills/personal")
async def personal_skills(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import _user_agent_skill_store
    _, records = await _user_agent_skill_store(identity["username"], db)
    return {"items": [custom_skill_public(record) for record in records], "scope": "personal"}


def downloaded(definition):
    return Response(definition["content"].encode("utf-8"), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="{definition["filename"]}"',
                             "X-Definition-SHA256": definition["definition_sha256"]})


@router.get(settings.api_prefix + "/agent/skills/{skill_id}/definition")
async def personal_definition(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return skill_definition(await personal_record(skill_id, identity, db), "personal")


@router.get(settings.api_prefix + "/agent/skills/{skill_id}/definition/download")
async def personal_download(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return downloaded(await personal_definition(skill_id, identity, db))


@router.get(settings.api_prefix + "/agent/global-skills/{skill_id}/definition")
async def global_definition(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return skill_definition(await global_skill_record(skill_id, identity, db), "global")


@router.get(settings.api_prefix + "/agent/global-skills/{skill_id}/definition/download")
async def global_download(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return downloaded(await global_definition(skill_id, identity, db))

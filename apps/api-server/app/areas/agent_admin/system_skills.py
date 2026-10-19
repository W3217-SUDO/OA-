"""系统技能声明查看和注销接口。"""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.security import current_identity
from app.system_agent_skills import delete_system_skill, system_skill_detail

router = APIRouter()


class SystemSkillDeleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm: Literal[True]
    revision: int = Field(ge=0)
    definition_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.get(settings.api_prefix + "/agent/system-skills/{skill_id}/definition")
async def get_system_skill(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await system_skill_detail(skill_id, identity, db)


@router.delete(settings.api_prefix + "/agent/system-skills/{skill_id}")
async def remove_system_skill(skill_id: str, body: SystemSkillDeleteInput,
                              identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await delete_system_skill(skill_id, body, identity, db)

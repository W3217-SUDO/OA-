"""系统技能声明查看和注销接口。"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.security import current_identity
from app.system_agent_skills import delete_system_skill, require_active_system_skill, system_skill_detail
from app.system_skill_packages import read_package_resource

router = APIRouter()


@router.get(settings.api_prefix + "/agent/system-skills/{skill_id}/resources", summary="读取系统技能参考资料")
async def read_system_skill_resource(
    skill_id: str, path: str = Query(min_length=1, max_length=500, description="选中技能原文列出的配套资料相对路径，不是服务器路径"),
    offset: int = Query(default=0, ge=0, description="从0开始的字符偏移；续读使用上一页 next_offset"),
    limit: int = Query(default=6000, ge=1, le=16000, description="本次读取字符数，最大16000；未读完时继续分页"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """仅读取当前未注销系统技能的固定版本原文资料；不安装、执行脚本或访问案件数据。

    skill_id 使用本轮选中系统技能的标识，path 使用其指令中列出的准确路径。
    """
    await require_active_system_skill(skill_id, db)
    return read_package_resource(skill_id, path, offset, limit)


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

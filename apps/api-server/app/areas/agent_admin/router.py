from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_skills import public_skill_catalog
from app.config import settings
from app.core.constants import case_agent_runtime
from app.core.permissions import _require_admin
from app.database import get_db
from app.models import SystemConfig, User
from app.security import current_identity
from app.user_agent_skills import USER_SKILL_CONFIG_GROUP, USER_SKILL_CONFIG_PREFIX


router = APIRouter()


@router.get(f"{settings.api_prefix}/agent-admin/overview")
async def agent_admin_overview(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """智能体运行状态、系统技能目录，以及每个账号保存的个人技能。"""
    _require_admin(identity)
    libraries = (await db.scalars(select(SystemConfig).where(
        SystemConfig.group == USER_SKILL_CONFIG_GROUP,
        SystemConfig.key.startswith(USER_SKILL_CONFIG_PREFIX, autoescape=True),
    ).order_by(SystemConfig.updated_at.desc()))).all()
    usernames = [str((item.value or {}).get("owner_username") or "") for item in libraries]
    display_names = dict((await db.execute(select(User.username, User.display_name).where(User.username.in_(usernames)))).all())
    runtime = case_agent_runtime.status()
    runtime.pop("skills", None)
    return {
        "runtime": runtime,
        "system_skills": public_skill_catalog(),
        "user_libraries": [
            {
                "username": username,
                "display_name": display_names.get(username, ""),
                "skills": [
                    {"id": skill.get("id"), "name": skill.get("name"), "category": skill.get("category"), "enabled": bool(skill.get("enabled", True))}
                    for skill in (item.value or {}).get("skills") or [] if isinstance(skill, dict)
                ],
            }
            for username, item in zip(usernames, libraries)
        ],
    }

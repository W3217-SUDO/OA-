from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.system_agent_skills import active_system_skills
from app.config import settings
from app.core.constants import case_agent_runtime
from app.agent_permissions import is_actual_system_admin, require_agent_settings_management
from app.database import get_db
from app.models import SystemConfig, User
from app.security import current_identity
from app.user_agent_skills import USER_SKILL_CONFIG_GROUP, USER_SKILL_CONFIG_PREFIX
from app.areas.agent_admin.skills import router as skills_router
from app.areas.agent_admin.system_skills import router as system_skills_router
from app.areas.capability_market.router import router as capability_router


router = APIRouter()
router.include_router(skills_router)
router.include_router(system_skills_router)
router.include_router(capability_router)


@router.get(f"{settings.api_prefix}/agent-admin/overview")
async def agent_admin_overview(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """智能体运行状态、系统技能目录，以及每个账号保存的个人技能。"""
    require_agent_settings_management(identity)
    runtime = case_agent_runtime.status()
    runtime.pop("skills", None)
    system_skills = await active_system_skills(db)
    runtime["skill_count"] = len(system_skills)
    overview = {
        "runtime": runtime,
        "system_skills": system_skills,
        "can_manage_global": True,
        "can_view_user_libraries": is_actual_system_admin(identity),
        "user_libraries": [],
    }
    # 委派管理不读取或返回其他员工账号及其个人技能库。
    if not overview["can_view_user_libraries"]:
        return overview
    libraries = (await db.scalars(select(SystemConfig).where(
        SystemConfig.group == USER_SKILL_CONFIG_GROUP,
        SystemConfig.key.startswith(USER_SKILL_CONFIG_PREFIX, autoescape=True),
    ).order_by(SystemConfig.updated_at.desc()))).all()
    # 返回全部有效账号，管理员才能确认哪些账号尚未创建个人技能库；技能记录仍只从归属校验通过的配置中读取。
    users = (await db.execute(
        select(User.username, User.display_name)
        .where(User.is_active.is_(True))
        .order_by(User.username.asc())
    )).all()
    library_by_username: dict[str, list] = {}
    for item in libraries:
        owner_key = str((item.value or {}).get("owner_username") or "").strip().casefold()
        if owner_key and owner_key not in library_by_username:
            library_by_username[owner_key] = (item.value or {}).get("skills") or []
    return {
        **overview,
        "user_libraries": [
            {
                "username": username,
                "display_name": display_name or username,
                "skills": [
                    {"id": skill.get("id"), "name": skill.get("name"), "category": skill.get("category"), "enabled": bool(skill.get("enabled", True))}
                    for skill in library_by_username.get(username.casefold(), [])
                    if isinstance(skill, dict)
                ],
            }
            for username, display_name in users
        ],
    }

"""系统内联技能的活动注册、详情和持久化注销；不修改不可变源码。"""
from dataclasses import asdict

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.agent_permissions import require_agent_settings_management
from app.agent_skills import AGENT_SKILLS, SKILLS_BY_ID
from app.models import SystemConfig
from app.skill_definitions import skill_definition

SYSTEM_SKILL_CONFIG_KEY = "agent_system_skills_v1"


async def system_skill_registry(db):
    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == SYSTEM_SKILL_CONFIG_KEY)
                           .execution_options(populate_existing=True))
    if item is None:
        return None, {"schema_version": 1, "revision": 0, "deleted_ids": []}
    value = item.value
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or type(value.get("revision")) is not int or value["revision"] < 1
            or not isinstance(value.get("deleted_ids"), list)
            or any(not isinstance(key, str) for key in value["deleted_ids"])
            or len(set(value["deleted_ids"])) != len(value["deleted_ids"])):
        raise HTTPException(409, "系统技能注册信息无效，请由管理员核对")
    return item, value


async def active_system_skills(db):
    _, value = await system_skill_registry(db)
    return [{**skill.public_dict(), "scope": "system"} for skill in AGENT_SKILLS
            if skill.id not in value["deleted_ids"]]


async def require_active_system_skill(skill_id, db):
    skill = SKILLS_BY_ID.get(skill_id)
    if skill is None:
        raise HTTPException(404, "系统技能不存在")
    _, value = await system_skill_registry(db)
    if skill_id in value["deleted_ids"]:
        raise HTTPException(409, "该系统技能已删除，请清空技能选择或重新选择")
    return skill


async def runtime_system_skill(skill_id):
    from app.database import SessionLocal
    async with SessionLocal() as db:
        return await require_active_system_skill(skill_id, db)


def definition_hash(skill):
    return skill_definition(asdict(skill), "system")["definition_sha256"]


async def system_skill_detail(skill_id, identity, db):
    require_agent_settings_management(identity)
    skill = await require_active_system_skill(skill_id, db)
    _, value = await system_skill_registry(db)
    return {**skill.public_dict(), **skill_definition(asdict(skill), "system"), "instruction": skill.instruction,
            "content_origin": "runtime_declaration", "resources": [], "can_delete": True,
            "revision": value["revision"], "definition_sha256": definition_hash(skill)}


async def delete_system_skill(skill_id, body, identity, db):
    require_agent_settings_management(identity)
    skill = await require_active_system_skill(skill_id, db)
    item, value = await system_skill_registry(db)
    if body.revision != value["revision"] or body.definition_sha256 != definition_hash(skill):
        raise HTTPException(409, "系统技能内容或注册版本已变化，请重新查看后确认")
    replacement = {"schema_version": 1, "revision": value["revision"] + 1,
                   "deleted_ids": [*value["deleted_ids"], skill_id]}
    from app.core.system import _system_audit
    try:
        if item is None:
            db.add(SystemConfig(key=SYSTEM_SKILL_CONFIG_KEY, label="系统技能活动注册", group="智能体",
                value=replacement, description="专用接口持久化注销系统技能，不删除源码", updated_by=identity["username"]))
            await db.flush()
        else:
            # 按注册版本比较，兼容 PostgreSQL JSON 列并阻断并发覆盖。
            result = await db.execute(update(SystemConfig).where(
                SystemConfig.key == SYSTEM_SKILL_CONFIG_KEY,
                SystemConfig.value["revision"].as_integer() == value["revision"],
            ).values(value=replacement, updated_by=identity["username"]).execution_options(synchronize_session=False))
            if result.rowcount != 1:
                raise HTTPException(409, "系统技能注册版本已变化，请刷新后确认")
        await _system_audit(db, identity, "删除系统技能注册", skill.name,
                            {"skill_id": skill_id, "revision": replacement["revision"],
                             "definition_sha256": definition_hash(skill), "deletion_mode": "registry_deactivation"})
        await db.commit()
        db.expire_all()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "系统技能注册刚被更新，请刷新后确认") from exc
    except Exception:
        await db.rollback()
        raise
    return {"id": skill_id, "scope": "system", "deleted": True,
            "deletion_mode": "registry_deactivation", "revision": replacement["revision"]}

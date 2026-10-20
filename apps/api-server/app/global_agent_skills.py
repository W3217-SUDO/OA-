"""Administrator-managed global definitions, separate from every personal library."""
from uuid import uuid4
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import SystemConfig
from app.agent_permissions import can_manage_agent_settings, require_agent_settings_management
from app.user_agent_skills import CUSTOM_SKILL_LIMIT, normalize_custom_skill

GLOBAL_SKILL_CONFIG_KEY = "agent_global_skills_v1"


def require_global_admin(identity):
    from app.core.permissions import _require_actual_system_admin
    _require_actual_system_admin(identity)


def can_manage_global(identity):
    return can_manage_agent_settings(identity)


async def global_skill_store(db, *, lock=False):
    query = select(SystemConfig).where(SystemConfig.key == GLOBAL_SKILL_CONFIG_KEY)
    item = await db.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    if item is None:
        return None, []
    value = item.value or {}
    if value.get("schema_version") != 1 or value.get("scope") != "global" or not isinstance(value.get("skills"), list):
        raise HTTPException(409, "全局技能库结构无效，请由管理员核对")
    records = value["skills"]
    if any(not isinstance(record, dict) or not re.fullmatch(r"global-[a-f0-9]{32}", str(record.get("id", ""))) for record in records):
        raise HTTPException(409, "全局技能库记录归属无效")
    if len({record["id"] for record in records}) != len(records):
        raise HTTPException(409, "全局技能标识重复")
    return item, [dict(record) for record in records]


async def save_global_skills(item, records, identity, db):
    require_agent_settings_management(identity)
    from app.core.system import _system_audit
    value = {"schema_version": 1, "scope": "global", "skills": records}
    try:
        if item is None:
            db.add(SystemConfig(key=GLOBAL_SKILL_CONFIG_KEY, label="全局智能体技能库", group="智能体",
                value=value, description="仅智能体中心专用管理员接口可管理", updated_by=identity["username"]))
        else:
            item.value = value
            item.updated_by = identity["username"]
        await _system_audit(db, identity, "更新全局智能体技能", "全局技能库", {"skill_count": len(records)})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "全局技能库刚被其他管理员创建，请刷新后重试") from exc
    except Exception:
        await db.rollback()
        raise


async def add_global_skill(payload, identity, db, *, source="user-custom", digest=None):
    require_agent_settings_management(identity)
    record = normalize_custom_skill(payload, skill_id="global-" + uuid4().hex, source=source)
    if digest:
        record["sha256"] = digest
    item, records = await global_skill_store(db, lock=True)
    if digest:
        existing = next((entry for entry in records if entry.get("source") == source), None)
        if existing:
            if existing.get("sha256") != digest or any(existing.get(key) != record[key] for key in ("name", "description", "instruction")):
                raise HTTPException(409, "该全局来源已有不同或已编辑版本，请先删除旧技能再安装")
            if record.get("bundle") and not existing.get("bundle"):
                existing["bundle"] = record["bundle"]
                await save_global_skills(item, records, identity, db)
            return existing
    if len(records) >= CUSTOM_SKILL_LIMIT:
        raise HTTPException(409, f"全局最多保存 {CUSTOM_SKILL_LIMIT} 个技能")
    records.append(record)
    await save_global_skills(item, records, identity, db)
    return record


async def global_skill_record(skill_id, identity, db):
    _, records = await global_skill_store(db)
    record = next((item for item in records if item["id"] == skill_id), None)
    if record is None or (not record.get("enabled", True) and not can_manage_global(identity)):
        raise HTTPException(404, "全局技能不存在或已停用")
    return record

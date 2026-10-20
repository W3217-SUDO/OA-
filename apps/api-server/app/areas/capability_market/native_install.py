"""将市场技能的固定来源资源包接入既有全局及个人技能库。"""
import hashlib
import json
import re
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agent_permissions import require_agent_settings_management
from app.github_agent_skills import github_skill_location
from app.global_agent_skills import global_skill_store, save_global_skills
from app.harness_agent.bundles import install_bundle, read_resource
from app.models import SystemConfig
from app.user_agent_skills import CUSTOM_SKILL_LIMIT, normalize_custom_skill, user_skill_config_key


SCRIPT_ADAPTATION_REASONS = {
    "原技能声明需要 Bash，当前 OA 不执行第三方命令。",
    "需要脚本、CLI 或多智能体运行环境，当前未接入。",
    "需要脚本、CLI 或多智能体运行环境，当前 OA 未接入这些执行依赖。",
}


def installation_reason(item):
    reason = item.get("unavailable_reason", "")
    if (item.get("kind") == "skill" and reason in SCRIPT_ADAPTATION_REASONS
            and not item.get("dependencies")
            and not re.search(r"\b(?:TeamCreate|AgentTool)\b", item.get("instruction", ""))):
        return ""
    return reason


def native_definition(item):
    return {"name": item["name"], "category": item["category"], "description": item["description"],
            "instruction": item["instruction"], "quick_prompts": item.get("quick_prompts", [])}


def _matching_record(previous, payload, legacy_payload, digest):
    if previous.get("sha256") != digest:
        raise HTTPException(409, "此来源已安装但摘要不同，请核对原技能后再安装")
    if any(previous.get(key) != payload[key] for key in payload):
        # 仅升级系统先前生成的完整指令；本人的任何编辑都不能被覆盖。
        if any(previous.get(key) != legacy_payload[key] for key in legacy_payload):
            raise HTTPException(409, "此来源已有用户编辑内容，不能用市场包覆盖")


async def _bundle(item):
    location = github_skill_location(item["source"])
    if not re.fullmatch(r"[a-f0-9]{40}", location["ref"]):
        raise HTTPException(409, "市场技能必须绑定固定 GitHub 提交")
    source_text = item.get("resources", {}).get("SKILL.md")
    if not isinstance(source_text, str):
        raise HTTPException(409, "市场技能缺少已校验的原始 SKILL.md，未安装")
    return await install_bundle({"source": item["source"], "source_text": source_text,
                                 "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest()})


def _verify_installed_bundle(bundle, item):
    location = github_skill_location(item["source"])
    files = bundle.get("files", {})
    if (bundle.get("commit") != location["ref"] or "SKILL.md" not in files
            or hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest() != bundle.get("id")):
        raise HTTPException(409, "已安装技能资源清单与固定来源不同，请核对后重新安装")
    for path in files:
        content = read_resource(bundle, path)
        if path == "SKILL.md":
            try:
                original = content.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
            except UnicodeDecodeError as exc:
                raise HTTPException(409, "已安装技能原文不是 UTF-8") from exc
            if original != item["resources"]["SKILL.md"]:
                raise HTTPException(409, "已安装技能原文与市场来源不同，未覆盖原文件")


async def install_native(item, scope, identity, db, *, legacy_payload):
    """下载在锁外完成，持有库记录行锁后重读并校验，避免覆盖并发编辑。"""
    from app.core.documents import _save_user_agent_skills, _user_agent_skill_store

    if scope == "global":
        require_agent_settings_management(identity)
        _, initial = await global_skill_store(db)
    else:
        _, initial = await _user_agent_skill_store(identity["username"], db)
    payload = native_definition(item)
    existing = next((record for record in initial if record.get("source") == item["source"]), None)
    if existing:
        _matching_record(existing, payload, legacy_payload, item["sha256"])
    elif len(initial) >= CUSTOM_SKILL_LIMIT:
        raise HTTPException(409, f"技能库最多保存 {CUSTOM_SKILL_LIMIT} 项")
    bundle = existing.get("bundle") if existing else None
    if bundle:
        _verify_installed_bundle(bundle, item)
    else:
        bundle = await _bundle(item)
    try:
        if scope == "global":
            store, records = await global_skill_store(db, lock=True)
        else:
            await db.scalar(select(SystemConfig).where(
                SystemConfig.key == user_skill_config_key(identity["username"])).with_for_update().execution_options(populate_existing=True))
            _, records = await _user_agent_skill_store(identity["username"], db)
        previous = next((record for record in records if record.get("source") == item["source"]), None)
        if previous:
            if existing and previous["id"] != existing["id"]:
                raise HTTPException(409, "技能已被重新安装，请刷新后核对")
            _matching_record(previous, payload, legacy_payload, item["sha256"])
            if previous.get("bundle") and previous["bundle"] != bundle:
                raise HTTPException(409, "技能资源已被其他请求修改，请刷新后核对")
            result = normalize_custom_skill({**payload, "bundle": bundle, "sha256": item["sha256"],
                                              "enabled": previous.get("enabled", True)},
                                             skill_id=previous["id"], source=item["source"])
            if result == previous:
                return previous
            records[records.index(previous)] = result
        else:
            if existing:
                raise HTTPException(409, "技能刚被删除，请刷新后重新安装")
            if len(records) >= CUSTOM_SKILL_LIMIT:
                raise HTTPException(409, f"技能库最多保存 {CUSTOM_SKILL_LIMIT} 项")
            result = normalize_custom_skill({**payload, "bundle": bundle, "sha256": item["sha256"]},
                skill_id="global-" + uuid4().hex if scope == "global" else "", source=item["source"])
            records.append(result)
        if scope == "global":
            await save_global_skills(store, records, identity, db)
        else:
            await _save_user_agent_skills(identity["username"], records, identity, db)
        return result
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "技能库刚被其他请求创建，请刷新后重试") from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(422, f"能力包不满足当前技能格式：{exc}") from exc
    except Exception:
        await db.rollback()
        raise

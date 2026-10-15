from __future__ import annotations

import asyncio
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import logger
from app.database import get_db
from app.security import current_identity
from app.skill_catalog import CatalogSource
from app.areas.personal_agent.service import build_context, decide_action, generate_response, manage_conversations, personal_identity, personal_state, stop_response, _user_dir
from app.areas.personal_agent.memory_graph import delete_memory, list_memories, update_settings
from app.areas.personal_agent import conversations
from app.areas.personal_agent.workspace import workspace_commands
from app.areas.personal_agent.response_runtime import ResponseMode, supports_response_modes
from app.areas.personal_agent.confirmation_history import read_confirmation_detail, read_confirmation_history, project_personal_actions
from app.areas.personal_agent.action_presentation import dismiss_personal_actions
from app.areas.personal_agent.project_workspaces import ProjectWorkspace, normalize_workspace
from app.areas.personal_agent.ai_space import router as ai_space_router


router = APIRouter()
router.include_router(ai_space_router)


class PersonalMessageInput(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=64)
    content: str = Field(min_length=1, max_length=8000)
    skill_id: str = Field(default="general-office", max_length=120)
    attachment_ids: list[int] = Field(default_factory=list, max_length=12)
    case_id: int | None = Field(default=None, ge=1)
    document_ids: list[int] = Field(default_factory=list, max_length=12)
    response_mode: ResponseMode = "fast"
    workspace: ProjectWorkspace | None = None


class PersonalConversationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace: ProjectWorkspace | None = None


class PersonalWorkspaceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace: ProjectWorkspace


class MemorySettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    recall_limit: int | None = Field(default=None, ge=0, le=20)


def conversation_workspace(
    workspace_kind: Literal["personal", "case"] | None = None,
    workspace_case_id: Annotated[int | None, Query(ge=1)] = None,
) -> dict | None:
    if workspace_kind is None and workspace_case_id is None:
        return None
    return normalize_workspace({"kind": workspace_kind, "case_id": workspace_case_id})


class PersonalActionDecisionInput(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=64)
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=1000)


class PersonalActionDismissInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_ids: list[str] = Field(min_length=1, max_length=30)


class GitHubSkillPreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)


class GitHubSkillInstallInput(GitHubSkillPreviewInput):
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SkillCatalogPreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: CatalogSource
    id: str = Field(min_length=1, max_length=600)
    q: str = Field(default="", max_length=100)


@router.get(f"{settings.api_prefix}/agent/skills/catalog")
async def skill_catalog_list(source: CatalogSource = "openai", q: str = Query(default="", max_length=100),
                             identity: dict = Depends(current_identity)):
    from app.skill_catalog import catalog, catalog_quota
    catalog_quota(identity["username"])
    return await catalog(source, q)


@router.post(f"{settings.api_prefix}/agent/skills/catalog/preview")
async def skill_catalog_preview(body: SkillCatalogPreviewInput, identity: dict = Depends(current_identity)):
    from app.skill_catalog import catalog_preview, catalog_quota
    catalog_quota(identity["username"])
    return await catalog_preview(body.source, body.id, body.q)


@router.post(f"{settings.api_prefix}/agent/skills/github/preview")
async def github_skill_preview(body: GitHubSkillPreviewInput, identity: dict = Depends(current_identity)):
    from app.github_agent_skills import preview_github_skill
    return await preview_github_skill(body.url)


@router.post(f"{settings.api_prefix}/agent/skills/github/install")
async def github_skill_install(body: GitHubSkillInstallInput, identity: dict = Depends(current_identity),
                               db: AsyncSession = Depends(get_db)):
    from app.core.documents import _save_user_agent_skills, _user_agent_skill_store
    from app.github_agent_skills import preview_github_skill
    from app.user_agent_skills import CUSTOM_SKILL_LIMIT, custom_skill_public, normalize_custom_skill

    preview = await preview_github_skill(body.url)
    if preview["sha256"] != body.sha256:
        raise HTTPException(status_code=409, detail="GitHub 技能内容已变化，请重新预览后安装")
    _, skills = await _user_agent_skill_store(identity["username"], db)
    existing = next((item for item in skills if item.get("source") == preview["source"]), None)
    if existing:
        if (existing.get("sha256") != preview["sha256"]
                or any(existing.get(field) != preview[field] for field in ("name", "description", "instruction"))):
            raise HTTPException(status_code=409, detail="该来源已有不同版本技能，请先删除旧技能再安装")
        return custom_skill_public(existing)
    if len(skills) >= CUSTOM_SKILL_LIMIT:
        raise HTTPException(status_code=409, detail=f"每个账号最多保存 {CUSTOM_SKILL_LIMIT} 个自定义技能")
    record = normalize_custom_skill({**preview, "category": "GitHub"}, source=preview["source"])
    record["sha256"] = preview["sha256"]
    skills.append(record)
    await _save_user_agent_skills(identity["username"], skills, identity, db)
    return custom_skill_public(record)


@router.get(f"{settings.api_prefix}/personal-agent/status")
async def personal_agent_status(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    from app.areas.personal_agent.ai_space_service import personal_save_capability
    file_capability = await personal_save_capability(safe_identity, db)
    return {
        "ready": bool(settings.langgraph_enabled and settings.langgraph_api_base_url and settings.langgraph_api_key and settings.langgraph_model),
        "model": settings.langgraph_model,
        "model_provider": settings.langgraph_model_provider,
        "runtime": "personal-agent",
        "supports_response_modes": supports_response_modes(),
        "write_requires_confirmation": True,
        "personal_file_storage": file_capability,
        "identity": {key: value for key, value in safe_identity.items() if not key.startswith("_")},
        "commands": workspace_commands(safe_identity),
    }


@router.get(f"{settings.api_prefix}/personal-agent/state")
async def personal_agent_state(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await personal_state(await personal_identity(identity, db), db)


@router.get(f"{settings.api_prefix}/personal-agent/workspace")
async def personal_agent_workspace(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    context = await build_context(safe_identity, db)
    # 工作台与对话共用权限裁剪后的真实业务摘要，不返回内部身份文件。
    return {key: context[key] for key in (
        "todos", "my_tasks", "pending_contract_approvals", "pending_other_approvals", "visible_cases",
    )}


@router.get(f"{settings.api_prefix}/personal-agent/conversations")
async def personal_agent_conversations(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
                                       workspace: dict | None = Depends(conversation_workspace)):
    return await manage_conversations(await personal_identity(identity, db), db=db, workspace=workspace)


@router.post(f"{settings.api_prefix}/personal-agent/workspaces")
async def personal_agent_register_workspace(body: PersonalWorkspaceInput, identity: dict = Depends(current_identity),
                                            db: AsyncSession = Depends(get_db)):
    return await manage_conversations(await personal_identity(identity, db), "register", db=db,
                                       workspace=body.workspace.model_dump(exclude_none=True))


@router.get(f"{settings.api_prefix}/personal-agent/confirmation-history")
async def personal_agent_confirmation_history(
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str = "",
):
    safe_identity = await personal_identity(identity, db)
    return await read_confirmation_history(safe_identity, db, status=status, page=page, page_size=page_size,
                                           directory=_user_dir(safe_identity["username"]))


@router.get(f"{settings.api_prefix}/personal-agent/memory")
async def personal_agent_memory(scope: Literal["short", "long"] = "short",
                                limit: Annotated[int, Query(ge=1, le=100)] = 50,
                                identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    result = list_memories(_user_dir(safe_identity["username"]), int(safe_identity["_actual_user_id"]), limit)
    if scope == "long":
        items = [{**item, "memory_type": "long", "source": "用户明确要求保存"} for item in result["items"]]
    else:
        state = conversations.read_state(_user_dir(safe_identity["username"]))
        items = []
        if state.get("memory_summary"):
            items = [{"id": f"short-{state.get('conversation_id')}", "memory_type": "short",
                      "content": state["memory_summary"], "source": "当前会话自动压缩",
                      "conversation_id": state.get("conversation_id"), "permission_scope": "当前用户",
                      "created_at": state.get("memory_summary_updated_at") or state.get("updated_at")}]
    return {"settings": result["settings"], "items": items,
            "long_term_enabled": bool(result["settings"].get("enabled", True)),
            "recall_limit": int(result["settings"].get("recall_limit", 5))}


@router.post(f"{settings.api_prefix}/personal-agent/memory/settings")
async def personal_agent_memory_settings(body: MemorySettingsInput,
                                         identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    return {"settings": update_settings(_user_dir(safe_identity["username"]), int(safe_identity["_actual_user_id"]),
                                          enabled=body.enabled, retention_days=body.retention_days,
                                          recall_limit=body.recall_limit)}


@router.delete(f"{settings.api_prefix}/personal-agent/memory/{{memory_id}}")
async def personal_agent_memory_delete(memory_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    if not delete_memory(_user_dir(safe_identity["username"]), int(safe_identity["_actual_user_id"]), memory_id):
        raise HTTPException(status_code=404, detail="记忆不存在或不属于当前用户")
    return {"id": memory_id, "status": "deleted"}


@router.get(f"{settings.api_prefix}/personal-agent/confirmation-history/{{source}}/{{request_id}}")
async def personal_agent_confirmation_detail(source: str, request_id: str,
                                             identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    return await read_confirmation_detail(source, request_id, safe_identity, db,
                                          directory=_user_dir(safe_identity["username"]))


@router.post(f"{settings.api_prefix}/personal-agent/conversations/{{conversation_id}}/actions/dismiss")
async def personal_agent_action_dismiss(conversation_id: str, body: PersonalActionDismissInput,
                                        identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.agent_mcp.auth import authenticated_identity

    actual_identity = await authenticated_identity(db)
    if identity["username"] != actual_identity["username"]:
        raise HTTPException(403, "操作卡展示身份与实际登录账号不一致")
    return await dismiss_personal_actions(_user_dir(actual_identity["username"]), conversation_id, body.action_ids,
                                         actual_identity, db)


@router.post(f"{settings.api_prefix}/personal-agent/conversations")
async def personal_agent_create_conversation(body: PersonalConversationInput | None = None,
                                              identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    workspace = body.workspace.model_dump(exclude_none=True) if body and body.workspace is not None else None
    return await manage_conversations(await personal_identity(identity, db), "create", db=db, workspace=workspace)


@router.post(f"{settings.api_prefix}/personal-agent/conversations/{{conversation_id}}/select")
async def personal_agent_select_conversation(conversation_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
                                             workspace: dict | None = Depends(conversation_workspace)):
    return await manage_conversations(await personal_identity(identity, db), "select", conversation_id, db=db, workspace=workspace)


@router.delete(f"{settings.api_prefix}/personal-agent/conversations/{{conversation_id}}")
async def personal_agent_delete_conversation(conversation_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
                                             workspace: dict | None = Depends(conversation_workspace)):
    return await manage_conversations(await personal_identity(identity, db), "delete", conversation_id, db=db, workspace=workspace)


@router.post(f"{settings.api_prefix}/personal-agent/conversations/{{conversation_id}}/stop")
async def personal_agent_stop_generation(conversation_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await stop_response(await personal_identity(identity, db), conversation_id, db=db)


@router.get(f"{settings.api_prefix}/personal-agent/identity.md")
async def personal_agent_identity_file(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    state = await personal_state(safe_identity, db)
    return {"name": "IDENTITY.md", "content": state["identity_file"]}


@router.post(f"{settings.api_prefix}/personal-agent/messages")
async def personal_agent_message(body: PersonalMessageInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def on_delta(content: str) -> None:
        await queue.put({"type": "delta", "content": content})

    async def on_progress(content: str) -> None:
        await queue.put({"type": "progress", "content": content})

    async def run() -> None:
        try:
            result = await asyncio.wait_for(generate_response(safe_identity, db, body.content, on_delta, conversation_id=body.conversation_id, skill_id=body.skill_id, attachment_ids=body.attachment_ids, case_id=body.case_id, document_ids=body.document_ids, response_mode=body.response_mode, on_progress=on_progress,
                                                               workspace=body.workspace.model_dump(exclude_none=True) if body.workspace is not None else None), timeout=180)
            await queue.put({"type": "state", "state": result["state"]})
        except TimeoutError:
            await queue.put({"type": "error", "detail": "个人智能体本轮处理超时，请查看待确认请求后继续"})
        except HTTPException as exc:
            await queue.put({"type": "error", "detail": str(exc.detail)})
        except Exception:
            logger.exception("个人智能体生成失败，用户=%s", safe_identity["username"])
            await queue.put({"type": "error", "detail": "个人智能体处理失败，请稍后重试"})
        finally:
            await queue.put({"type": "done"})

    async def events():
        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] == "done":
                    break
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post(f"{settings.api_prefix}/personal-agent/actions/{{action_id}}/decision")
async def personal_agent_action_decision(action_id: str, body: PersonalActionDecisionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    result = await decide_action(safe_identity, db, action_id, body.decision, body.comment, conversation_id=body.conversation_id)
    return {**result, "state": await project_personal_actions(result["state"], safe_identity, db)}

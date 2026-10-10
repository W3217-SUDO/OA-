from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import logger
from app.database import get_db
from app.security import current_identity
from app.areas.personal_agent.service import build_context, decide_action, generate_response, personal_identity, personal_state
from app.areas.personal_agent.workspace import workspace_commands
from app.areas.personal_agent.response_runtime import ResponseMode, supports_response_modes


router = APIRouter()


class PersonalMessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    skill_id: str = Field(default="general-office", max_length=120)
    attachment_ids: list[int] = Field(default_factory=list, max_length=12)
    case_id: int | None = Field(default=None, ge=1)
    document_ids: list[int] = Field(default_factory=list, max_length=12)
    response_mode: ResponseMode = "fast"


class PersonalActionDecisionInput(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(default="", max_length=1000)


@router.get(f"{settings.api_prefix}/personal-agent/status")
async def personal_agent_status(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    safe_identity = await personal_identity(identity, db)
    return {
        "ready": bool(settings.langgraph_enabled and settings.langgraph_api_base_url and settings.langgraph_api_key and settings.langgraph_model),
        "model": settings.langgraph_model,
        "model_provider": settings.langgraph_model_provider,
        "runtime": "personal-agent",
        "supports_response_modes": supports_response_modes(),
        "write_requires_confirmation": True,
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
            result = await asyncio.wait_for(generate_response(safe_identity, db, body.content, on_delta, skill_id=body.skill_id, attachment_ids=body.attachment_ids, case_id=body.case_id, document_ids=body.document_ids, response_mode=body.response_mode, on_progress=on_progress), timeout=180)
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
    return await decide_action(safe_identity, db, action_id, body.decision, body.comment)

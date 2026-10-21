"""智能体设置中的 DSH 原生插件管理；沿用全所智能体管理授权。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.global_agent_skills import require_global_admin
from app.config import settings
from app.harness_agent.plugin_packages import run_operation
from app.harness_agent.plugins import change, overview
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix + "/agent-admin/dsh-plugins")


class InstallInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spec: str = Field(min_length=1, max_length=500)
    allow_builds: list[str] = Field(default_factory=list, max_length=20)


class PluginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=214)


class ToggleInput(PluginInput):
    enabled: bool


@router.get("")
async def list_plugins(identity: dict = Depends(current_identity)):
    require_global_admin(identity)
    return await run_operation(overview)


@router.post("/install")
async def install_plugin(body: InstallInput, identity: dict = Depends(current_identity)):
    require_global_admin(identity)
    return await run_operation(change, "install", body.model_dump())


@router.post("/toggle")
async def toggle_plugin(body: ToggleInput, identity: dict = Depends(current_identity)):
    require_global_admin(identity)
    return await run_operation(change, "toggle", body.model_dump())


@router.post("/remove")
async def remove_plugin(body: PluginInput, identity: dict = Depends(current_identity)):
    require_global_admin(identity)
    return await run_operation(change, "remove", body.model_dump())

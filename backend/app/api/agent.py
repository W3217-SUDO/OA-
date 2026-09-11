"""Local Agent contract used by both the Vue demo and the CLI.

The runtime is deliberately deterministic in this demo. A production Agent
provider can later implement the same contract without changing page code.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    skill: str = Field(min_length=1, max_length=120)
    input: str = Field(min_length=1, max_length=10_000)
    context: dict[str, object] = Field(default_factory=dict)


class AgentRun(BaseModel):
    id: str
    status: str
    skill: str
    input: str
    output: str
    created_at: datetime
    read_only: bool = True


CAPABILITIES = [
    {
        "name": "legacy.page.explain",
        "label": "解释旧页面",
        "description": "根据当前页面上下文解释字段、按钮和跳转关系。",
        "read_only": True,
    },
    {
        "name": "legacy.case.search",
        "label": "查询案件",
        "description": "通过受控业务服务查询案件，不直接写数据库。",
        "read_only": True,
    },
    {
        "name": "legacy.workflow.draft",
        "label": "生成流程草稿",
        "description": "生成待人工确认的流程草稿，Demo 阶段不执行写入。",
        "read_only": True,
    },
]

_runs: dict[str, AgentRun] = {}


@router.get("/capabilities")
def capabilities() -> dict[str, object]:
    return {"items": CAPABILITIES, "runtime": "local-demo", "read_only": True}


@router.post("/runs", response_model=AgentRun, status_code=status.HTTP_202_ACCEPTED)
def create_run(payload: AgentRunRequest) -> AgentRun:
    if payload.skill not in {item["name"] for item in CAPABILITIES}:
        raise HTTPException(status_code=400, detail="Unsupported agent skill")
    run = AgentRun(
        id=f"run_{uuid4().hex[:12]}",
        status="completed",
        skill=payload.skill,
        input=payload.input,
        output=f"Demo 已接收“{payload.input}”，技能 {payload.skill} 当前仅生成只读结果。",
        created_at=datetime.now(UTC),
    )
    _runs[run.id] = run
    return run


@router.get("/runs/{run_id}", response_model=AgentRun)
def get_run(run_id: str) -> AgentRun:
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


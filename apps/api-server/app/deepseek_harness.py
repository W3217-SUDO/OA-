"""智能体执行固定使用 DPH；拒绝恢复已停用的旧引擎。"""
from typing import Any
from .case_agent import CaseAgentRuntime


def create_case_agent_runtime(*, runtime_backend: str = "deepseek-harness", **kwargs: Any) -> CaseAgentRuntime:
    if runtime_backend.strip().casefold() != "deepseek-harness":
        raise ValueError("仅支持 deepseek-harness，旧智能体引擎已停用")
    return CaseAgentRuntime(**kwargs)

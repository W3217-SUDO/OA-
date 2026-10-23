"""案件阶段按案件类型取范围（10.22 第 11 行）。

刑事案件的“变更阶段”范围 = 刑事专用阶段（公安侦查、批捕、检察院审查起诉，及旧系统迁入且
extra.case_type=刑事案件 的阶段）+ 与民事共用的“新案待分配”、一审/二审/再审/归档四组。
其他案件类型沿用 app.core.cases 中原有的“内置 + 管理员关联”规则，行为不变。

生产库可能同时存在内置阶段和旧系统迁入的同名阶段（不同 id）。这里：
- 列表按名称去重，同名时优先内置编码行，避免弹窗按名称匹配到另一条；
- 提交时以所选 id 为准，只核对该 id 自身的名称，不再按名称全表取第一条，
  消除“案件阶段 ID 与名称不匹配”的误报。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.constants import (
    BUILTIN_CASE_PHASE_CODES, CASE_PHASE_STATUS_BY_CODE, CRIMINAL_CASE_PHASE_CODES,
    CRIMINAL_CASE_TYPE, CRIMINAL_SHARED_CIVIL_PHASE_CODES, is_criminal_case_type,
)
from app.models import CaseTypeCasePhaseRelation, SystemParameter


def _phase_case_type(phase: SystemParameter) -> str:
    return str((phase.extra or {}).get("case_type") or "").strip()


def criminal_phase_is_builtin(phase: SystemParameter) -> bool:
    """刑事案件内置可用阶段：刑事专用（含迁入刑事阶段）+ 与民事共用的内置阶段。"""
    if phase.code in CRIMINAL_CASE_PHASE_CODES or _phase_case_type(phase) == CRIMINAL_CASE_TYPE:
        return True
    return phase.code in CRIMINAL_SHARED_CIVIL_PHASE_CODES and _phase_case_type(phase) in {"民事争议", "民事案件"}


def phase_is_builtin_for_case_type(phase: SystemParameter, case_type: SystemParameter | None) -> bool:
    from app.core.cases import _phase_is_builtin_for_case_type
    if case_type and is_criminal_case_type(case_type.name):
        return criminal_phase_is_builtin(phase)
    return _phase_is_builtin_for_case_type(phase, case_type)


def dedupe_phases_by_name(phases: list[SystemParameter]) -> list[SystemParameter]:
    """同名阶段只保留一条：优先内置编码，其次最早一条；保持原排序。"""
    chosen: dict[str, SystemParameter] = {}
    for phase in phases:
        name = str(phase.name or "").strip()
        current = chosen.get(name)
        if current is None or (phase.code in BUILTIN_CASE_PHASE_CODES and current.code not in BUILTIN_CASE_PHASE_CODES):
            chosen[name] = phase
    kept = {item.id for item in chosen.values()}
    return [phase for phase in phases if phase.id in kept]


async def case_phase_is_allowed(case_type_value: str, phase_id: int, db: AsyncSession) -> bool:
    from app.core.cases import _case_phase_is_allowed, _case_type_parameter_for_value
    case_type = await _case_type_parameter_for_value(case_type_value, db)
    phase = await db.get(SystemParameter, phase_id)
    if is_criminal_case_type(case_type_value):
        if case_type and phase and criminal_phase_is_builtin(phase):
            return True
    elif phase and phase.code in CRIMINAL_CASE_PHASE_CODES:
        # 新增的刑事专用阶段不进入其他案件类型（原规则下“未配置关联即全部可用”会放行）；
        # 管理员明确把它关联给其他类型时仍按关联放行。
        if not case_type:
            return False
        return bool(await db.scalar(select(CaseTypeCasePhaseRelation.id).where(
            CaseTypeCasePhaseRelation.case_type_id == case_type.id,
            CaseTypeCasePhaseRelation.case_phase_id == phase.id,
        ).limit(1)))
    return await _case_phase_is_allowed(case_type_value, phase_id, db)


async def resolve_case_phase(case_phase_id: int | None, case_phase_name: str, db: AsyncSession) -> dict:
    from app.core.cases import _active_case_phase_values, _case_phase_option
    phase_id = int(case_phase_id or 0)
    phase_name = str(case_phase_name or "").strip()
    phase = await db.get(SystemParameter, phase_id) if phase_id else None
    if phase_id and (not phase or phase.category != "case_phase" or not phase.is_active):
        raise HTTPException(status_code=422, detail="案件阶段不存在或已停用")
    if phase is not None:
        if phase_name and phase_name not in {
            str(phase.name or "").strip(), CASE_PHASE_STATUS_BY_CODE.get(phase.code, phase.name),
        }:
            raise HTTPException(status_code=422, detail="案件阶段 ID 与名称不匹配")
    elif phase_name:
        candidates = list((await db.scalars(select(SystemParameter).where(
            SystemParameter.category == "case_phase", SystemParameter.name == phase_name,
            SystemParameter.is_active.is_(True),
        ).order_by(SystemParameter.id))).all())
        if not candidates:
            raise HTTPException(status_code=422, detail="案件阶段不存在或已停用")
        phase = next((item for item in candidates if item.code in BUILTIN_CASE_PHASE_CODES), candidates[0])
    if not phase:
        raise HTTPException(status_code=422, detail="阶段名称不能为空")
    canonical_name = CASE_PHASE_STATUS_BY_CODE.get(phase.code, phase.name)
    if canonical_name not in await _active_case_phase_values(db):
        raise HTTPException(status_code=422, detail="案件阶段不是允许的办理阶段")
    return {**_case_phase_option(phase), "canonical_name": canonical_name}

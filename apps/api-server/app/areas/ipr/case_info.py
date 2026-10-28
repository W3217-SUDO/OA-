"""知识产权案件页“案件信息”的修改、保存（BUG20261028001，陶国南 2026-10-28 确认）。

字段和原系统案件页一致；迁移来的历史案件也能修改（原来整页只读）。写回案件页读取的同名字段，
新系统字段名（application_no 等）一并同步，修改记一条系统日志。
"""
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.dependencies import AsyncSession, Depends, HTTPException, WorkflowEvent, current_identity, func, get_db, settings

router = APIRouter()

# 页面字段 → 案件 data 里要写的键（第一个是案件页读取的键，其余同步）。
INFO_FIELD_KEYS = {
    "case_phase": ("case_phase",),
    "case_register_date": ("case_register_date",),
    "case_request_no": ("case_request_no", "application_no"),
    "case_name": ("case_name",),
    "case_request_date": ("case_request_date", "application_date"),
    "authorization_date": ("authorization_date",),
    "case_origin_people_name": ("case_origin_people_name", "case_source"),
    "agent": ("agent",),
    "writer": ("writer",),
    "first_annual_year": ("first_annual_year", "annual_fee_year"),
    "case_origin_date": ("case_origin_date", "source_date"),
    "ref_case_no": ("ref_case_no",),
    "card_no": ("card_no",),
    "cost_slow_rate": ("cost_slow_rate", "rate"),
    "applicant_name": ("applicant_name", "applicant"),
    "inventor": ("inventor", "case_inventor"),
    "case_manager": ("case_manager",),
}
FLAG_KEYS = ("has_priority", "has_foreign", "has_relief", "has_private_inventor", "has_iu")
INFO_LABELS = {
    "case_phase": "案件阶段", "case_register_date": "立案日", "case_request_no": "申请号", "case_name": "名称",
    "case_request_date": "申请日", "authorization_date": "授权日", "case_origin_people_name": "案源人", "agent": "代理人",
    "writer": "撰稿人", "first_annual_year": "首年年费年度", "case_origin_date": "案源日", "ref_case_no": "关联案号",
    "card_no": "证件号码", "cost_slow_rate": "费用减缓比例", "applicant_name": "申请人", "inventor": "发明人",
    "case_manager": "案件管理人", "has_priority": "优先权", "has_foreign": "涉外案件", "has_relief": "费用减缓",
    "has_private_inventor": "不公发明人", "has_iu": "一发一实",
}
RELIEF_RATES = ("1.00", "0.85", "0.70")


class IprCaseInfoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_phase: str | None = Field(default=None, max_length=128)
    case_register_date: date | None = None
    case_request_no: str | None = Field(default=None, max_length=128)
    case_name: str | None = Field(default=None, max_length=255)
    case_request_date: date | None = None
    authorization_date: date | None = None
    case_origin_people_name: str | None = Field(default=None, max_length=128)
    agent: str | None = Field(default=None, max_length=255)
    writer: str | None = Field(default=None, max_length=255)
    first_annual_year: int | None = Field(default=None, ge=1, le=30)
    case_origin_date: date | None = None
    ref_case_no: str | None = Field(default=None, max_length=128)
    card_no: str | None = Field(default=None, max_length=64)
    cost_slow_rate: str | None = Field(default=None, max_length=8)
    applicant_name: str | None = Field(default=None, max_length=500)
    inventor: str | None = Field(default=None, max_length=500)
    case_manager: str | None = Field(default=None, max_length=128)
    has_priority: bool | None = None
    has_foreign: bool | None = None
    has_relief: bool | None = None
    has_private_inventor: bool | None = None
    has_iu: bool | None = None


def _stored(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return value


@router.patch(f"{settings.api_prefix}/ipr/cases/{{case_id}}/info")
async def update_ipr_case_info(case_id: int, body: IprCaseInfoInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _require_role_action
    await _require_role_action(identity, db, "ipr.case.update")
    from app.core.permissions import _ensure_record_module, _require_record_owner_or_manager
    from app.core.system import _allowed_field_keys, _record_dict
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status in {"已结案"}:
        raise HTTPException(status_code=409, detail="已结案的案件不能修改")
    values = body.model_dump(exclude_unset=True)
    if "cost_slow_rate" in values and values["cost_slow_rate"] not in (None, "", *RELIEF_RATES):
        raise HTTPException(status_code=422, detail="费用减缓比例只能是无减缓、85%减缓或70%减缓")
    data = dict(record.data or {})
    changed = []
    for field, value in values.items():
        new = _stored(value)
        if field in FLAG_KEYS:
            new = "T" if value else "F"
            was_checked = str(data.get(field) or "F") in {"T", "t", "true", "True", "1"}
            if was_checked != (new == "T"):
                changed.append(INFO_LABELS[field])
            data[field] = new
            continue
        keys = INFO_FIELD_KEYS[field]
        before = str(data.get(keys[0]) or "")
        if (before[:10] if isinstance(value, date) else before) != str(new or ""):
            changed.append(INFO_LABELS[field])
        for key in keys:
            data[key] = str(new) if field == "first_annual_year" and new is not None else new
    if "case_name" in values and values["case_name"]:
        record.title = values["case_name"].strip()
    if not changed:
        return _record_dict(record, await _allowed_field_keys(identity, db))
    record.data = data
    record.updated_at = func.now()
    db.add(WorkflowEvent(record_id=record.id, action="修改案件信息", from_status=record.status, to_status=record.status,
                         operator=identity["username"], comment="修改：" + "、".join(changed)))
    await db.commit()
    await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/phase-options")
async def list_ipr_case_phase_options(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """案件阶段下拉：原系统该案件类型可用的阶段（IPR_CaseType_PhaseList）；镜像表不在时只给当前阶段。"""
    from app.core.permissions import _ensure_record_module
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    data = record.data or {}
    current = str(data.get("case_phase") or "").strip()
    names: list[str] = []
    try:
        async with db.begin_nested():
            type_id = int(data.get("case_type_id") or 0)
            rows = (await db.execute(text(
                'SELECT p."CasePhaseName" FROM "IPR_CaseType_PhaseList" l JOIN "IPR_CasePhase" p ON p."CasePhaseId" = l."CasePhaseId" '
                'WHERE l."CaseTypeId" = :type_id ORDER BY p."CasePhaseId"'
            ), {"type_id": type_id})).scalars().all() if type_id else []
            if not rows:
                rows = (await db.execute(text('SELECT "CasePhaseName" FROM "IPR_CasePhase" ORDER BY "CasePhaseId"'))).scalars().all()
            names = [str(name).strip() for name in rows if str(name or "").strip()]
    except SQLAlchemyError:
        names = []
    if current and current not in names:
        names.insert(0, current)
    return {"items": list(dict.fromkeys(names))}

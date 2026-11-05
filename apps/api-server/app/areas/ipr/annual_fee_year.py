"""501617（fwl 11-05）：专利年费页补老系统“修改首年年度及减缓比例”（批量处理）。单独路由放在知识产权路由最后（main.py 按顺序切片）。"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import AsyncSession, Depends, HTTPException, WorkflowEvent, current_identity, get_db, settings

router = APIRouter()


class _AnnualYearEditInput(BaseModel):
    case_ids: list[int] = Field(min_length=1, max_length=500)
    first_annual_year: int = Field(ge=1, le=20)
    cost_slow_rate: str


@router.post(f"{settings.api_prefix}/ipr/annual-fee-monitor/annual-year")
async def edit_ipr_annual_fee_first_year(body: _AnnualYearEditInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """勾选案件后批量设“首年缴费年度”“减缓比例”（无减缓 1.00 / 减缓85% 0.85 / 减缓70% 0.70，同 501614 案件上的下拉），
    写到每个案件上，记案件日志；年费列表按新值重算。"""
    from app.areas.ipr.case_info import RELIEF_RATES
    from app.core.permissions import _ensure_record_module, _require_record_owner_or_manager, _require_role_action
    await _require_role_action(identity, db, "ipr.case.reminder.manage")
    if body.cost_slow_rate not in RELIEF_RATES:
        raise HTTPException(status_code=422, detail="减缓比例只能选 无减缓 / 减缓85% / 减缓70%")
    records = []
    for case_id in dict.fromkeys(body.case_ids):
        record = await _ensure_record_module(case_id, "ipr_case", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        records.append(record)
    label = {"1.00": "无减缓", "0.85": "减缓85%", "0.70": "减缓70%"}[body.cost_slow_rate]
    for record in records:
        data = dict(record.data or {})
        before = f"第{data.get('first_annual_year') or '-'}年度 / {data.get('cost_slow_rate') or '-'}"
        data.update(first_annual_year=body.first_annual_year, annual_fee_year=body.first_annual_year, cost_slow_rate=body.cost_slow_rate, rate=body.cost_slow_rate)
        record.data = data
        db.add(WorkflowEvent(record_id=record.id, action="修改首年年度及减缓比例", from_status=record.status, to_status=record.status,
                             operator=identity["username"], comment=f"{before} → 第{body.first_annual_year}年度 / {label}"))
    await db.commit()
    return {"updated": len(records)}

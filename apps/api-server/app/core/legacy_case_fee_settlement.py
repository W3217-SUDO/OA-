"""从已导入的案件费用还原待结算提成资格。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, LegacyFinanceRecord


async def legacy_case_fee_settlement_sources(
    db: AsyncSession, fee_ids: set[int] | None = None,
) -> dict[int, dict]:
    """读取原案件费用的到账基数和结算状态，供列表及写入共用。"""
    conditions = [
        BusinessRecord.module == "finance",
        BusinessRecord.status != "已删除",
        BusinessRecord.data["fee_type"].as_string() == "代理费",
        LegacyFinanceRecord.source_table == "FAM_AR_CaseFee",
        LegacyFinanceRecord.is_active.is_(True),
    ]
    if fee_ids is not None:
        if not fee_ids:
            return {}
        conditions.append(BusinessRecord.id.in_(fee_ids))
    rows = (await db.execute(
        select(
            BusinessRecord.id,
            BusinessRecord.data["commission_paid"].as_string(),
            BusinessRecord.data["settlement_status"].as_string(),
            LegacyFinanceRecord.source_payload["SettlementStatus"].as_string(),
            LegacyFinanceRecord.source_payload["CashedAmount"].as_string(),
        )
        .join(
            LegacyFinanceRecord,
            LegacyFinanceRecord.legacy_id == BusinessRecord.data["legacy_case_fee_id"].as_string(),
        )
        .where(*conditions)
    )).all()
    sources: dict[int, dict] = {}
    for record_id, paid_flag, current_status, source_status, cash_value in rows:
        cashed_amount = float(cash_value or 0)
        sources[record_id] = {
            "eligible": bool(
                str(paid_flag or "").lower() not in {"true", "1"}
                and str(current_status or "").strip() != "25"
                and str(source_status or "").strip() != "25"
                and cashed_amount > 0
            ),
            "cashed_amount": cashed_amount,
        }
    return sources

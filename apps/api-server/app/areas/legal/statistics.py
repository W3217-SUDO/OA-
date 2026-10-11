"""沿用案件检索权限和条件，对全部匹配案件汇总，不读取分页历史明细。"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas.cases import CounselCaseSearchInput
from app.config import settings
from app.core.cases import _query_counsel_cases
from app.database import get_db
from app.security import current_identity


router = APIRouter()


@router.post(f"{settings.api_prefix}/cases/statistics")
async def case_statistics(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """案件全量统计：在原查询权限和全部筛选条件下返回案件总数及阶段分布，忽略明细分页。"""
    records = await _query_counsel_cases(body, identity, db, counsel_only=False, search_projection=True)
    phases = Counter(str(record.status or "未填写") for record in records)
    types = Counter(str((record.data or {}).get("case_type") or "未填写") for record in records)
    return {
        "total": len(records), "phase_counts": dict(sorted(phases.items())),
        "case_type_counts": dict(sorted(types.items())),
        "aggregation_scope": "当前账号在原案件检索权限及筛选条件下的全部匹配案件，不受 page/page_size 限制；默认普通列表排除法律顾问，global 或明确案件类型按原检索规则执行",
        "filters": {
            **body.model_dump(mode="json", exclude_defaults=True, exclude={"page", "page_size", "sort_order"}),
            "scope": body.scope,
        },
    }

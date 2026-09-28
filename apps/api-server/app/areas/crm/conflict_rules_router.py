"""利益冲突规则目录的只读接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.areas.crm.conflict_rule_catalog import get_conflict_rule_catalog
from app.config import settings
from app.core.dependencies import current_identity, get_db
from app.core.permissions import _require_customer_conflict_permission


router = APIRouter()


@router.get(f"{settings.api_prefix}/conflict-rules")
async def list_conflict_rules(
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    await _require_customer_conflict_permission(identity, db)
    return get_conflict_rule_catalog()

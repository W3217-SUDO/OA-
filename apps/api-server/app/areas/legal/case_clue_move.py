"""案件线索整条移到其他案子（501337，fwl 11-04）：线索、证物（公证书号、仓库位置）、该线索的费用一起移。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import current_identity, get_db

router = APIRouter()


class CaseClueMoveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_case_no: str = Field(min_length=1, max_length=64)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/clues/{{clue_id}}/bundle")
async def preview_case_clue_bundle(case_id: int, clue_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_fee_move import clue_bundle_preview
    return await clue_bundle_preview(case_id, clue_id, identity, db)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/clues/{{clue_id}}/move-case")
async def move_case_clue_to_case(case_id: int, clue_id: int, body: CaseClueMoveInput,
                                 identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_fee_move import move_case_clue
    return await move_case_clue(case_id, clue_id, body.target_case_no, identity, db)

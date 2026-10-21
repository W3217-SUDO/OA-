"""案件主体分类请求；展示命名由三个原子字段生成。"""

from typing import Literal

from pydantic import BaseModel, Field


class ClassifiedCasePartyInput(BaseModel):
    id: str = Field(default="", max_length=32)
    name: str = Field(min_length=1, max_length=256)
    party_standpoint: Literal["我方", "对方"]
    party_type: Literal["当事人", "关联方", "第三人"]
    is_client_principal: bool = False
    related_client_id: int | None = Field(default=None, gt=0)
    subject_kind: Literal["自然人", "法人", "其他组织"]
    credit_code: str = Field(default="", max_length=64)
    litigation_status: Literal["原告", "被告", "第三人", "申请人", "被申请人", "其他"]
    litigation_status_overridden: bool = False
    remark: str = Field(default="", max_length=500)

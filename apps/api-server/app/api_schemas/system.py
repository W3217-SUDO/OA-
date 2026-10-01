"""system 领域请求数据契约。"""

from pydantic import BaseModel, Field


class CacheBatchClearInput(BaseModel):
    cache_keys: list[str] = Field(default_factory=list, max_length=50)


class SystemParameterInput(BaseModel):
    category: str = Field(min_length=2, max_length=32)
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    extra: dict = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_active: bool = True


class SystemParameterUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    extra: dict | None = None
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_active: bool | None = None


class SystemParameterRelationReplaceInput(BaseModel):
    source_id: int = Field(gt=0)
    target_ids: list[int] = Field(default_factory=list, max_length=1000)


class SystemConfigUpdate(BaseModel):
    value: dict


class SystemMenuUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=64)
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_visible: bool | None = None
    is_active: bool | None = None


class SystemMenuVisibilityBatchInput(BaseModel):
    visible_keys: list[str] = Field(default_factory=list, max_length=500)


class SystemMenuInput(BaseModel):
    key: str | None = Field(default=None, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")
    parent_key: str = Field(default="", max_length=128)
    label: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=255)
    icon: str = Field(default="", max_length=64)
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_visible: bool = True
    is_active: bool = True


class ReportInput(BaseModel):
    title: str
    report_type: str
    period: str
    format: str = "CSV"
    description: str = ""

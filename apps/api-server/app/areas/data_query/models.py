"""接口结果组合查询契约；不接收 SQL、数据库地址或身份参数。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QueryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(QueryModel):
    field: str = Field(min_length=1, max_length=160, pattern=r"^[\w.-]+$")
    op: Literal["eq", "ne", "in", "not_in", "contains", "starts_with", "gt", "gte", "lt", "lte", "is_null", "not_null"]
    value: Any = None

    @model_validator(mode="after")
    def validate_value(self):
        if self.op in {"in", "not_in"}:
            if not isinstance(self.value, list) or len(self.value) > 100 or any(isinstance(x, (dict, list)) for x in self.value):
                raise ValueError("集合筛选值必须是不超过100项的标量数组")
        elif isinstance(self.value, (dict, list)):
            raise ValueError("筛选值必须是标量")
        if self.op in {"contains", "starts_with"} and not isinstance(self.value, str):
            raise ValueError("文字筛选值必须是字符串")
        return self


class Metric(QueryModel):
    name: str = Field(min_length=1, max_length=40, pattern=r"^[\w-]+$")
    op: Literal["count", "sum", "avg", "min", "max"]
    field: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^[\w.-]+$")

    @model_validator(mode="after")
    def require_field(self):
        if self.op != "count" and self.field is None:
            raise ValueError("非计数统计必须指定字段")
        return self


class Order(QueryModel):
    field: str = Field(min_length=1, max_length=160, pattern=r"^[\w.-]+$")
    direction: Literal["asc", "desc"] = "asc"


class Pagination(QueryModel):
    location: Literal["query", "body"]
    page_field: Literal["page", "page_no", "PageNo"] = "page"
    size_field: Literal["page_size", "PageSize"] = "page_size"
    page_size: int = Field(default=100, ge=1, le=100)
    total_path: str = Field(default="total", min_length=1, max_length=160, pattern=r"^[\w.-]+$")


class DataQuery(QueryModel):
    source_tool: str = Field(min_length=1, max_length=180)
    arguments: dict[str, Any] = Field(default_factory=dict)
    rows_path: str = Field(default="items", max_length=160, pattern=r"^[\w.-]*$")
    all_pages: bool = False
    pagination: Pagination | None = None
    fields: list[str] = Field(default_factory=list, max_length=30)
    where: list[Condition] = Field(default_factory=list, max_length=30)
    match: Literal["all", "any"] = "all"
    group_by: list[str] = Field(default_factory=list, max_length=4)
    metrics: list[Metric] = Field(default_factory=list, max_length=8)
    order_by: list[Order] = Field(default_factory=list, max_length=4)
    offset: int = Field(default=0, ge=0, le=5000)
    limit: int = Field(default=100, ge=1, le=200)

    @model_validator(mode="after")
    def validate_shape(self):
        import re
        for name in [*self.fields, *self.group_by]:
            if len(name) > 160 or not re.fullmatch(r"[\w.-]+", name):
                raise ValueError("字段路径无效")
        if self.all_pages != (self.pagination is not None):
            raise ValueError("全量分页查询必须提供原接口分页契约，单页查询不能指定它")
        names = [item.name for item in self.metrics]
        if len(set(names)) != len(names) or set(names).intersection(self.group_by):
            raise ValueError("统计名称不能重复或覆盖分组字段")
        if (self.metrics or self.group_by) and self.fields:
            raise ValueError("分组统计不能同时选择明细字段")
        return self

"""records 领域请求数据契约。"""

from pydantic import BaseModel, Field


class RecordInput(BaseModel):
    module: str
    serial_no: str
    title: str
    customer: str = ""
    status: str = "草稿"
    owner: str = "管理者"
    department: str = "上海分所"
    description: str = ""
    data: dict = Field(default_factory=dict)


class RecordUpdate(BaseModel):
    title: str | None = None
    customer: str | None = None
    status: str | None = None
    owner: str | None = None
    department: str | None = None
    description: str | None = None
    data: dict | None = None


class TransitionInput(BaseModel):
    to_status: str
    comment: str = ""

"""tasks 领域请求数据契约。"""

from datetime import date, datetime
from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    clue_ids: list[int] = Field(default_factory=list, max_length=100)
    title: str
    customer: str = ""
    owner: str
    deadline: date
    priority: str = "普通"
    source: str = "日常任务"
    task_type: str = ""
    collaborators: list[str] = Field(default_factory=list, max_length=20)
    case_no: str = ""
    case_nos: list[str] = Field(default_factory=list, max_length=100)
    case_record_id: int | None = Field(default=None, gt=0)
    case_module: str = Field(default="case", pattern="^(case|ipr_case)$")
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str = ""
    is_vip: bool = False


class VipTaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    customer: str = Field(default="", max_length=255)
    owner: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="普通", max_length=32)
    status: str = Field(default="待处理", max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str = Field(default="", max_length=10000)
    collaborators: list[str] = Field(default_factory=list, max_length=20)


class VipTaskUpdateInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    customer: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, min_length=1, max_length=64)
    priority: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str | None = Field(default=None, max_length=10000)
    collaborators: list[str] | None = Field(default=None, max_length=20)


class VipTaskNodeInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="普通", max_length=32)
    status: str = Field(default="待处理", max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str = Field(default="", max_length=10000)
    participants: list[str] = Field(default_factory=list, max_length=20)


class VipTaskNodeUpdateInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    owner: str | None = Field(default=None, min_length=1, max_length=64)
    priority: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    start_at: datetime | None = None
    deadline: date | None = None
    end_at: datetime | None = None
    description: str | None = Field(default=None, max_length=10000)
    participants: list[str] | None = Field(default=None, max_length=20)


class VipTaskMessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    recipients: list[str] = Field(default_factory=list, max_length=30)
    node_id: int | None = Field(default=None, gt=0)


class VipTaskMessageReadInput(BaseModel):
    message_ids: list[int] = Field(default_factory=list, max_length=100)


class TaskHandoffInput(BaseModel):
    recipient: str
    comment: str = ""
    end_at: datetime | None = None


class TaskActionInput(BaseModel):
    comment: str = ""


class TaskExceptionRequestInput(BaseModel):
    action: str = Field(pattern="^(挂起|取消)$")
    reason: str = Field(min_length=2, max_length=1000)


class TaskExceptionReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class TaskBatchUpdateInput(BaseModel):
    task_ids: list[int] = Field(min_length=1, max_length=100)
    owner: str | None = Field(default=None, max_length=128)
    deadline: date | None = None
    priority: str | None = None
    is_vip: bool | None = None
    comment: str = Field(default="", max_length=1000)


class TaskBatchLifecycleInput(BaseModel):
    task_ids: list[int] = Field(min_length=1, max_length=100)
    action: str = Field(pattern="^(accept|complete|confirm|handoff|withdraw)$")
    recipient: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=1000)


class TaskBatchReadInput(BaseModel):
    """Selected task rows on the personal unread-message page."""
    task_ids: list[int] = Field(min_length=1, max_length=100)


class CaseTaskFinishedInput(BaseModel):
    """Legacy CaseTaskController.Finished payload: cases, never task ids."""
    case_ids: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=1000)

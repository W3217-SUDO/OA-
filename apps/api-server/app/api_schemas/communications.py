"""communications 领域请求数据契约。"""

from datetime import datetime
from pydantic import BaseModel, Field


class UserMessageInput(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=4000)


class CommunicationLogInput(BaseModel):
    customer_record_id: int
    contact: str = Field(default="", max_length=128)
    phone: str = Field(default="", max_length=64)
    content: str = Field(min_length=1, max_length=4000)
    occurred_at: datetime


class CommunicationLogUpdate(BaseModel):
    contact: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    occurred_at: datetime | None = None

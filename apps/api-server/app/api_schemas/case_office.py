"""案件 Office 编辑器请求契约。"""

from typing import Literal

from pydantic import BaseModel, Field


class OfficeCallbackInput(BaseModel):
    key: str = Field(pattern=r"^[a-f0-9]{32}$")
    status: Literal[1, 2, 3, 4, 6, 7]
    url: str | None = Field(default=None, max_length=8192)
    filetype: str | None = Field(default=None, max_length=16)
    users: list[str] = Field(default_factory=list, max_length=100)
    forcesavetype: int | None = Field(default=None, ge=0, le=3)
    userdata: str | None = Field(default=None, max_length=128)

"""identity 领域请求数据契约。"""

from pydantic import BaseModel, Field


class SystemUserInput(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    department: str = Field(default="上海分所", min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str | None = None
    role_ids: list[str] | None = None
    is_active: bool = True
    # An administrator-issued password is always one-time.  Keep accepting
    # this legacy request field for API compatibility, but never allow a
    # caller to opt a newly created account out of the first-login change.
    must_change_password: bool = True
    manager_id: int | None = Field(default=None, gt=0)
    access_level: str = Field(default="", max_length=64)
    lead_rate: str = Field(default="", max_length=32)
    copy_rate: str = Field(default="", max_length=32)
    profile: dict = Field(default_factory=dict)


class SystemUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=64)
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    department: str | None = Field(default=None, min_length=1, max_length=64)
    role: str | None = None
    role_ids: list[str] | None = None
    manager_id: int | None = Field(default=None, ge=0)
    access_level: str | None = Field(default=None, max_length=64)
    lead_rate: str | None = Field(default=None, max_length=32)
    copy_rate: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    profile: dict | None = None


class UserPermissionOverrideUpdate(BaseModel):
    menu_keys: list[str] | None = None
    field_keys: list[str] | None = None
    data_scope: str | None = None
    clear: bool = False


class SystemUserPasswordResetInput(BaseModel):
    """Administrator-issued one-time password for an existing account."""

    new_password: str = Field(min_length=8, max_length=128)


class CurrentUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    email: str | None = Field(default=None, max_length=128)
    office_phone: str | None = Field(default=None, max_length=32)
    mobile: str | None = Field(default=None, max_length=32)
    menu_auto_collapse: str | None = Field(default=None, pattern="^(yes|no)$")
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class DingTalkLoginInput(BaseModel):
    auth_code: str = Field(min_length=1, max_length=512)


class DingTalkBindInput(DingTalkLoginInput):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class DingTalkBindingInput(BaseModel):
    user_id: str = Field(default="", max_length=128)


class RolePermissionUpdate(BaseModel):
    data_scope: str = Field(min_length=1, max_length=64)
    menu_keys: list[str]
    field_keys: list[str]
    action_keys: list[str] | None = None


class SecurityPolicyUpdate(BaseModel):
    min_password_length: int = Field(ge=8, le=32)
    max_failed_attempts: int = Field(ge=3, le=10)
    lock_minutes: int = Field(ge=1, le=1440)
    token_minutes: int = Field(ge=15, le=1440)

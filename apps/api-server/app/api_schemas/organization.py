"""organization 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field


class HrTransitionInput(BaseModel):
    to_status: str
    effective_date: date = Field(default_factory=date.today)
    reason: str = ""
    handover_to: str = ""
    comment: str = ""


class HrEmployeeBatchDeleteInput(BaseModel):
    employee_ids: list[int] = Field(min_length=1, max_length=100)


class HrSubrecordInput(BaseModel):
    kind: str = Field(pattern="^(leave|matter|commission)$")
    data: dict = Field(default_factory=dict)


class HrPerformanceInput(BaseModel):
    employee_id: int = Field(gt=0)
    data: dict = Field(default_factory=dict)


class HrSubrecordUpdate(BaseModel):
    data: dict


class DepartmentInput(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    parent_department_id: int | None = Field(default=None, ge=1)
    manager: str = Field(default="", max_length=64)
    overdue_deduction: bool = False
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    parent_department_id: int | None = Field(default=None, ge=1)
    manager: str | None = Field(default=None, max_length=64)
    overdue_deduction: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_active: bool | None = None


class JobRoleInput(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    permissions: list[str] = Field(default_factory=list, max_length=50)
    field_keys: list[str] = Field(default_factory=list, max_length=50)
    field_keys_configured: bool = False
    data_scope: str | None = Field(default=None, max_length=64)
    description: str = Field(default="", max_length=1000)
    sort_order: int = Field(default=0, ge=0, le=99999)
    is_active: bool = True


class JobRoleUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    permissions: list[str] | None = Field(default=None, max_length=50)
    field_keys: list[str] | None = Field(default=None, max_length=50)
    field_keys_configured: bool | None = None
    data_scope: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = Field(default=None, ge=0, le=99999)
    is_active: bool | None = None


class JobRolePermissionUpdate(BaseModel):
    permissions: list[str] = Field(default_factory=list)
    case_actions_explicit: bool = False
    field_keys: list[str] | None = Field(default=None, max_length=50)
    field_keys_configured: bool | None = None
    data_scope: str | None = Field(default=None, max_length=64)


class HrEmployeeUpdateInput(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    department: str = Field(min_length=1, max_length=64)
    role: str
    position: str = Field(min_length=1, max_length=128)
    is_active: bool = True
    email: str = Field(default="", max_length=128)
    mobile: str = Field(default="", max_length=32)
    office_phone: str = Field(default="", max_length=32)
    joined_at: date
    left_at: date | None = None
    data: dict = Field(default_factory=dict)


class HrEmployeeLoginStatusInput(BaseModel):
    is_active: bool


class HrEmployeeContractApprovalStatusInput(BaseModel):
    contract_approval_enabled: bool


class HrEmployeeSealApprovalStatusInput(BaseModel):
    seal_approval_enabled: bool


class HrEmployeeCreateInput(BaseModel):
    # Only an "employee account" has a system-login counterpart.  Keeping this
    # optional lets HR retain customer/external personnel files without creating
    # a privileged or orphaned system account by accident.
    username: str = Field(default="", max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    employee_no: str = Field(min_length=1, max_length=64)
    company: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=64)
    password: str = Field(default="", max_length=128)
    role: str = "user"
    position: str = Field(min_length=1, max_length=128)
    is_active: bool = True
    account_type: str = Field(default="员工账号", max_length=32)
    data: dict = Field(default_factory=dict)


class LawFirmInput(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    registered_address: str = Field(default="", max_length=255)
    business_address: str = Field(default="", max_length=255)
    detail_address: str = Field(default="", max_length=255)
    postal_code: str = Field(default="", max_length=32)
    phone: str = Field(default="", max_length=64)
    fax: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=128)
    organization_code: str = Field(default="", max_length=64)
    company_code: str = Field(default="", max_length=64)
    firm_type: str = Field(default="", max_length=64)
    firm_level: str = Field(default="", max_length=32)
    country: str = Field(default="中国", max_length=64)
    is_active: bool = True
    default_contact: "LawFirmContactInput | None" = None


class LawFirmContactInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    address: str = Field(default="", max_length=255)
    postal_code: str = Field(default="", max_length=32)
    phone: str = Field(default="", max_length=64)
    fax: str = Field(default="", max_length=64)
    email: str = Field(default="", max_length=128)
    is_active: bool = True

LawFirmInput.model_rebuild()

"""customers 领域请求数据契约。"""

from pydantic import BaseModel, Field, field_validator


class CustomerShareInput(BaseModel):
    recipients: list[str] = Field(max_length=200)
    comment: str = ""

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if value and not normalized:
            raise ValueError("共享人员不能仅包含空白值；取消共享请提交空列表")
        return normalized


class CustomerActionInput(BaseModel):
    comment: str = ""


class CustomerContactInput(BaseModel):
    name: str
    project_role: str = ""
    phone: str = ""
    office_phone: str = ""
    im_account: str = ""
    email: str = ""
    position: str = ""
    contact_status: str = "正常联系"
    is_valid: bool = True
    is_primary: bool = False
    is_received_email: bool = True
    is_contacted: bool = True
    is_people_base: bool = True
    remark: str = ""


class CustomerManagersInput(BaseModel):
    managers: list[str] = Field(min_length=1, max_length=20)
    comment: str = ""


class CustomerPatchInput(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    data: dict = Field(default_factory=dict)


class CustomerEventInput(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=4000)


class CustomerContactStatusInput(BaseModel):
    is_valid: bool | None = None
    is_primary: bool | None = None


class CustomerNoteInput(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    note_type: str = Field(default="跟进记录", max_length=32)


class CustomerLevelChangeInput(BaseModel):
    level: str = Field(min_length=2, max_length=32)
    comment: str = Field(default="", max_length=1000)


class CustomerLevelReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class CustomerKeyChangeInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    credit_code: str = Field(default="", max_length=64)
    comment: str = Field(min_length=2, max_length=1000)


class CustomerKeyChangeReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class CustomerPortalActionInput(BaseModel):
    account: str = Field(default="", max_length=128)
    comment: str = Field(default="", max_length=1000)


class CustomerPortalLoginInput(BaseModel):
    account: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class CustomerPortalDemandInput(CustomerPortalLoginInput):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=2000)
    case_no: str = Field(default="", max_length=128)


class CustomerPortalActivationInput(BaseModel):
    account: str = Field(min_length=3, max_length=128)
    activation_code: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class CustomerCreateInput(BaseModel):
    serial_no: str = ""
    title: str = ""
    status: str = ""
    owner: str = ""
    department: str = ""
    description: str = ""
    customer_managers: list[str] = Field(default_factory=list, max_length=20)
    customer_type: str | None = None
    organization_type: str | None = None
    identity_no: str | None = None
    level: str | None = None
    is_shared: str | bool | None = None
    is_assisted: str | bool | None = None
    fee_reduction: str | bool | None = None
    contact: str | list[str] | None = None
    contact_accounts: list[str] = Field(default_factory=list, max_length=20)
    phone: str | None = None
    credit_code: str | None = None
    legal_representative: str | None = None
    registered_address: str | None = None
    invoice_title: str | None = None
    taxpayer_id: str | None = None
    invoice_address: str | None = None
    invoice_phone: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    short_name: str | None = None
    fax: str | None = None
    legal_agent_id_no: str | None = None
    legal_agent_title: str | None = None
    customer_source: str | None = None
    file_date: str | None = None
    province: str | None = None
    postal_code: str | None = None
    patent_customer_type: str | None = None
    industry: str | None = None
    output_value: str | None = None
    cooperation_status: str | None = None
    gb_classification: str | None = None
    website: str | None = None
    organization_nature: str | None = None
    organization_code: str | None = None
    registration_region: str | None = None
    registration_postal_code: str | None = None
    registered_capital: str | None = None
    registration_year: str | None = None
    data: dict = Field(default_factory=dict)

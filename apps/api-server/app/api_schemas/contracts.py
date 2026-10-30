"""contracts 领域请求数据契约。"""

from datetime import date
from pydantic import BaseModel, Field, model_validator

from app.api_schemas.data_keys import CONTRACT_DATA_KEYS, CONTRACT_FEE_MODE_COMMON, CONTRACT_TYPE_COMMON, data_schema, merge_named


class ContractAttachmentBatchDeleteInput(BaseModel):
    file_ids: list[int] = Field(default_factory=list, max_length=100)
    fileIds: list[int] = Field(default_factory=list, max_length=100)
    attachment_ids: list[int] = Field(default_factory=list, max_length=100)


class ContractWholeDeleteInput(BaseModel):
    """Legacy FCM ContractDelete body: accepts snake_case and camelCase ids."""
    contract_ids: list[int] = Field(default_factory=list, max_length=200)
    contractIds: list[int] = Field(default_factory=list, max_length=200)


class ContractSubmitInput(BaseModel):
    approvers: list[str] = Field(min_length=1, max_length=10, description=(
        "合同审批人账号。前置条件：必须是 GET /contracts/approver-settings 返回中 selected=true 的 username；"
        "合同须至少已有一份“合同附件”，否则提交被拒。"))
    comment: str = Field(default="", description="提交说明")
    sync_seal: bool = False  # 是否同步申请合同用印


class ContractApproverSettingsInput(BaseModel):
    usernames: list[str] = Field(default_factory=list, max_length=200)


class ContractDraftInput(BaseModel):
    serial_no: str = Field(default="", max_length=128)
    title: str = Field(min_length=1, max_length=255, description="合同名称（不能与未删除、未归档合同重名）")
    customer: str = Field(min_length=1, max_length=255, description="客户名称（须与客户档案名称一致）")
    owner: str = Field(min_length=1, max_length=64, description="负责人账号；普通账号由服务器改为本人")
    department: str = Field(min_length=1, max_length=64, description="所属部门；非管理员由服务器改为本人部门")
    staff_id: int | None = Field(default=None, gt=0)
    description: str = Field(default="", max_length=2000, description="备注")
    data: dict = Field(default_factory=dict, json_schema_extra=data_schema(CONTRACT_DATA_KEYS, "合同扩展字段"))
    # 以下具名参数与 data 中同义键二选一，服务器归并进 data（data.type 等旧写法继续有效）。
    contract_type: str | None = Field(default=None, max_length=64, description="合同类别，归并为 data.type。常用值：" + "、".join(CONTRACT_TYPE_COMMON))
    fee_type: str | None = Field(default=None, max_length=64, description="收费模式，归并为 data.fee_type。常用值：" + "、".join(CONTRACT_FEE_MODE_COMMON))
    contract_body: str | None = Field(default=None, pattern="^(律所|平台)$", description="合同主体：律所/平台，归并为 data.contract_body")
    external_contract_numbers: list[str] | None = Field(default=None, max_length=20, description="外部合同号（可多个），归并为 data.external_contract_numbers")
    amount: float | None = Field(default=None, ge=0, description="合同金额，归并为 data.amount")
    signed_at: date | None = Field(default=None, description="签订日期，归并为 data.signed_at")
    end_date: date | None = Field(default=None, description="合同截止日期，归并为 data.end_date")
    attachment_ids: list[int] = Field(default_factory=list, max_length=20, description=(
        "合同附件：本人已上传、尚未关联业务的附件 ID（如 MCP 先调 /agent-tools/upload 得到的 id）；保存后复制挂到本合同，类别“合同附件”。"
        "原“先建合同再上传附件”的两步方式继续可用。"))

    @model_validator(mode="after")
    def _merge_named_fields(self):
        named = {"type": self.contract_type, "fee_type": self.fee_type, "contract_body": self.contract_body,
                 "external_contract_numbers": self.external_contract_numbers, "amount": self.amount,
                 "signed_at": self.signed_at.isoformat() if self.signed_at else None,
                 "end_date": self.end_date.isoformat() if self.end_date else None}
        self.data = merge_named(self.data, named, "合同")
        return self


class ContractApprovalInput(BaseModel):
    approved: bool
    comment: str = ""
    action_key: str = Field(default="", max_length=128)


class ContractSealApplicationInput(BaseModel):
    approver: str = Field(min_length=1, max_length=100)
    seal_asset_id: int
    copies: int = Field(ge=1, le=999)
    purpose: str = Field(min_length=1, max_length=500)
    use_date: date
    delivery_method: str = "现场用印"
    document_names: str = ""
    source_attachment_ids: list[int] = Field(default_factory=list, max_length=100)
    description: str = ""
    submit: bool = False


class ContractInvestigationInput(BaseModel):
    """前置条件：合同不能是草稿；管理员须已在人员管理配置“调查任务分配人员”（owner 只能是该调查主管）。"""
    title: str = Field(min_length=2, max_length=200, description="调查任务标题")
    owner: str = Field(default="", max_length=100, description="分配人：系统配置的调查主管账号；留空即用该主管")
    authorized_from: date = Field(description="授权开始日期")
    authorized_to: date = Field(description="授权结束日期")
    authorization_range: str | None = Field(default=None, max_length=300, description="授权范围（页面“授权范围”，如 全国）。新名称，等同旧参数 region")
    authorization_area: str | None = Field(default=None, max_length=1000, description="授权区域（页面“授权区域”，如 全国 或具体省市）。新名称，等同旧参数 authorization_scope")
    region: str = Field(default="", max_length=300, description="旧参数名，含义是“授权范围”；建议改用 authorization_range")
    authorization_scope: str = Field(default="", max_length=1000, description="旧参数名，含义是“授权区域”；建议改用 authorization_area")
    attachment_ids: list[int] = Field(default_factory=list, max_length=100, description="调查资料附件 ID（本人上传、未关联业务）")
    right_type: str = Field(default="商标", max_length=50, description="权利类型，如 商标、专利、著作权")
    customer_review: bool = Field(default=False, description="线索是否需要客户审核")
    description: str = Field(default="", max_length=2000, description="备注")

    @model_validator(mode="after")
    def _merge_new_names(self):
        for new, old in (("authorization_range", "region"), ("authorization_area", "authorization_scope")):
            value = getattr(self, new)
            if value is None:
                continue
            if getattr(self, old) and getattr(self, old) != value:
                raise ValueError(f"{new} 与旧参数 {old} 不一致，请只保留一处")
            setattr(self, old, value)
        return self


class ContractChangeInput(BaseModel):
    change_type: str
    reason: str = Field(min_length=2, max_length=1000)
    contract_body: str | None = None
    contract_type: str | None = None
    fee_type: str | None = None
    title: str | None = None
    amount: float | None = Field(default=None, ge=0)
    description: str | None = None
    external_contract_no: str | None = None
    external_contract_numbers: list[str] | None = Field(default=None, max_length=50)
    end_date: date | None = None
    signed_at: date | None = None
    owner: str | None = Field(default=None, max_length=64)
    department: str | None = Field(default=None, max_length=128)
    # 已审批通过的合同变更后重新进入合同审批，审批人与新建合同审批同一名单（BUG20261030012）。
    approvers: list[str] = Field(default_factory=list, max_length=1)


class ContractChangeReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class ContractEventInput(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class ContractObjectInput(BaseModel):
    case_record_id: int
    fee_type: str = Field(min_length=1, max_length=64)
    amount: float = Field(ge=0, le=999999999)
    remark: str = Field(default="", max_length=2000)


class ContractArchiveClosureInput(BaseModel):
    case_fee_ids: list[int] = Field(min_length=1, max_length=200)
    fee_archived: bool = True
    comment: str = Field(default="", max_length=1000)


class ContractPaymentLineInput(BaseModel):
    # Legacy contract payment screens select individual case-fee rows. Keep
    # contract_object_id for backwards compatibility, while allowing the
    # precise fee row to be submitted when available.
    contract_object_id: int | None = Field(default=None, gt=0)
    case_fee_id: int | None = Field(default=None, gt=0)
    amount: float = Field(gt=0, le=999999999)
    remark: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def require_target(self):
        if not self.contract_object_id and not self.case_fee_id:
            raise ValueError("必须选择合同标的或案件费用")
        return self


class ContractPaymentApplicationInput(BaseModel):
    payment_type_id: int = Field(gt=0)
    payer_name: str = Field(default="", max_length=200)
    application_date: date
    remark: str = Field(default="", max_length=2000)
    lines: list[ContractPaymentLineInput] = Field(min_length=1, max_length=100)


class ContractPaymentReviewInput(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


class ContractPaymentPayInput(BaseModel):
    paid_date: date
    voucher_no: str = Field(min_length=1, max_length=128)
    comment: str = Field(default="", max_length=1000)


class ContractPaymentWriteoffInput(BaseModel):
    writeoff_date: date
    voucher_no: str = Field(min_length=2, max_length=128)
    comment: str = Field(default="", max_length=1000)

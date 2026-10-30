"""records 领域请求数据契约。"""

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.api_schemas.data_keys import CLUE_DATA_KEYS, data_schema, merge_named


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


class ClueIndictee(BaseModel):
    name: str = Field(min_length=1, max_length=256, description="被调查主体名称")


class _ClueNamedFields(BaseModel):
    """线索字段的具名参数：与 data 中同名键等价，服务器归并进 data。"""
    source_task_id: int | None = Field(default=None, gt=0, description="线索：来源调查任务/子任务 ID，归并为 data.source_task_id（新建必填）")
    infringement_method: str | None = Field(default=None, max_length=200, description="线索：侵权方式")
    sales_channel: str | None = Field(default=None, max_length=200, description="线索：销售渠道（必填，如 电商平台、实体店铺），同时写入 data.platform")
    product: str | None = Field(default=None, max_length=500, description="线索：侵权产品（必填；一条线索只对应一个品牌、一个侵权产品）")
    store_url: str | None = Field(default=None, max_length=2000, description="线索：店铺链接")
    shop_name: str | None = Field(default=None, max_length=500, description="线索：店铺名称")
    shop_id: str | None = Field(default=None, max_length=200, description="线索：店铺 ID")
    has_product: bool | None = Field(default=None, description="线索：有无产品")
    product_url: str | None = Field(default=None, max_length=2000, description="线索：产品链接")
    sale_num: str | None = Field(default=None, max_length=200, description="线索：规模/销量")
    address: str | None = Field(default=None, max_length=1000, description="线索：调查地址")
    investigated_at: date | None = Field(default=None, description="线索：调查日期")
    producer: str | None = Field(default=None, max_length=500, description="线索：生产商")
    indictees: list[ClueIndictee] | None = Field(default=None, max_length=20, description="线索：主体信息（被调查主体）")
    investigation_assistant: str | None = Field(default=None, max_length=200, description="线索：调查辅助员")
    right_type: str | None = Field(default=None, max_length=50, description="权利类型，如 商标、专利、著作权")
    source_owner: str | None = Field(default=None, max_length=100, description="案源人")
    region: str | None = Field(default=None, max_length=300, description="调查区域")
    source: str | None = Field(default=None, max_length=200, description="来源")

    def _clue_named(self) -> dict:
        named = {key: getattr(self, key) for key in (
            "source_task_id", "infringement_method", "sales_channel", "product", "store_url", "shop_name", "shop_id", "has_product",
            "product_url", "sale_num", "address", "producer", "investigation_assistant", "right_type", "source_owner", "region", "source")}
        named["investigated_at"] = self.investigated_at.isoformat() if self.investigated_at else None
        if self.indictees is not None:
            named["indictees"] = [item.model_dump() for item in self.indictees]
            named["indictee"] = self.indictees[0].name if self.indictees else ""
        if self.sales_channel is not None:
            named["platform"] = self.sales_channel
        return named


class InvestigationRecordInput(_ClueNamedFields, RecordInput):
    """调查中心新建记录。module=clue 时新建线索：须给 data.source_task_id（或具名参数 source_task_id），且只能挂在本人负责的调查任务下；
    serial_no、title 传空字符串，线索编号由服务器生成，状态固定为“草稿”。"""
    module: str = Field(description="investigation=调查任务（须带 data.contract_record_id）；clue=调查线索")
    serial_no: str = Field(description="调查任务编号；线索传空字符串（服务器生成）")
    title: str = Field(description="调查任务标题；线索传空字符串")
    data: dict = Field(default_factory=dict, json_schema_extra=data_schema(CLUE_DATA_KEYS, "调查记录扩展字段（线索字段见 properties）"))
    attachment_ids: list[int] = Field(default_factory=list, max_length=20, description=(
        "线索附件：本人已上传、未关联业务的附件 ID；保存后挂到本线索（类别“调查线索附件”）。原两步上传方式继续可用。"))

    @model_validator(mode="after")
    def _merge_named_fields(self):
        self.data = merge_named(self.data, self._clue_named(), "调查记录")
        return self

    def record_payload(self) -> dict:
        """只取通用记录字段（具名参数已归并进 data）。"""
        return self.model_dump(include=set(RecordInput.model_fields))


class RecordUpdate(BaseModel):
    title: str | None = None
    customer: str | None = None
    status: str | None = None
    owner: str | None = None
    department: str | None = None
    description: str | None = None
    data: dict | None = None


class InvestigationRecordUpdate(_ClueNamedFields, RecordUpdate):
    """修改调查记录/线索：只改传入的字段；线索字段可用具名参数或 data，服务器只接受可编辑的线索键并与原 data 合并。
    状态只能按“暂存（草稿）/提交审批（待审批）”变更，调查员须走分配入口修改。"""
    data: dict | None = Field(default=None, json_schema_extra=data_schema(CLUE_DATA_KEYS, "调查记录扩展字段（线索字段见 properties）"))

    @model_validator(mode="after")
    def _merge_named_fields(self):
        named = {key: value for key, value in self._clue_named().items() if value is not None}
        if named:
            self.data = merge_named(self.data, named, "调查记录")
        return self


class TransitionInput(BaseModel):
    to_status: str
    comment: str = ""

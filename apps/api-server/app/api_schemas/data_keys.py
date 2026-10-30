"""合同、调查线索、客户 data 对象的已知键：写进接口 schema 说明（MCP 原子工具可见），并供具名字段归并进 data。

只描述、不收紧：data 仍接受其他键（前端和历史数据照常可用）；真正的校验仍在各业务入口。
"""

from typing import Any

CUSTOMER_ORGANIZATION_TYPE_VALUES = ["公司企业", "个人", "个体工商户", "事业单位", "机关团体", "其他"]
CASE_CLIENT_POSITION_VALUES = ["原告/申请人", "被告/被申请人", "第三人", "被告人/犯罪嫌疑人", "被害人"]
CASE_TYPE_VALUES = ["民事案件", "刑事案件", "行政案件及国家赔偿", "法律顾问", "仲裁"]
CONTRACT_TYPE_COMMON = ["法律顾问合同", "争议解决合同", "框架合作合同", "非诉项目合同", "其他"]
CONTRACT_FEE_MODE_COMMON = ["固定收费", "固定+后期", "免费代理", "法律援助", "计时收费", "全风险代理"]
CLUE_STATUS_VALUES = ["草稿", "待审批", "待客户审核", "已驳回", "已拒绝", "待取证", "已取证", "已转案件"]

S: dict[str, Any] = {"type": "string"}


def _s(text: str, **extra) -> dict:
    return {**S, "description": text, **extra}


CONTRACT_DATA_KEYS: dict[str, dict] = {
    "type": _s("合同类别（页面“合同类别”；具名参数 contract_type）。常用值：" + "、".join(CONTRACT_TYPE_COMMON)),
    "fee_type": _s("收费模式。常用值：" + "、".join(CONTRACT_FEE_MODE_COMMON)),
    "contract_body": _s("合同主体：律所 或 平台；平台费用必须挂平台合同", enum=["律所", "平台"]),
    "external_contract_numbers": {"type": "array", "items": S, "description": "外部合同号（可多个；只有客户管理人能改）"},
    "external_contract_no": _s("第一个外部合同号（服务器按 external_contract_numbers 自动填）"),
    "amount": {"type": "number", "minimum": 0, "description": "合同金额"},
    "signed_at": _s("签订日期 YYYY-MM-DD", format="date"),
    "end_date": _s("合同截止日期 YYYY-MM-DD", format="date"),
    "customer_id": {"type": "integer", "description": "客户 ID（服务器按 customer 名称核对后写入）"},
    "customer_no": _s("客户编号（服务器写入）"),
}

CLUE_DATA_KEYS: dict[str, dict] = {
    "source_task_id": {"type": "integer", "description": "来源调查任务/子任务 ID（新建线索必填；只能是本人负责的任务）"},
    "source_task_no": _s("来源任务编号"),
    "infringement_method": _s("侵权方式"),
    "sales_channel": _s("销售渠道（必填，如 电商平台、实体店铺）；服务器同时写入 platform"),
    "platform": _s("同 sales_channel（旧导出字段）"),
    "product": _s("侵权产品（必填；一条线索只对应一个品牌、一个侵权产品）"),
    "store_url": _s("店铺链接"), "shop_name": _s("店铺名称"), "shop_id": _s("店铺 ID"),
    "has_product": {"type": "boolean", "description": "有无产品"},
    "product_url": _s("产品链接"), "sale_num": _s("规模/销量"), "address": _s("调查地址"),
    "investigated_at": _s("调查日期 YYYY-MM-DD", format="date"), "producer": _s("生产商"),
    "indictee": _s("第一个被调查主体名称（服务器按 indictees 填）"),
    "indictees": {"type": "array", "items": {"type": "object", "properties": {"name": S}}, "description": "主体信息（被调查主体）"},
    "investigation_assistant": _s("调查辅助员"), "right_type": _s("权利类型，如 商标、专利、著作权"),
    "source_owner": _s("案源人"), "region": _s("调查区域"), "source": _s("来源"),
}

CUSTOMER_DATA_LABELS = {
    "contact": "客户联系人账号", "contact_accounts": "客户联系人账号列表", "phone": "电话", "credit_code": "统一社会信用代码（非个人必填）",
    "legal_representative": "法人姓名", "registered_address": "注册地址", "invoice_title": "发票抬头", "taxpayer_id": "纳税人识别号",
    "invoice_address": "开票地址", "invoice_phone": "开票电话", "bank_name": "开户行", "bank_account": "帐号",
    "customer_type": "客户类型（取 GET /customers/reference-options 的 customer_types）",
    "organization_type": "组织类型：" + "、".join(CUSTOMER_ORGANIZATION_TYPE_VALUES) + "（个人填 identity_no，其他填 credit_code）",
    "identity_no": "身份证号（个人必填）", "short_name": "客户简称", "fax": "传真", "legal_agent_id_no": "法人身份证号",
    "legal_agent_title": "法人职务", "customer_source": "客户来源", "is_shared": "是否共享", "is_assisted": "上海市资助信息",
    "file_date": "建档日期 YYYY-MM-DD", "level": "客户等级", "province": "省市县", "postal_code": "邮编",
    "patent_customer_type": "专利客户类型", "fee_reduction": "费减", "industry": "行业", "output_value": "产值",
    "cooperation_status": "合作状态", "gb_classification": "国标分类", "website": "网址", "organization_nature": "单位性质",
    "organization_code": "组织机构代码", "registration_region": "注册地区", "registration_postal_code": "注册地邮编",
    "registered_capital": "注册资本", "registration_year": "注册年份",
}
CUSTOMER_DATA_KEYS: dict[str, dict] = {
    key: ({**_s(label), "enum": CUSTOMER_ORGANIZATION_TYPE_VALUES} if key == "organization_type" else _s(label))
    for key, label in CUSTOMER_DATA_LABELS.items()
}
CUSTOMER_DATA_KEYS["contact_accounts"] = {"type": "array", "items": S, "description": CUSTOMER_DATA_LABELS["contact_accounts"]}
for _flag in ("is_shared", "is_assisted", "fee_reduction"):
    CUSTOMER_DATA_KEYS[_flag] = {"anyOf": [{"type": "boolean"}, S], "description": CUSTOMER_DATA_LABELS[_flag]}


def data_schema(keys: dict[str, dict], title: str) -> dict:
    """data 字段的 json_schema_extra：列出已知键，仍允许其他键。"""
    return {"properties": keys, "additionalProperties": True,
            "description": f"{title}。已知键见 properties；也可直接用同名顶层参数，服务器会归并进 data。其他键按原样保存。"}


def merge_named(data: dict | None, named: dict[str, Any], label: str) -> dict:
    """把顶层具名参数归并进 data；同一键两处都给且不一致时报错，避免静默覆盖。"""
    result = dict(data or {})
    for key, value in named.items():
        if value is None:
            continue
        if key in result and result[key] not in (None, "", []) and result[key] != value:
            raise ValueError(f"{label}：参数 {key} 与 data.{key} 不一致，请只保留一处")
        result[key] = value
    return result

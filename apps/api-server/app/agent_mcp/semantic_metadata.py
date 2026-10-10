"""MCP 目录的业务语义及可审计的安全分类。"""

import re

from fastapi.routing import APIRoute

from app.config import settings


# 这些 POST 已逐项核对原处理函数及其查询调用链，不写业务记录。
READ_ONLY_POSTS = {
    ("POST", "/customers/{customer_id}/shared-objects", "list_customer_shared_objects"): "仅读取客户共享对象与负责人",
    ("POST", "/cases/{case_id}/commission-preview", "preview_case_commissions_for_amount"): "仅按金额计算案件提成预览",
    ("POST", "/finance/payment-packages/preview", "preview_internal_payment_package"): "仅计算付款包预览，不保存付款包",
    ("POST", "/cases/counsel/search", "search_counsel_cases"): "法律顾问案件分页查询",
    ("POST", "/cases/search", "search_ordinary_cases"): "普通案件分页及阶段统计查询",
    ("POST", "/cases/archive/search", "search_case_archive"): "归档案件分页查询",
    ("POST", "/WMS/Warehouse/GoodsList", "warehouse_goods_list"): "仓库证物分页查询",
    ("POST", "/WMS/WarehouseStorageLocation/GetStorageLocationGoodsCountList", "warehouse_storage_location_goods_count_list"): "仓库库位及证物数量查询",
    ("POST", "/hr/employees/batch-deletion-impact", "get_hr_employee_batch_deletion_impact"): "只查询员工删除阻断项，不执行删除",
    ("POST", "/investigations/clues/case-contracts", "resolve_clue_case_contracts"): "仅根据线索案件编号查询可见合同关联",
    ("POST", "/cases/counsel/export", "export_counsel_cases"): "查询法律顾问案件并在内存中导出 CSV",
    ("POST", "/cases/archive/export", "export_case_archive"): "查询归档案件并在内存中导出 CSV 或 Excel",
    ("POST", "/official-outgoing/download", "download_official_outgoing_documents"): "仅读取已审批发文附件并在内存中打包 ZIP",
    ("POST", "/cases/attachments/download", "download_case_attachments"): "仅读取可见案件附件并在内存中打包 ZIP",
    ("POST", "/seals/applications/batch-download", "batch_download_seal_files"): "仅读取可见用印附件并在内存中打包 ZIP",
    ("POST", "/seals/applications/package-download", "package_download_seal_files"): "用印附件只读打包下载的原挂载别名",
}

# Word 内容 GET 会取得持久化编辑锁；不能以路由别名代替实际处理函数分类。
SIDE_EFFECT_GETS = {
    ("GET", "/cases/{case_id}/attachments/{attachment_id}/word-editor/content", "get_case_word_editor_content"): "读取 Word 内容并取得持久化编辑锁",
    ("GET", "/system/security-policy", "get_security_policy"): "首次读取可能创建安全策略配置",
}

# 原挂载处理函数明确返回 CSV；旧 OpenAPI 未声明这些响应类型。
RESPONSE_MEDIA_TYPES = {
    ("GET", "/records/import-template", "records_import_template"): ("text/csv",),
    ("GET", "/investigations/clues/import-template", "clue_import_template"): ("text/csv",),
    ("GET", "/investigations/notaries/import-template", "notary_import_template"): ("text/csv",),
}


def operation_key(route: APIRoute, method: str) -> tuple[str, str, str]:
    return method, route.path.removeprefix(settings.api_prefix), route.endpoint.__name__

_CREDENTIAL_ENDPOINTS = {
    "create_system_user", "update_system_user", "delete_system_user",
    "reset_system_user_password", "unlock_system_user", "bind_system_user_dingtalk",
    "get_security_policy", "update_security_policy",
    "update_hr_employee_account_status", "open_customer_portal", "close_customer_portal",
    "create_office_preview_link", "stream_office_preview_attachment",
}

_CREDENTIAL_FIELDS = {"password", "current_password", "new_password", "client_secret", "access_token", "refresh_token", "api_key", "secret_key"}

_VERBS = {
    "batch": "批量", "create": "新建", "add": "新增", "list": "查询列表",
    "get": "查看详情", "search": "搜索", "query": "查询", "preview": "预览",
    "update": "修改", "patch": "修改", "maintain": "维护", "save": "保存",
    "delete": "删除", "remove": "移除", "upload": "上传", "import": "导入",
    "export": "导出", "download": "下载", "generate": "生成", "submit": "提交",
    "review": "审核审批", "approve": "批准审批", "confirm": "确认", "cancel": "取消",
    "revoke": "撤回", "rollback": "回退", "restore": "恢复", "transition": "状态流转",
    "pay": "付款", "receive": "收款", "writeoff": "核销", "issue": "开具",
    "void": "作废", "lock": "锁定", "unlock": "解锁", "assign": "指派",
    "claim": "领取", "share": "共享", "release": "释放", "recycle": "回收",
    "borrow": "借用", "return": "归还", "destroy": "销毁", "check": "检查",
    "process": "处理", "read": "读取", "mark": "标记", "link": "关联",
    "replace": "替换", "print": "打印", "send": "发送", "stamp": "盖章",
}

_SUBJECTS = {
    "case": "案件", "cases": "案件", "customer": "客户", "contract": "合同",
    "fee": "费用", "fees": "费用", "internal": "内部结算", "commission": "提成",
    "payment": "付款", "invoice": "开票发票", "incoming": "回款", "receivable": "应收",
    "refund": "退费", "reconciliation": "对账", "seal": "用印", "task": "任务",
    "document": "文书", "file": "文件", "attachment": "附件", "official": "官方文件",
    "outgoing": "发文", "receipt": "收文票据", "employee": "员工", "hr": "人事",
    "warehouse": "仓库", "evidence": "证物取证", "clue": "线索", "notary": "公证",
    "investigation": "调查", "ipr": "知识产权", "counsel": "法律顾问",
    "criminal": "刑事", "archive": "归档", "reminder": "提醒", "warning": "预警",
    "feedback": "反馈", "communication": "沟通", "event": "流水", "log": "日志",
    "parameter": "参数", "menu": "菜单", "permission": "权限", "role": "角色",
    "department": "部门", "report": "报表", "performance": "绩效", "template": "模板",
    "folder": "目录", "party": "当事人", "court": "法院", "record": "业务记录",
    "system": "系统", "config": "配置", "settlement": "结算", "application": "申请",
}


def exclusion_reasons(route: APIRoute) -> list[str]:
    path = route.path.lower()
    segments = set(path.strip("/").split("/"))
    reasons = []
    if "auth" in segments:
        reasons.append("认证及账户凭据生命周期，不向模型开放")
    if route.name in _CREDENTIAL_ENDPOINTS:
        reasons.append("账户凭据管理或访问令牌签发；必须由人工安全入口办理")
    if "customer-portal" in segments or "public" in segments:
        reasons.append("非 OA Bearer 身份的公开令牌入口，不得替代当前登录用户身份调用")
    if segments.intersection({"personal-agent", "agents", "mcp", "agent-mcp", "agent-tools"}) or (
        "agent" in segments and segments.intersection({"chat", "status", "state", "messages", "decision", "restore"})
    ):
        reasons.append("智能体或 MCP 自身运行入口，防止递归调用及绕过人工确认网关")
    if path == "/health" or segments.intersection({"health", "healthz", "runtime", "metrics", "cache", "caches"}):
        reasons.append("健康检查或运行时维护，不属于 OA 业务操作")
    if segments.intersection({"debug", "diagnostics", "credential", "credentials", "secrets", "tokens", "api-keys"}):
        reasons.append("调试或密钥凭据管理，不向模型开放")
    if "approval-gateway" in segments or "tool-requests" in segments or "agent-tools" in segments and "decision" in segments:
        reasons.append("人工确认网关不可由模型发现或自行批准")
    if not _has_oa_identity(route.dependant):
        reasons.append("没有原 OA current_identity 依赖，不具备原 Bearer 业务权限边界")
    return reasons


def disabled_credential_fields(schema: dict) -> list[str]:
    return [key for key in schema.get("properties", {}) if key.lower() in _CREDENTIAL_FIELDS]


def _has_oa_identity(dependant) -> bool:
    return any(
        getattr(item.call, "__name__", "") == "current_identity" or _has_oa_identity(item)
        for item in dependant.dependencies
    )


def domain_for(route: APIRoute) -> str:
    text = (route.path + " " + route.name).lower()
    tokens = set(re.split(r"[^a-z0-9]+", text))
    if tokens.intersection({"invoice", "invoices"}):
        return "开票"
    if any(word in text for word in ("incoming-payment", "incoming_payment", "receivable", "receive_payment", "arrival")):
        return "回款"
    if any(word in text for word in ("payment", "writeoff", "write_off")):
        return "付款"
    if tokens.intersection({"fee", "fees", "commission", "commissions", "settlement", "settlements", "refund", "refunds"}):
        return "费用"
    if "seal" in text or "stamp" in text:
        return "用印"
    if "warehouse" in text or "/wms/" in text:
        return "仓库"
    if any(word in text for word in ("investigation", "notary", "evidence", "clue")):
        return "调查"
    if "contract" in text:
        return "合同"
    if "customer" in text or "law_firm" in text or "law-firm" in text:
        return "客户"
    if "/hr" in text or "employee" in text or "job_role" in text or "department" in text:
        return "人事"
    if "finance" in text or "reconciliation" in text:
        return "财务"
    if any(word in text for word in ("case", "ipr", "task", "document", "attachment", "template", "communication")):
        return "案件"
    return "系统"


def is_write(route: APIRoute, method: str) -> bool:
    key = operation_key(route, method)
    if key in READ_ONLY_POSTS:
        return False
    if method not in {"GET", "HEAD", "OPTIONS"}:
        return True
    return key in SIDE_EFFECT_GETS or bool(
        set(route.endpoint.__name__.lower().split("_")).intersection(
            {"generate", "create", "acquire", "submit", "approve", "mark", "sync", "migrate", "process", "delete", "update"}
        )
    )


def title_for(route: APIRoute, method: str) -> str:
    key = operation_key(route, method)
    if method == "POST" and key[1] in {"/finance/fees", "/fees"}:
        return "新增费用草稿"
    if key[2] == "create_hr_employee":
        return "新增外部合作员工档案"
    if key[2] == "download_case_document_template":
        return "下载案件文书模板"
    if key[2] == "get_case_word_editor_content":
        return "读取并锁定案件 Word 文书"
    words = route.endpoint.__name__.lower().split("_")
    verbs = list(dict.fromkeys(_VERBS[word] for word in words if word in _VERBS))
    subjects = list(dict.fromkeys(_SUBJECTS.get(word, _SUBJECTS.get(word.rstrip("s"), "")) for word in words))
    subjects = [subject for subject in subjects if subject]
    verb = verbs[0] if verbs else "查询" if not is_write(route, method) else "办理"
    if "batch" in words and verb != "批量":
        verb = "批量" + verb
    subject = "".join(subjects) or domain_for(route)
    if "agent" in words and "document" in words:
        subject = "智能文书"
    if "skill" in words:
        subject = "自定义技能"
    return (verb + subject)[:80]


def describe(route: APIRoute, method: str, write: bool) -> tuple[str, bool]:
    key = operation_key(route, method)
    words = route.endpoint.__name__.lower().split("_")
    terms = list(dict.fromkeys(_VERBS[word] for word in words if word in _VERBS))
    subjects = list(dict.fromkeys(_SUBJECTS[word.rstrip("s")] for word in words if word.rstrip("s") in _SUBJECTS))
    text = f"{domain_for(route)}：{'、'.join(terms + subjects)}。原接口 {method} {route.path}（{route.name}）。"
    original = "\n".join(filter(None, (route.summary, route.description)))
    # 既有编码损坏不复制给模型；保留明确英文接口名和路径供审计追溯。
    corrupted = bool(re.search(r"[\ufffd\ue000-\uf8ff]|(?:锟斤拷|烫烫|屯屯)|(?:[ÃÂ][\x80-\xff])", original))
    if original and not corrupted:
        text += original.strip() + "。"
    if method == "POST" and key[1] in {"/finance/fees", "/fees"}:
        model = route.body_field.field_info.annotation
        fields = getattr(model, "model_fields", {})
        model_name = getattr(model, "__name__", str(model))
        required = [name for name, item in fields.items() if item.is_required()]
        optional = [name for name, item in fields.items() if not item.is_required()]
        text += (
            "新增案件财务费用草稿，不是付款、回款或开票。"
            f"body 使用实际挂载的原模型 {model_name}：必填 {'、'.join(required)}；可选 {'、'.join(optional)}。"
            "费用类别应从实际费用主数据查询，例如代理费、官费、内部费用；不能臆造编号、金额规则或合同总额门槛。"
            "先查案件和费用类别；保存草稿后仍需原业务提交、审批、付款或开票步骤。"
        )
        if "expense_scope" in fields:
            text += "expense_scope 的原枚举范围示例为律所、平台、内部；expense_subtype 按原类别主数据选择。"
    if route.endpoint.__name__ == "create_hr_employee":
        text += (
            "本工具仅创建外部合作账号类型的无登录员工业务档案：account_type 必须为外部合作账号，username 必须为空。"
            "不接收或生成密码；创建员工登录账号或客户登录账号仍须使用原人工安全入口，不能通过本工具完成。"
        )
    if key in READ_ONLY_POSTS:
        text += f"已核对只读 POST：{READ_ONLY_POSTS[key]}。"
    if key in SIDE_EFFECT_GETS:
        text += f"注意 GET 有写副作用：{SIDE_EFFECT_GETS[key]}。"
    text += "须持久化人工确认后调用，继续执行原权限、数据范围、校验和业务审批。" if write else "继续执行原权限和当前用户数据范围。"
    return text, corrupted

"""从已校验或持久保存的接口参数生成确认摘要，不查询或执行业务。"""

from contextvars import ContextVar

from app.config import settings

# 本次摘要用的中文显示名（预览里保存的 field_labels / value_labels，501137）。
_DISPLAY: ContextVar[tuple[dict, dict]] = ContextVar("action_summary_display", default=({}, {}))


_FIELD_LABELS = {
    "task_id": "任务ID", "task_ids": "任务ID", "case_id": "案件ID", "case_ids": "案件ID",
    "case_record_id": "案件记录ID", "case_no": "案号", "case_nos": "案号",
    "contract_id": "合同ID", "contract_ids": "合同ID", "contractIds": "合同ID",
    "contract_record_id": "合同记录ID", "contract_no": "合同号", "contract_object_id": "合同标的ID",
    "fee_id": "费用ID", "fee_ids": "费用ID", "case_fee_id": "案件费用ID",
    "case_fee_ids": "案件费用ID", "source_fee_id": "来源费用ID",
    "record_id": "记录ID", "record_ids": "记录ID", "customer_id": "客户ID",
    "attachment_id": "附件ID", "attachment_ids": "附件ID", "source_attachment_ids": "来源附件ID",
    "file_id": "文件ID", "file_ids": "文件ID", "fileIds": "文件ID",
    "title": "名称", "serial_no": "编号", "customer": "客户", "owner": "负责人账号",
    "recipient": "接收人账号", "recipients": "接收人账号", "handler": "经办人",
    "department": "所属部门", "deadline": "截止日期", "start_at": "开始时间", "end_at": "结束时间",
    "priority": "优先级", "is_vip": "VIP", "collaborators": "协作人", "participants": "参与人",
    "amount": "金额", "actual_amount": "实际金额", "base_amount": "基准金额",
    "payment_amount": "付款金额", "received_amount": "到账金额", "receivable_amount": "应收金额",
    "fee_type": "费用类型", "fee_type_id": "费用类型ID", "expense_scope": "费用归属",
    "expense_subtype": "费用子类", "payee": "收款人", "payer": "付款人",
    "payer_name": "付款方名称", "payee_username": "收款人账号", "payment_type_id": "付款类型ID",
    "payment_method": "付款方式", "payment_account": "付款账号", "payment_payee": "付款收款人",
    "paid_date": "付款日期", "received_date": "到账日期", "writeoff_date": "核销日期",
    "inform_date": "通知日期", "invoice_no": "发票号", "voucher_no": "凭证号",
    "description": "说明", "remark": "备注", "comment": "处理意见", "reason": "原因",
    "status": "状态", "to_status": "目标状态", "action": "动作", "action_key": "操作权限键",
    "approved": "审批结论", "approver": "审批人", "approvers": "审批人",
    "submit": "提交", "submit_payment": "同时提交请款", "sync_seal": "同步用印",
    "change_type": "变更类型", "contract_body": "合同主体", "contract_type": "合同类别",
    "signed_at": "签订日期", "end_date": "到期日期", "external_contract_no": "外部合同号",
    "external_contract_numbers": "外部合同号", "commission_mode": "提成模式",
    "commission_details": "提成明细", "employee_username": "员工账号", "commission_type": "提成类别",
    "items": "明细", "lines": "明细", "changes": "修改字段", "data": "业务字段",
    "actions": "操作明细", "case_contracts": "案件合同关联", "module": "业务模块",
    # 501137：业务工具和常用接口里其余参数的中文名，不再显示内部代码名。
    "file_date": "建档日期", "investigation_id": "调查任务ID", "start_date": "开始日期", "page": "页码", "page_size": "每页条数",
    "clue_id": "线索ID", "clue_ids": "线索ID", "warehouse_id": "仓库ID", "storage_location_id": "存放位置ID",
    "finance_scope": "财务中心", "business_type": "业务类型", "archive_type": "归档类型", "payment_id": "到账ID",
    "receipt_id": "到账ID", "receipt_ids": "到账ID", "invoice_id": "发票ID", "invoice_ids": "发票ID",
    "user_id": "用户ID", "username": "账号", "display_name": "姓名", "name": "名称", "content": "内容",
    "note": "备注", "notes": "备注", "phone": "电话", "email": "邮箱", "address": "地址", "court": "法院",
    "court_case_no": "法院案号", "judge": "法官", "clerk": "书记员", "hearing_date": "开庭日期", "hearing_time": "开庭时间",
    "filing_date": "立案日期", "level": "审级", "case_stage": "案件阶段", "case_type": "案件类型", "cause_or_charge": "案由",
    "client_position": "客户诉讼地位", "handling_lawyers": "经办律师", "assistant": "律师助理", "investigator": "调查员",
    "source_person": "案源人", "plaintiffs": "原告", "defendants": "被告", "third_parties": "第三人",
    "organization_type": "主体类型", "identity_no": "证件号码", "contacts": "联系人", "category": "类别",
    "invoice_type": "发票类型", "invoice_title": "发票抬头", "taxpayer_id": "纳税人识别号", "tax_rate": "税率",
    "application_date": "申请日期", "reminder_date": "提醒日期", "date": "日期", "type": "类型", "keyword": "关键字",
    "confirm": "确认执行", "scope": "范围", "decision": "决定",
    # 501634（tgn 11-05）：案件基本信息常用字段的中文名，确认窗口不出现“其他信息”。
    "customer_record_id": "客户", "case_phase": "案件阶段", "assistants": "律师助理", "business_owner": "业务负责人",
    "extra_investigators": "其他调查员", "investigation_clue_ids": "关联线索", "right_type": "权利类型",
}

_TASK_ACTIONS = {
    "accept": "接收并开始处理", "complete": "提交完成", "confirm": "验收",
    "handoff": "交接", "withdraw": "撤回", "reject": "退回", "restart": "重新开始",
    "resend": "重新发送", "start": "开始处理", "assign": "指派",
}


_KEY_FIELDS = (
    "action", "approved", "to_status", "recipient", "fee_type", "amount", "payment_amount",
    "submit", "submit_payment", "sync_seal", "owner", "title", "module", "status",
    "fee_type_id", "expense_scope", "expense_subtype", "deadline", "end_at", "priority", "is_vip",
    "handler", "approvers", "change_type", "actions", "items", "lines", "remark", "comment",
)


def _text(value, limit: int = 48) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[:limit] + "…（完整内容见详情）"


def _value_text(value) -> str:
    if value is None:
        return "空值"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, dict):
        # 主摘要不递归展开业务对象；完整结构始终保留在 preview.params。
        return f"{len(value)}个字段（见详情）" if value else "空对象"
    if isinstance(value, list):
        if not value:
            return "空列表"
        if any(isinstance(item, (dict, list)) for item in value):
            return f"共{len(value)}项明细（见详情）"
        shown = "、".join(_text(item, 32) for item in value[:3])
        return shown + (f"等，共{len(value)}项" if len(value) > 3 else "")
    if isinstance(value, str):
        return _text(value) if value else "空字符串"
    return str(value)


def _field_text(key: str, value) -> str:
    from app.agent_mcp.display_labels import field_label, value_label
    prefix, separator, name = key.rpartition(".")
    name = name if separator else key
    labels, values = _DISPLAY.get()
    label = (prefix + "." if separator else "") + field_label(name, labels)
    value = value_label(name, value, values)
    if isinstance(value, list):
        value = [value_label(name, item, values) for item in value]
    if name == "approved" and isinstance(value, bool):
        text = "通过" if value else "拒绝"
    elif isinstance(value, str) and (name in {"recipient", "owner", "handler", "amount"} or name.endswith("_amount")):
        text = value if value else "空字符串"
    else:
        text = _value_text(value)
    return f"{label}：{text}"


def _task_summary(path: str, method: str, params: dict, body: dict) -> str | None:
    if method != "POST":
        return None
    if path == "/tasks":
        fields = [key for key in ("owner", "deadline", "end_at", "priority") if key in body]
        details = "，".join(_field_text(key, body[key]) for key in fields)
        return f"新建任务“{_text(body['title'])}”" + (f"，{details}" if details else "")
    if path in {"/tasks/batch-lifecycle", "/tasks/batch-update", "/tasks/messages/batch-read"}:
        ids = list(dict.fromkeys(body["task_ids"]))
        target = f"{len(ids)}项任务（ID：{_value_text(ids)}）"
    elif path.startswith("/tasks/{task_id}/"):
        target = f"任务（ID：{params['path']['task_id']}）"
    else:
        return None
    if path == "/tasks/batch-update":
        fields = [key for key in ("owner", "deadline", "priority", "is_vip") if body.get(key) is not None]
        changes = "、".join(_field_text(key, body[key]).replace("：", "设为", 1) for key in fields)
        if not fields:
            return f"修改{target}（请求未指定修改字段）"
        return f"修改{target}：{changes}"
    if path == "/tasks/messages/batch-read":
        return f"将{target}的消息标记为已读"
    action = body.get("action") if path == "/tasks/batch-lifecycle" else path.rsplit("/", 1)[-1]
    if action not in _TASK_ACTIONS:
        return None
    if action == "handoff":
        # 接收人属于决定含义，不因长ID列表或备注而被标题截断隐藏。
        if "recipient" not in body:
            return f"交接{target}（请求未提供接收人）"
        if not body["recipient"].strip():
            return f"交接{target}（请求接收人为空）"
        summary = f"将{target}交接给账号{body['recipient']}"
        if body.get("end_at") is not None:
            summary += f"，结束时间：{body['end_at']}"
        return summary
    summary = f"{_TASK_ACTIONS[action]}{target}"
    if action in {"withdraw", "reject"} and body.get("comment"):
        summary += f"，原因：{_text(body['comment'])}"
    return summary


def _is_id_field(name: str) -> bool:
    return name == "id" or name.endswith(("_id", "_ids", "Ids"))


def _shown_to_user(key: str, value) -> bool:
    """501634（tgn 11-05）：摘要里不出现内部编号和“其他信息”：编号能换成案号、名称的才显示，换不了的不显示；
    没有中文名的参数不显示。执行仍用原参数，完整参数在确认窗口里看。"""
    from app.agent_mcp.display_labels import OTHER_FIELD, field_label, value_label
    name = key.rpartition(".")[2] or key
    labels, values = _DISPLAY.get()
    if field_label(name, labels) == OTHER_FIELD:
        return False
    if _is_id_field(name):
        items = value if isinstance(value, list) else [value]
        return bool(items) and all(value_label(name, item, values) is not item for item in items)
    return True


def _key_details(fields: dict, limit: int = 4) -> str:
    def priority(key):
        name = key.rsplit(".", 1)[-1]
        return _KEY_FIELDS.index(name) if name in _KEY_FIELDS else len(_KEY_FIELDS)

    ordered = sorted((key for key in fields if _shown_to_user(key, fields[key])), key=priority)
    shown = [_field_text(key, fields[key]) for key in ordered[:limit]]
    if len(ordered) > limit:
        shown.append(f"另{len(ordered) - limit}项参数见详情")
    return "，".join(shown)


def _action_list(actions: list) -> str:
    parts = []
    for index, action in enumerate(actions[:3], 1):
        details = _key_details(action, limit=3) if isinstance(action, dict) else _value_text(action)
        parts.append(f"第{index}项：{details}")
    if len(actions) > 3:
        parts.append(f"其余{len(actions) - 3}项操作见详情")
    return f"共{len(actions)}项操作（{'；'.join(parts)}）"


def summary_from_preview(preview: dict) -> str:
    """新旧确认记录共用，只读取原预览；不依赖当前目录或修改历史记录。"""
    token = _DISPLAY.set((preview.get("field_labels") or {}, preview.get("value_labels") or {}))
    try:
        return _summary_from_preview(preview)
    finally:
        _DISPLAY.reset(token)


def _summary_from_preview(preview: dict) -> str:
    path = preview["path_template"].removeprefix(settings.api_prefix)
    method = preview["method"]
    params = preview["params"]
    body = params.get("body")
    body_fields = body if isinstance(body, dict) else {}
    task_summary = _task_summary(path, method, params, body_fields)
    if task_summary is not None:
        return task_summary
    operation = preview["operation_name"]
    if isinstance(body_fields.get("approved"), bool):
        batch_prefix = "批量" if operation.startswith("批量") else ""
        subject = operation.removeprefix(batch_prefix)
        for prefix in ("批准审批", "审核审批"):
            if subject.startswith(prefix):
                operation = batch_prefix + ("批准" if body_fields["approved"] else "拒绝") + subject.removeprefix(prefix)
                break
    targets = [_field_text(key, value) for key, value in params["path"].items() if _shown_to_user(key, value)]
    details = {}
    for source in (body_fields, params["query"]):
        for key, value in source.items():
            if key.endswith(("_id", "_ids", "_no", "_nos", "Ids")) and key not in {"fee_type_id", "payment_type_id"}:
                if _shown_to_user(key, value):
                    targets.append(_field_text(key, value))
            elif key in {"data", "changes"} and isinstance(value, dict):
                details.update({_FIELD_LABELS.get(key, "业务字段") + "." + name: item for name, item in value.items()})
            else:
                details[key] = value
    if body is not None and not isinstance(body, dict):
        details["请求内容"] = body
    actions = details.pop("actions", None)
    if isinstance(actions, list):
        action_text = _action_list(actions)
    elif actions is not None:
        details["actions"] = actions
        action_text = ""
    else:
        action_text = ""
    if params.get("files"):
        details["使用已上传附件"] = params["files"]
    target_text = "；".join(targets[:3])
    if len(targets) > 3:
        target_text += f"；另{len(targets) - 3}项目标见详情"
    parts = [part for part in (action_text, _key_details(details)) if part]
    return operation + (f"（{target_text}）" if targets else "") + ("：" + "；".join(parts) if parts else "")

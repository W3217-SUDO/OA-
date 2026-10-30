"""按《法律服务机构管理系统》操作手册的业务动作组合原接口的 MCP 业务工具。

一个业务动作一个工具（例如“新建合同并提交审批”），内部每一步都经 call_tool 调用目录里的原接口：
原接口的角色权限、数据范围、校验、审批流，个人令牌的只读/业务范围限制和操作日志全部照旧，不另开通道。
写工具两段式：不带 confirm=true 时只跑查询并返回执行计划，不写任何数据；用户同意后带 confirm=true 才执行。
审批、盖章、付款核销、开票作废、退费到账等不可撤回步骤仍由原通道生成待确认请求，须本人在 OA 网页确认。
设计与对照见 docs/业务工具/。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Awaitable, Callable

from fastapi import HTTPException
from jsonschema import Draft202012Validator

from app.agent_mcp.auth import authenticated_identity, get_auth_context
from app.agent_mcp.catalog import get_catalog


PLANNED = "（执行时生成）"
_CONFIRM = {"type": "boolean", "default": False,
            "description": "false/不传=只返回执行计划，不写数据；用户看过计划并明确同意后再传 true 执行"}


class StepFailed(Exception):
    def __init__(self, step: dict):
        super().__init__(step.get("error"))
        self.step = step


class Run:
    """一次业务工具调用：记录每一步调用了哪个原接口、参数和结果；计划模式下写步骤只记录不执行。"""

    def __init__(self, tool: "BusinessTool", confirm: bool, call):
        self.tool, self.confirm, self._call = tool, confirm, call
        self.steps: list[dict] = []
        self.notes: list[str] = []

    async def read(self, name: str, arguments: dict, purpose: str):
        step = {"step": len(self.steps) + 1, "purpose": purpose, "tool": name, "kind": "读", "arguments": arguments}
        self.steps.append(step)
        if get_catalog(get_auth_context().application).get(name).is_write:
            raise RuntimeError(f"业务工具把写接口当成读步骤：{name}")
        result = await self._invoke(step, name, arguments)
        step["status"] = "完成"
        return result

    async def _invoke(self, step: dict, name: str, arguments: dict):
        try:
            result = await self._call(name, arguments)
        except HTTPException as exc:
            step.update(status="失败", error=exc.detail)
            raise StepFailed(step) from exc
        # 部分沿用旧系统的接口用 HTTP 200 + {"IsSuccess": false, "Message": ...} 表示业务拒绝，不能当成功。
        if isinstance(result, dict) and result.get("IsSuccess") is False:
            step.update(status="失败", error=result.get("Message") or "原接口返回失败")
            raise StepFailed(step)
        return result

    async def write(self, name: str, arguments: dict, purpose: str):
        step = {"step": len(self.steps) + 1, "purpose": purpose, "tool": name, "kind": "写", "arguments": arguments}
        self.steps.append(step)
        spec = get_catalog(get_auth_context().application).get(name)
        if not spec.is_write:
            raise RuntimeError(f"业务工具把读接口当成写步骤：{name}")
        if not self.confirm:
            step["status"] = "待执行"
            _precheck(spec, step)
            if PLANNED not in json.dumps(arguments, ensure_ascii=False, default=str):
                try:
                    spec.validate_arguments(arguments)
                except HTTPException as exc:
                    step["problem"] = exc.detail
            return {"id": PLANNED, "serial_no": PLANNED, "planned": True}
        result = await self._invoke(step, name, arguments)
        if isinstance(result, dict) and result.get("status") == "pending":
            step.update(status="待网页确认", request_id=result.get("request_id"), confirmation_url=result.get("confirmation_url"))
        else:
            step["status"] = "完成"
            created = _created_ref(result)
            if created:
                step["result"] = created
        return result


def _precheck(spec, step: dict) -> None:
    """计划阶段就按个人令牌规则提示哪一步会被拒；账号角色权限由原接口执行时判断。"""
    context = get_auth_context()
    if not context.readonly:
        return
    from app.agent_mcp.personal_tokens import token_tool_allowed
    if not token_tool_allowed(spec) or (context.groups and spec.group_id not in context.groups) or not context.write_allowed:
        step["problem"] = "这一步在当前连接下不允许写入（只读授权或不在所选业务范围）"


def _created_ref(result) -> dict | None:
    if isinstance(result, dict):
        keys = ("id", "serial_no", "title", "status")
        found = {key: result[key] for key in keys if key in result and not isinstance(result[key], (dict, list))}
        return found or None
    return None


@dataclass(frozen=True)
class BusinessTool:
    name: str
    title: str
    description: str
    properties: dict
    required: tuple[str, ...]
    write: bool
    uses: tuple[str, ...]  # 内部会调用的目录工具名：用于令牌业务范围过滤和启动自检
    handler: Callable[[Run, dict], Awaitable[dict]]

    @property
    def input_schema(self) -> dict:
        properties = {**self.properties, **({"confirm": _CONFIRM} if self.write else {})}
        return {"type": "object", "properties": properties, "required": list(self.required), "additionalProperties": False}

    def to_mcp(self) -> dict:
        kind = "【业务·写入】" if self.write else "【业务·查询】"
        return {"name": self.name, "title": kind + self.title, "description": self.description, "inputSchema": self.input_schema,
                "annotations": {"readOnlyHint": not self.write, "destructiveHint": self.write, "openWorldHint": False}}

    def to_model_function(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": f"{self.title}：{self.description}",
                                                 "parameters": self.input_schema}}


TOOLS: dict[str, BusinessTool] = {}


def business_tool(name, title, description, properties, required=(), *, write, uses):
    def register(handler):
        TOOLS[name] = BusinessTool(name, title, description, properties, tuple(required), write, tuple(uses), handler)
        return handler
    return register


def is_business_tool(name: object) -> bool:
    return isinstance(name, str) and name in TOOLS


def visible_tools(catalog=None, context=None) -> list[BusinessTool]:
    """个人令牌只看到全部内部接口都在所选业务范围、且（写工具）账号有写入授权的业务工具。"""
    context = context or get_auth_context()
    from app.agent_mcp.personal_tokens import token_tool_allowed
    catalog = catalog or get_catalog(context.application)
    result = []
    for tool in TOOLS.values():
        try:
            specs = [catalog.get(name) for name in tool.uses]
        except (HTTPException, KeyError):  # 内部接口不在当前目录（例如被下线）时整个业务工具不开放
            continue
        if not context.readonly:
            result.append(tool)
        elif (not tool.write or context.write_allowed) and all(token_tool_allowed(spec) for spec in specs) and (
                not context.groups or all(spec.group_id in context.groups for spec in specs)):
            result.append(tool)
    return result


async def run_business_tool(name: str, arguments: object, *, call=None, context=None) -> dict:
    """call 默认是 service.call_tool；站内智能体传入带会话上下文的调用。"""
    if call is None:
        from app.agent_mcp.service import call_tool as call
    tool = TOOLS.get(name)
    if tool is None or tool not in visible_tools(context=context):
        raise HTTPException(403, "该业务工具不存在，或不在当前连接的业务范围/读写授权内")
    if not isinstance(arguments, dict):
        raise HTTPException(422, "业务工具参数必须是 JSON 对象")
    errors = sorted(Draft202012Validator(tool.input_schema).iter_errors(arguments), key=lambda item: list(item.path))
    if errors:
        raise HTTPException(422, detail=[{"loc": ["arguments", *map(str, error.path)], "msg": error.message} for error in errors[:20]])
    confirm = bool(arguments.get("confirm")) if tool.write else True
    values = {key: value for key, value in arguments.items() if key != "confirm"}
    run = Run(tool, confirm, call)
    try:
        data = await tool.handler(run, values)
    except StepFailed as exc:
        done = [step for step in run.steps if step.get("status") in ("完成", "待网页确认")]
        return {"isError": True, "tool": name, "mode": "执行" if confirm else "计划",
                "message": f"第 {exc.step['step']} 步“{exc.step['purpose']}”失败，已停止，后续步骤未执行"
                           + ("；前面已完成的写入保留（有留痕，可由管理员还原），不要直接重复提交" if confirm and any(s["kind"] == "写" for s in done) else ""),
                "failed_step": exc.step, "completed_steps": done, "steps": run.steps}
    pending = [step for step in run.steps if step.get("status") == "待网页确认"]
    problems = [step for step in run.steps if step.get("problem")]
    result = {"tool": name, "mode": "执行" if confirm else "计划", "steps": run.steps, **(data or {})}
    if run.notes:
        result["notes"] = run.notes
    if tool.write and not confirm:
        result["next_step"] = ("计划里有问题，先补齐或修正再生成计划：" + "；".join(f"第{s['step']}步 {s['problem']}" for s in problems)
                               if problems else "以上是执行计划，尚未写入任何数据。请把计划给用户看，用户明确同意后用相同参数加 confirm=true 再调用一次。")
    elif pending:
        result["next_step"] = "其中有不可撤回的步骤已生成待确认请求，须用户在 OA 网页“智能体中心”确认后才会执行。"
    return result


# ---------- 通用查找 ----------

def _items(result) -> list[dict]:
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        for key in ("items", "records", "rows", "data", "results"):
            if isinstance(result.get(key), list):
                return [item for item in result[key] if isinstance(item, dict)]
    return []


def _brief(item: dict, *keys: str) -> dict:
    keys = keys or ("id", "serial_no", "title", "customer", "status", "owner")
    return {key: item.get(key) for key in keys if key in item}


def _one(matches: list[dict], label: str, value) -> dict:
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise HTTPException(404, f"没有找到{label}“{value}”，或当前账号无权查看")
    raise HTTPException(409, detail={"msg": f"{label}“{value}”匹配到多条，请用编号或 ID 指定", "candidates": [_brief(item) for item in matches[:10]]})


async def find_customer(run: Run, args: dict) -> dict:
    if args.get("customer_id"):
        result = await run.read("oa_get_record_get", {"path": {"record_id": args["customer_id"]}}, "读取客户档案")
        return result
    name = str(args.get("customer_name") or "").strip()
    if not name:
        raise HTTPException(422, "请提供 customer_name（客户名称）或 customer_id")
    rows = await _customers_named(run, name, 50)
    exact = [row for row in rows if str(row.get("title") or "").strip() == name]
    return _one(exact or rows, "客户", name)


async def _customers_named(run: Run, name: str, page_size: int) -> list[dict]:
    """客户列表默认只查“我的客户”；查不到再按全所范围查（没有全所查看权限时原接口会拒绝，按没找到处理）。"""
    rows = _items(await run.read("oa_list_customers_get", {"query": {"customer_name": name, "page_size": page_size}}, "按名称查客户（我的客户）"))
    if any(str(row.get("title") or "").strip() == name for row in rows):
        return rows
    try:
        company = await run.read("oa_list_customers_get", {"query": {"customer_name": name, "scope": "company", "page_size": page_size}},
                                 "按名称查客户（全所客户）")
    except StepFailed as exc:
        exc.step.update(status="跳过", note="当前账号不能按全所范围查客户")
        return rows
    return _items(company) or rows


async def find_record(run: Run, module: str, serial_no: str | None, record_id: int | None, label: str) -> dict:
    if record_id:
        return await run.read("oa_get_record_get", {"path": {"record_id": record_id}}, f"读取{label}")
    serial_no = str(serial_no or "").strip()
    if not serial_no:
        raise HTTPException(422, f"请提供{label}编号或 ID")
    # serial_no 筛选只在合同列表生效，keyword 对所有模块都按编号/名称模糊匹配；只认编号完全一致的那条，不拿近似结果顶替。
    result = await run.read("oa_list_records_get", {"query": {"module": module, "serial_no": serial_no, "keyword": serial_no, "page_size": 20}},
                            f"按编号查{label}")
    return _one([row for row in _items(result) if str(row.get("serial_no") or "").strip() == serial_no], label, serial_no)


async def find_case(run: Run, args: dict) -> dict:
    if args.get("case_id"):
        return await run.read("oa_get_record_get", {"path": {"record_id": args["case_id"]}}, "读取案件")
    case_no = str(args.get("case_no") or "").strip()
    if not case_no:
        raise HTTPException(422, "请提供 case_no（我方案号）或 case_id")
    result = await run.read("oa_search_ordinary_cases_post", {"body": {"serial_no": case_no, "page": 1, "page_size": 20}}, "按案号查案件")
    rows = _items(result)
    return _one([row for row in rows if str(row.get("serial_no") or "").strip() == case_no] or rows, "案件", case_no)


def _drop_empty(values: dict) -> dict:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


def _ids(value) -> int:
    return value if isinstance(value, int) else 0


S = {"type": "string"}
INT = {"type": "integer", "minimum": 1}
DATE = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "YYYY-MM-DD"}
MONEY = {"type": "number", "exclusiveMinimum": 0}
NAMES = {"type": "array", "items": {"type": "string", "minLength": 1}, "maxItems": 20}
ATTACHMENTS = {"type": "array", "items": INT, "maxItems": 20,
               "description": "已上传附件的 ID（先通过 /api/v1/agent-tools/upload 上传本地文件拿到 attachment_id）"}


def _desc(schema: dict, text: str) -> dict:
    return {**schema, "description": text}


CUSTOMER_REF = {"customer_name": _desc(S, "客户名称（我的客户里的名称）"), "customer_id": _desc(INT, "客户 ID，已知时优先")}
CONTRACT_REF = {"contract_no": _desc(S, "合同编号，如 SHHT2610059"), "contract_id": _desc(INT, "合同 ID，已知时优先")}
CASE_REF = {"case_no": _desc(S, "我方案号，如 SHMS2500615"), "case_id": _desc(INT, "案件 ID，已知时优先")}
FINANCE_SCOPE = {"type": "string", "enum": ["firm", "platform"], "default": "firm", "description": "firm=财务中心（律所）；platform=平台财务中心"}


# ---------- 01 客户管理 ----------

@business_tool("biz_customer_overview", "客户总览（我的客户/客户查看）",
               "按客户名称查客户档案，并带出联系人、事项记录、客户文档和名下合同。",
               CUSTOMER_REF, write=False,
               uses=("oa_list_customers_get", "oa_get_record_get", "oa_list_customer_contacts_get",
                     "oa_list_customer_events_by_guid_get", "oa_list_customer_files_by_guid_get", "oa_list_records_get"))
async def _customer_overview(run: Run, args: dict) -> dict:
    customer = await find_customer(run, args)
    customer_id = customer["id"]
    contacts = await run.read("oa_list_customer_contacts_get", {"path": {"customer_id": customer_id}}, "联系人")
    guid = (customer.get("data") or {}).get("customer_guid")
    events = files = None
    if guid:
        events = await run.read("oa_list_customer_events_by_guid_get", {"path": {"customer_guid": guid}}, "事项记录")
        files = await run.read("oa_list_customer_files_by_guid_get", {"path": {"customer_guid": guid}}, "客户文档")
    contracts = await run.read("oa_list_records_get", {"query": {"module": "contract", "customer_id": customer_id, "page_size": 100}}, "名下合同")
    return {"customer": customer, "contacts": _items(contacts), "notes": _items(events), "files": _items(files),
            "contracts": [_brief(row) for row in _items(contracts)]}


@business_tool("biz_customer_conflict_check", "客户利益检索",
               "新客户、新案件前按名称检索利益冲突，并列出同名或近似的已有客户。",
               {"name": _desc(S, "客户或当事人名称")}, ("name",), write=False,
               uses=("oa_customer_conflicts_get", "oa_list_customers_get"))
async def _customer_conflict(run: Run, args: dict) -> dict:
    conflicts = await run.read("oa_customer_conflicts_get", {"query": {"name": args["name"]}}, "利益冲突检索")
    similar = await _customers_named(run, args["name"], 20)
    return {"conflicts": conflicts, "similar_customers": [_brief(row, "id", "serial_no", "title", "owner") for row in similar]}


CONTACT = {"type": "object", "additionalProperties": False, "required": ["name"], "properties": {
    "name": _desc(S, "姓名"), "position": _desc(S, "职务"), "project_role": _desc(S, "项目角色"),
    "office_phone": _desc(S, "办公电话"), "phone": _desc(S, "移动电话"), "im_account": _desc(S, "IM"), "email": _desc(S, "邮箱"),
    "is_primary": {"type": "boolean", "description": "主联系人"}, "remark": _desc(S, "备注")}}
CUSTOMER_PROFILE = {
    "customer_type": _desc(S, "客户类型"), "organization_type": {"type": "string", "enum": ["公司企业", "个人", "个体工商户", "事业单位", "机关团体", "其他"], "description": "组织类型"},
    "credit_code": _desc(S, "统一社会信用代码（企业必填）"), "identity_no": _desc(S, "身份证号（个人必填）"),
    "registered_address": _desc(S, "注册地址"), "postal_code": _desc(S, "邮编"), "short_name": _desc(S, "客户简称"),
    "phone": _desc(S, "电话"), "fax": _desc(S, "传真"),
    "legal_representative": _desc(S, "法人姓名"), "legal_agent_id_no": _desc(S, "法人身份证号"), "legal_agent_title": _desc(S, "法人职务"),
    "invoice_title": _desc(S, "发票抬头"), "taxpayer_id": _desc(S, "纳税人识别号/税号"), "invoice_address": _desc(S, "开票地址"),
    "invoice_phone": _desc(S, "开票电话"), "bank_name": _desc(S, "开户行"), "bank_account": _desc(S, "帐号"),
    "level": _desc(S, "客户等级"), "customer_source": _desc(S, "客户来源"), "file_date": DATE,
    "is_shared": {"type": "boolean", "description": "是否共享"}, "is_assisted": {"type": "boolean", "description": "上海市资助信息"},
}


@business_tool("biz_customer_create", "新建客户（含联系人）",
               "先做利益检索和重名检查，再新建客户档案（基本/法人/开票/控制信息），并逐个新增联系人。开票信息请尽量填全，否则开票申请无法自动带出。",
               {"title": _desc(S, "客户名称"), **CUSTOMER_PROFILE,
                "customer_managers": _desc(NAMES, "客户管理人（账号或姓名）"), "description": _desc(S, "备注"),
                "contacts": {"type": "array", "items": CONTACT, "maxItems": 20, "description": "联系人"}},
               ("title", "customer_managers"), write=True,
               uses=("oa_customer_conflicts_get", "oa_list_customers_get", "oa_create_customer_post", "oa_add_customer_contact_post"))
async def _customer_create(run: Run, args: dict) -> dict:
    title = args["title"].strip()
    conflicts = await run.read("oa_customer_conflicts_get", {"query": {"name": title}}, "利益冲突检索")
    same = [row for row in _items(await run.read("oa_list_customers_get", {"query": {"customer_name": title, "page_size": 20}}, "重名检查"))
            if str(row.get("title") or "").strip() == title]
    if same:
        raise HTTPException(409, detail={"msg": f"已存在同名客户“{title}”，不再新建；如需补信息请用 biz_customer_maintain",
                                         "existing": [_brief(row) for row in same]})
    body = _drop_empty({key: args.get(key) for key in (*CUSTOMER_PROFILE, "customer_managers", "description")})
    created = await run.write("oa_create_customer_post", {"body": {"title": title, **body}}, "新建客户档案")
    for contact in args.get("contacts") or []:
        await run.write("oa_add_customer_contact_post", {"path": {"customer_id": created.get("id")}, "body": contact}, f"新增联系人 {contact['name']}")
    return {"conflict_check": conflicts, "customer": _created_ref(created)}


@business_tool("biz_customer_maintain", "客户编辑（补信息/事项记录/联系人/管理人）",
               "客户编辑：补全开票、法人、银行等信息；新增事项记录；新增联系人；调整客户管理人。只做传入的部分。",
               {**CUSTOMER_REF, "profile": {"type": "object", "additionalProperties": False, "properties": CUSTOMER_PROFILE,
                                            "description": "要补全或修改的档案字段（只传要改的）"},
                "note": {"type": "object", "additionalProperties": False, "required": ["content"],
                         "properties": {"content": _desc(S, "事项内容"), "note_type": _desc(S, "记录类型")}, "description": "新增事项记录"},
                "contacts": {"type": "array", "items": CONTACT, "maxItems": 20, "description": "新增联系人"},
                "managers": _desc(NAMES, "调整后的全部客户管理人"), "manager_comment": _desc(S, "管理人调整说明")},
               write=True,
               uses=("oa_list_customers_get", "oa_get_record_get", "oa_patch_customer_patch", "oa_add_customer_note_post",
                     "oa_add_customer_contact_post", "oa_update_customer_managers_put"))
async def _customer_maintain(run: Run, args: dict) -> dict:
    customer = await find_customer(run, args)
    customer_id = customer["id"]
    if not any(args.get(key) for key in ("profile", "note", "contacts", "managers")):
        raise HTTPException(422, "请至少提供 profile、note、contacts、managers 中的一项")
    if args.get("profile"):
        data = {**(customer.get("data") or {}), **args["profile"]}
        await run.write("oa_patch_customer_patch", {"path": {"customer_id": customer_id}, "body": {"data": data}}, "补全客户档案")
    if args.get("note"):
        await run.write("oa_add_customer_note_post", {"path": {"customer_id": customer_id}, "body": _drop_empty(args["note"])}, "新增事项记录")
    for contact in args.get("contacts") or []:
        await run.write("oa_add_customer_contact_post", {"path": {"customer_id": customer_id}, "body": contact}, f"新增联系人 {contact['name']}")
    if args.get("managers"):
        await run.write("oa_update_customer_managers_put", {"path": {"customer_id": customer_id},
                                                            "body": _drop_empty({"managers": args["managers"], "comment": args.get("manager_comment")})}, "调整客户管理人")
    return {"customer": _brief(customer)}


# ---------- 02 合同中心 ----------

CONTRACT_FIELDS = {
    "contract_body": {"type": "string", "enum": ["律所", "平台"], "description": "合同主体"},
    "contract_type": _desc(S, "合同类别，如 法律顾问合同"), "fee_type": _desc(S, "收费模式，如 固定收费、风险代理"),
    "external_contract_numbers": _desc(NAMES, "外部合同号（可多个；仅客户管理人可改）"),
    "amount": {"type": "number", "minimum": 0, "description": "合同金额"}, "signed_at": _desc(DATE, "签订日期 YYYY-MM-DD"),
}


@business_tool("biz_contract_create_and_submit", "新建合同并提交审批",
               "新建合同：①按客户名称找到客户建合同草稿 ②挂合同附件 ③选审批人提交审批（可同步申请用印）。不传 approvers 时只建草稿并返回可选审批人。",
               {"customer_name": _desc(S, "客户名称"), "customer_id": _desc(INT, "客户 ID"), "title": _desc(S, "合同名称"),
                **CONTRACT_FIELDS, "description": _desc(S, "备注（页面必填）"), "attachment_ids": _desc(ATTACHMENTS, "合同附件 ID"),
                "approvers": _desc(NAMES, "合同审批人账号，最多 10 个"), "submit_comment": _desc(S, "提交说明"),
                "sync_seal": {"type": "boolean", "default": False, "description": "是否同步申请用印"}},
               ("title", "contract_type", "fee_type", "description"), write=True,
               uses=("oa_list_customers_get", "oa_get_record_get", "oa_contract_approver_settings_get", "oa_create_contract_draft_post",
                     "oa_upload_attachment_post", "oa_submit_contract_post"))
async def _contract_create(run: Run, args: dict) -> dict:
    if args.get("approvers") and not args.get("attachment_ids"):
        raise HTTPException(422, "提交合同审批前必须至少有一份合同附件：请先上传附件，把 attachment_ids 一起传入")
    customer = await find_customer(run, args)
    approver_options = await run.read("oa_contract_approver_settings_get", {}, "可选合同审批人")
    allowed = {item.get("username"): item.get("display_name") for item in _items(approver_options) if item.get("selected")}
    unknown = [name for name in args.get("approvers") or [] if name not in allowed]
    if unknown:
        raise HTTPException(422, detail={"msg": f"这些人不在合同审批人名单里：{'、'.join(unknown)}",
                                         "allowed_approvers": [{"username": key, "display_name": value} for key, value in allowed.items()]})
    data = _drop_empty({"type": args["contract_type"], "fee_type": args["fee_type"], "contract_body": args.get("contract_body") or "律所",
                        "external_contract_numbers": args.get("external_contract_numbers"),
                        "external_contract_no": (args.get("external_contract_numbers") or [""])[0],
                        "amount": args.get("amount", 0), "signed_at": args.get("signed_at"), "customer_id": customer["id"],
                        "customer_no": customer.get("serial_no")})
    identity = await authenticated_identity()
    created = await run.write("oa_create_contract_draft_post", {"body": {
        "title": args["title"].strip(), "customer": customer.get("title"), "owner": identity["username"],
        "department": identity.get("department") or "", "description": args["description"], "data": data}}, "新建合同草稿")
    for attachment_id in args.get("attachment_ids") or []:
        await run.write("oa_upload_attachment_post", {"body": {"record_id": created.get("id"), "category": "合同附件", "remark": "智能体新建合同时挂附件"},
                                                      "files": {"file": attachment_id}}, f"挂合同附件 {attachment_id}")
    if args.get("approvers"):
        await run.write("oa_submit_contract_post", {"path": {"contract_id": created.get("id")}, "body": _drop_empty({
            "approvers": args["approvers"], "comment": args.get("submit_comment"), "sync_seal": args.get("sync_seal", False)})}, "提交合同审批")
    else:
        run.notes.append("未传 approvers：只建草稿不提交。可选审批人见 allowed_approvers。")
    return {"customer": _brief(customer), "contract": _created_ref(created),
            "allowed_approvers": [{"username": key, "display_name": value} for key, value in allowed.items()]}


@business_tool("biz_contract_change", "合同变更（含外部合同号）",
               "按合同编号找到合同，提交变更并重新审批。合同变更不能更换客户；外部合同号只有客户管理人能改。只传要改的字段。",
               {**CONTRACT_REF, "change_type": _desc(S, "变更类型"), "reason": _desc(S, "变更原因"),
                **CONTRACT_FIELDS, "title": _desc(S, "合同名称"), "end_date": _desc(DATE, "合同截止日期"),
                "description": _desc(S, "备注"), "approvers": _desc(NAMES, "合同审批人账号")},
               ("change_type", "reason", "approvers"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_contract_changes_get", "oa_change_contract_post"))
async def _contract_change(run: Run, args: dict) -> dict:
    contract = await find_record(run, "contract", args.get("contract_no"), args.get("contract_id"), "合同")
    history = await run.read("oa_contract_changes_get", {"path": {"contract_id": contract["id"]}}, "已有变更记录")
    body = _drop_empty({key: args.get(key) for key in ("change_type", "reason", "contract_body", "contract_type", "fee_type", "title", "amount",
                                                      "external_contract_numbers", "end_date", "signed_at", "description", "approvers")})
    if args.get("external_contract_numbers"):
        body["external_contract_no"] = args["external_contract_numbers"][0]
    await run.write("oa_change_contract_post", {"path": {"contract_id": contract["id"]}, "body": body}, "提交合同变更审批")
    return {"contract": _brief(contract), "previous_changes": _items(history)[:5]}


@business_tool("biz_contract_overview", "合同总览（我的合同/应收）",
               "按合同编号查合同详情，并带出名下案件、应收明细、回款和合同付款申请。",
               CONTRACT_REF, write=False,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_list_contract_object_cases_get", "oa_list_receivable_contracts_get",
                     "oa_list_contract_incoming_payments_get", "oa_list_contract_payment_applications_get"))
async def _contract_overview(run: Run, args: dict) -> dict:
    contract = await find_record(run, "contract", args.get("contract_no"), args.get("contract_id"), "合同")
    path = {"path": {"contract_id": contract["id"]}}
    cases = await run.read("oa_list_contract_object_cases_get", path, "名下案件")
    receivables = await run.read("oa_list_receivable_contracts_get", {"query": {"contract_no": contract.get("serial_no")}}, "应收汇总")
    incoming = await run.read("oa_list_contract_incoming_payments_get", path, "回款")
    payments = await run.read("oa_list_contract_payment_applications_get", path, "合同付款申请")
    return {"contract": contract, "cases": _items(cases) or cases, "receivables": receivables,
            "incoming_payments": _items(incoming) or incoming, "payment_applications": _items(payments) or payments}


@business_tool("biz_contract_payment_request", "合同付款（一键申请付款）",
               "把合同名下所有案件的待付费用一次申请付款（仅适合同一付款单位）。不传 fee_ids 则取全部待付余额。创建后即进入付款审批。",
               {**CONTRACT_REF, "payment_type_id": _desc(INT, "付款方式（付款单位）ID；不传时用候选里的第一个"),
                "application_date": _desc(DATE, "申请日期"), "payer_name": _desc(S, "交款人，默认合同客户"), "remark": _desc(S, "备注"),
                "fee_ids": {"type": "array", "items": INT, "maxItems": 200, "description": "只申请这些案件费用 ID（可选）"}},
               ("application_date",), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_contract_payment_candidates_get", "oa_create_contract_payment_application_post"))
async def _contract_payment(run: Run, args: dict) -> dict:
    contract = await find_record(run, "contract", args.get("contract_no"), args.get("contract_id"), "合同")
    candidates = await run.read("oa_contract_payment_candidates_get", {"path": {"contract_id": contract["id"]}}, "合同付款候选")
    rows = _items(candidates)
    if args.get("fee_ids"):
        wanted = set(args["fee_ids"])
        rows = [row for row in rows if row.get("case_fee_id") in wanted]
        missing = wanted - {row.get("case_fee_id") for row in rows}
        if missing:
            raise HTTPException(422, f"这些费用不在合同付款候选里：{sorted(missing)}")
    lines = [{"contract_object_id": row.get("contract_object_id"), "case_fee_id": row.get("case_fee_id"),
              "amount": float(row.get("remaining_amount") or 0), "remark": ""} for row in rows if float(row.get("remaining_amount") or 0) > 0]
    if not lines:
        raise HTTPException(409, "合同下没有待付余额的案件费用")
    types = (candidates or {}).get("payment_types") or [] if isinstance(candidates, dict) else []
    payment_type_id = args.get("payment_type_id") or (types[0].get("value") if types else None)
    if not payment_type_id:
        raise HTTPException(422, "请提供 payment_type_id（付款方式）；候选里没有可用的付款方式")
    await run.write("oa_create_contract_payment_application_post", {"path": {"contract_id": contract["id"]}, "body": _drop_empty({
        "payment_type_id": payment_type_id, "payer_name": args.get("payer_name") or contract.get("customer"),
        "application_date": args["application_date"], "remark": args.get("remark"), "lines": lines})}, "创建并提交合同付款申请")
    return {"contract": _brief(contract), "lines": lines, "total": round(sum(line["amount"] for line in lines), 2), "payment_types": types}


INVOICE_FIELDS = {
    "invoice_type": _desc(S, "发票类型，默认普票"), "service_name": _desc(S, "服务名称（开票内容），如 律师服务费"),
    "tax_rate": {"type": "number", "minimum": 0, "maximum": 100, "default": 0, "description": "税率(%)"},
    "tax_amount": {"type": "number", "minimum": 0, "default": 0, "description": "税额"},
    "extra_amount": {"type": "number", "minimum": 0, "description": "高开金额"},
    "delivery_method": _desc(S, "交付方式"), "recipient": _desc(S, "收件人"), "recipient_phone": _desc(S, "联系电话"),
    "email": _desc(S, "接收邮箱"), "delivery_address": _desc(S, "交付地址"), "remark": _desc(S, "备注"),
}


def _customer_invoice_defaults(customer: dict) -> dict:
    data = customer.get("data") or {}

    def first(*values):
        return next((str(value).strip() for value in values if str(value or "").strip()), "")
    return {"invoice_title": first(data.get("invoice_title"), customer.get("title")), "taxpayer_id": first(data.get("taxpayer_id"), data.get("credit_code")),
            "invoice_address": first(data.get("invoice_address"), data.get("registered_address")), "invoice_phone": first(data.get("invoice_phone"), data.get("phone")),
            "bank_name": first(data.get("bank_name")), "bank_account": first(data.get("bank_account"))}


async def _invoice(run: Run, args: dict, subjects: list[dict], customer: dict, *, contract: dict | None, case: dict | None) -> dict:
    if args.get("fee_ids"):
        wanted = set(args["fee_ids"])
        subjects = [row for row in subjects if int(row.get("fee_id") or 0) in wanted]
        missing = wanted - {int(row.get("fee_id") or 0) for row in subjects}
        if missing:
            raise HTTPException(422, f"这些费用不能开票（不是律师费或无可开余额）：{sorted(missing)}")
    allocations = [{"fee_id": int(row["fee_id"]), "amount": round(float(row.get("invoiceable_amount") or 0), 2)}
                   for row in subjects if float(row.get("invoiceable_amount") or 0) > 0]
    if not allocations:
        raise HTTPException(409, "没有可开票余额的律师费（成本费用不可开票）")
    total = round(sum(item["amount"] for item in allocations), 2)
    defaults = _customer_invoice_defaults(customer)
    missing = [label for key, label in (("invoice_title", "发票抬头"), ("taxpayer_id", "纳税人识别号")) if not defaults[key]]
    if missing:
        raise HTTPException(422, f"客户档案缺少{'、'.join(missing)}，请先用 biz_customer_maintain 补全开票信息")
    case_nos = sorted({row.get("case_no") for row in subjects if row.get("case_no")})
    service = {"service_name": args.get("service_name") or "律师服务费", "quantity": 1, "unit_price": total, "amount": total,
               "tax_rate": args.get("tax_rate", 0), "tax_amount": args.get("tax_amount", 0)}
    body = _drop_empty({**defaults, "customer": customer.get("title"), "amount": total, "extra_amount": args.get("extra_amount"),
                        "invoice_type": args.get("invoice_type") or "普票", "invoice_content": service["service_name"],
                        "case_no": case_nos[0] if len(case_nos) == 1 else "", "contract_record_id": (contract or {}).get("id"),
                        "case_record_id": (case or {}).get("id"), "case_fee_ids": [item["fee_id"] for item in allocations],
                        "case_fee_allocations": allocations, "service_items": [service],
                        **{key: args.get(key) for key in ("delivery_method", "recipient", "recipient_phone", "email", "delivery_address", "remark")}})
    created = await run.write("oa_create_invoice_application_post", {"body": body}, "新建开票申请草稿")
    await run.write("oa_submit_invoice_application_post", {"path": {"invoice_id": created.get("id")}, "body": _drop_empty({"comment": args.get("remark")})}, "提交开票申请")
    return {"allocations": allocations, "total": total, "invoice_info": defaults}


@business_tool("biz_contract_invoice_request", "合同开票（多案合并申请开票）",
               "合同名下案件的律师费一次申请开票（同一开票单位）。开票信息从客户档案带出；不传 fee_ids 则开全部可开余额。",
               {**CONTRACT_REF, **INVOICE_FIELDS, "fee_ids": {"type": "array", "items": INT, "maxItems": 100, "description": "只开这些费用 ID（可选）"}},
               write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_contract_invoice_candidates_get", "oa_list_customers_get",
                     "oa_create_invoice_application_post", "oa_submit_invoice_application_post"))
async def _contract_invoice(run: Run, args: dict) -> dict:
    contract = await find_record(run, "contract", args.get("contract_no"), args.get("contract_id"), "合同")
    candidates = await run.read("oa_contract_invoice_candidates_get", {"path": {"contract_id": contract["id"]}}, "合同可开票费用")
    customer_id = (contract.get("data") or {}).get("customer_id")
    customer = await find_customer(run, {"customer_id": customer_id} if customer_id else {"customer_name": contract.get("customer")})
    detail = await _invoice(run, args, _items(candidates), customer, contract=contract, case=None)
    return {"contract": _brief(contract), **detail}


@business_tool("biz_investigation_task_publish", "新建调查任务（按合同发布）",
               "案源人/品牌管理人在合同下发布调查任务。",
               {**CONTRACT_REF, "title": _desc(S, "任务标题，默认用合同名称"), "owner": _desc(S, "分配人（调查组长）账号"),
                "right_type": _desc(S, "权利类型，如 商标"), "customer_review": {"type": "boolean", "description": "线索是否需客户审核"},
                "authorized_from": _desc(DATE, "授权开始日期"), "authorized_to": _desc(DATE, "授权结束日期"),
                "investigation_region": _desc(S, "授权范围（页面“授权范围”，如 全国）"), "authorization_scope": _desc(S, "授权区域（页面“授权区域”，如 全国，或具体省市）"),
                "attachment_ids": ATTACHMENTS, "description": _desc(S, "备注")},
               ("right_type", "customer_review", "authorized_from", "authorized_to", "investigation_region", "authorization_scope"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_create_contract_investigation_post"))
async def _investigation_publish(run: Run, args: dict) -> dict:
    contract = await find_record(run, "contract", args.get("contract_no"), args.get("contract_id"), "合同")
    body = _drop_empty({"title": args.get("title") or contract.get("title"), "owner": args.get("owner"), "right_type": args["right_type"],
                        "customer_review": args["customer_review"], "authorized_from": args["authorized_from"], "authorized_to": args["authorized_to"],
                        "region": args.get("investigation_region"), "authorization_scope": args.get("authorization_scope"),
                        "attachment_ids": args.get("attachment_ids"), "description": args.get("description")})
    body["customer_review"] = args["customer_review"]
    created = await run.write("oa_create_contract_investigation_post", {"path": {"contract_id": contract["id"]}, "body": body}, "发布调查任务")
    return {"contract": _brief(contract), "investigation": _created_ref(created)}


# ---------- 03 调查大厅 ----------

@business_tool("biz_investigation_subtask_assign", "新增调查子任务（组长分配）",
               "调查组长在“待我分配的调查任务”下给调查员新增子任务。",
               {"investigation_no": _desc(S, "调查编号，如 RW2609262613143"), "investigation_id": INT, "title": _desc(S, "任务名称"),
                "investigator": _desc(S, "调查员账号"), "deadline": _desc(DATE, "截止日期"), "start_date": DATE, "end_date": DATE,
                "priority": _desc(S, "优先级"), "description": _desc(S, "备注"),
                "investigation_regions": {"type": "array", "maxItems": 50, "items": {"type": "array", "minItems": 1, "maxItems": 3, "items": S},
                                          "description": "调查区域，每项是 省/市/区 路径，如 [[\"上海市\"], [\"浙江省\", \"杭州市\"]]"}},
               ("title", "investigator", "deadline"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_create_investigation_task_post"))
async def _subtask(run: Run, args: dict) -> dict:
    record = await find_record(run, "investigation", args.get("investigation_no"), args.get("investigation_id"), "调查任务")
    data = record.get("data") or {}
    body = _drop_empty({"title": args["title"], "owner": args["investigator"], "deadline": args["deadline"], "start_date": args.get("start_date"),
                        "end_date": args.get("end_date"), "priority": args.get("priority"), "investigation_regions": args.get("investigation_regions"),
                        "description": args.get("description"), "contract_record_id": data.get("contract_record_id") or data.get("contract_id")})
    created = await run.write("oa_create_investigation_task_post", {"path": {"record_id": record["id"]}, "body": body}, "新增调查子任务")
    return {"investigation": _brief(record), "subtask": _created_ref(created)}


CLUE_FIELDS = {
    "infringement_method": _desc(S, "侵权方式"), "sales_channel": _desc(S, "销售渠道（电商平台/实体店铺…）"), "product": _desc(S, "侵权产品"),
    "store_url": _desc(S, "店铺链接"), "shop_name": _desc(S, "店铺名称"), "shop_id": _desc(S, "店铺 ID"),
    "has_product": {"type": "boolean", "description": "有无产品"}, "product_url": _desc(S, "产品链接"), "sale_num": _desc(S, "规模/销量"),
    "address": _desc(S, "调查地址"), "investigated_at": _desc(DATE, "调查日期"), "producer": _desc(S, "生产商"),
    "indictees": {"type": "array", "maxItems": 20, "items": {"type": "object", "required": ["name"], "properties": {"name": S}},
                  "description": "主体信息（被调查主体）"},
    "investigation_assistant": _desc(S, "调查辅助员"), "right_type": _desc(S, "权利类型"), "region": _desc(S, "调查区域"),
    "source": _desc(S, "来源"), "source_owner": _desc(S, "案源人"),
}


@business_tool("biz_clue_create", "新增调查线索（暂存或提交）",
               "调查员在“我的调查任务”下新增线索、挂附件，submit=true 时直接提交审批。一条线索只能对应一个品牌、一个侵权产品。",
               {"task_no": _desc(S, "调查任务/子任务编号"), "task_id": INT, "customer": _desc(S, "客户（权利人），默认取任务"),
                **CLUE_FIELDS, "description": _desc(S, "备注"), "attachment_ids": _desc(ATTACHMENTS, "线索附件 ID"),
                "submit": {"type": "boolean", "default": False, "description": "true=提交审批；false=暂存"}},
               ("sales_channel", "product"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_create_investigation_record_post", "oa_upload_attachment_post",
                     "oa_submit_investigation_clue_post"))
async def _clue_create(run: Run, args: dict) -> dict:
    task = None
    if args.get("task_no") or args.get("task_id"):
        task = await find_record(run, "investigation", args.get("task_no"), args.get("task_id"), "调查任务")
    task_data = (task or {}).get("data") or {}
    identity = await authenticated_identity()
    data = _drop_empty({key: args.get(key) for key in CLUE_FIELDS})
    data.update(platform=args["sales_channel"], publisher=identity["username"], has_product=bool(args.get("has_product")),
                indictee=(args.get("indictees") or [{}])[0].get("name", ""), customer_review=bool(task_data.get("customer_review")))
    if task:
        data.update(source_task_id=task["id"], source_task_no=task.get("serial_no"))
        data.setdefault("right_type", task_data.get("right_type", ""))
    created = await run.write("oa_create_investigation_record_post", {"body": {
        "module": "clue", "serial_no": "", "title": "", "customer": args.get("customer") or (task or {}).get("customer") or "",
        "status": "草稿", "owner": identity["username"], "department": identity.get("department") or "", "description": args.get("description") or "", "data": data}},
        "新建线索（暂存）")
    for attachment_id in args.get("attachment_ids") or []:
        await run.write("oa_upload_attachment_post", {"body": {"record_id": created.get("id"), "category": "调查线索附件", "remark": "新建线索附件"},
                                                      "files": {"file": attachment_id}}, f"挂线索附件 {attachment_id}")
    if args.get("submit"):
        await run.write("oa_submit_investigation_clue_post", {"path": {"clue_id": created.get("id")}, "body": {"comment": "提交线索审批"}}, "提交线索审批")
    return {"task": _brief(task) if task else None, "clue": _created_ref(created)}


CLUE_VIEWS = {"待提交": ["草稿"], "待审核": ["待审批"], "待客户审核": ["待客户审核"], "已拒绝": ["已驳回", "已拒绝"],
              "待取证": ["待取证"], "已取证": ["已取证", "已转案件"]}  # 与“我的调查线索”各页签一致


@business_tool("biz_my_clues", "我的调查线索",
               "按状态查线索：待提交/待审核/待取证/已取证，或按关键字、公证书号查。",
               {"status_group": {"type": "string", "enum": list(CLUE_VIEWS), "description": "线索分组"},
                "keyword": _desc(S, "关键字（店铺、权利人、线索号等）"), "notary_no": _desc(S, "公证书号"),
                "page": {"type": "integer", "minimum": 1, "default": 1}},
               write=False, uses=("oa_list_records_get",))
async def _my_clues(run: Run, args: dict) -> dict:
    query = _drop_empty({"module": "clue", "keyword": args.get("keyword"), "notary_no": args.get("notary_no"),
                         "statuses": ",".join(CLUE_VIEWS.get(args.get("status_group")) or []), "page": args.get("page", 1), "page_size": 50})
    result = await run.read("oa_list_records_get", {"query": query}, "查询线索")
    return {"clues": [_brief(row, "id", "serial_no", "customer", "status", "owner") | {
        key: (row.get("data") or {}).get(key) for key in ("shop_name", "sales_channel", "product", "notarization_no", "case_no")} for row in _items(result)],
            "total": result.get("total") if isinstance(result, dict) else None}


@business_tool("biz_clue_review", "线索审核",
               "案源人/客户管理人审核线索：先查疑似冲突再给结论。审核属不可撤回操作，提交后须本人在 OA 网页确认。",
               {"clue_no": _desc(S, "线索编号"), "clue_id": INT, "approved": {"type": "boolean", "description": "true=通过；false=驳回"},
                "comment": _desc(S, "审核意见"), "supplement_evidence": {"type": "boolean", "description": "属于补充取证"},
                "merge_into_case_no": _desc(S, "补充取证时并入的案号")},
               ("approved", "comment"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_investigation_clue_conflicts_get", "oa_review_investigation_clue_post"))
async def _clue_review(run: Run, args: dict) -> dict:
    clue = await find_record(run, "clue", args.get("clue_no"), args.get("clue_id"), "线索")
    conflicts = await run.read("oa_investigation_clue_conflicts_get", {"path": {"clue_id": clue["id"]}}, "疑似冲突线索/案件")
    await run.write("oa_review_investigation_clue_post", {"path": {"clue_id": clue["id"]}, "body": _drop_empty({
        "approved": args["approved"], "comment": args["comment"], "supplement_evidence": args.get("supplement_evidence"),
        "merge_into_case_no": args.get("merge_into_case_no")}) | {"approved": args["approved"]}}, "提交审核结论")
    return {"clue": _brief(clue), "conflicts": conflicts}


async def _clue_ids(run: Run, clue_nos: list[str] | None, clue_ids: list[int] | None) -> list[int]:
    ids = list(clue_ids or [])
    for clue_no in clue_nos or []:
        ids.append((await find_record(run, "clue", clue_no, None, "线索"))["id"])
    if not ids:
        raise HTTPException(422, "请提供 clue_nos（线索编号）或 clue_ids")
    return ids


CLUE_LIST = {"clue_nos": {"type": "array", "items": S, "maxItems": 50, "description": "线索编号"},
             "clue_ids": {"type": "array", "items": INT, "maxItems": 50, "description": "线索 ID"}}


@business_tool("biz_clue_register_collection", "线索取证登记",
               "取证当日把一条或多条待取证线索登记为已取证（取证时间、公证机构、公证书号、仓库库位等）。",
               {**CLUE_LIST, "collected_at": _desc(DATE, "取证日期"), "notary_institution": _desc(S, "取证机构/公证处"),
                "notarization_no": _desc(S, "公证书号"), "invoice_no": _desc(S, "发票号码"), "warehouse_id": INT, "storage_location_id": INT,
                "evidence_status": _desc(S, "证物状态"), "comment": _desc(S, "取证说明")},
               ("collected_at", "notary_institution"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_investigation_evidence_storage_options_get", "oa_register_clue_collection_post",
                     "oa_register_clue_collection_batch_post"))
async def _collect(run: Run, args: dict) -> dict:
    ids = await _clue_ids(run, args.get("clue_nos"), args.get("clue_ids"))
    storage = await run.read("oa_investigation_evidence_storage_options_get", {}, "仓库/库位选项")
    body = _drop_empty({key: args.get(key) for key in ("collected_at", "notary_institution", "notarization_no", "invoice_no", "warehouse_id",
                                                      "storage_location_id", "evidence_status", "comment")})
    if len(ids) == 1:  # 批量接口要求至少两条
        await run.write("oa_register_clue_collection_post", {"path": {"clue_id": ids[0]}, "body": body}, "登记取证")
    else:
        await run.write("oa_register_clue_collection_batch_post", {"body": {"clue_ids": ids, **body}}, "批量登记取证")
    return {"clue_ids": ids, "storage_options": storage}


@business_tool("biz_clues_to_cases", "线索生成案件（批量）",
               "已取证线索批量生成案件，一条线索一个案件；补充取证的线索不要生成案件，应并入原案件。",
               {**CLUE_LIST, "client_position": {"type": "string", "enum": ["原告/申请人", "被告/被申请人", "第三人"], "description": "客户诉讼地位"}, "case_phase": _desc(S, "案件阶段"),
                "handling_lawyer": _desc(S, "经办律师账号"), "assistant": _desc(S, "律师助理账号"), "cause_or_charge": _desc(S, "案由"),
                "case_type": _desc(S, "案件类型"), "court": _desc(S, "拟管辖法院"), "contract_record_id": _desc(INT, "补绑来源任务合同 ID（可选）")},
               ("client_position", "case_phase", "handling_lawyer"), write=True,
               uses=("oa_list_records_get", "oa_get_record_get", "oa_resolve_clue_case_contracts_post", "oa_batch_create_cases_from_clues_post"))
async def _clues_to_cases(run: Run, args: dict) -> dict:
    ids = await _clue_ids(run, args.get("clue_nos"), args.get("clue_ids"))
    contracts = await run.read("oa_resolve_clue_case_contracts_post", {"body": {"clue_ids": ids}}, "核对线索可用合同")
    body = _drop_empty({key: args.get(key) for key in ("contract_record_id", "client_position", "case_phase", "handling_lawyer", "assistant",
                                                      "cause_or_charge", "case_type", "court")})
    created = await run.write("oa_batch_create_cases_from_clues_post", {"body": {"clue_ids": ids, **body}}, "批量生成案件")
    return {"clue_ids": ids, "contract_check": contracts, "result": created if not (isinstance(created, dict) and created.get("planned")) else None}


# ---------- 04 案件管理 ----------

@business_tool("biz_case_overview", "案件总览（费用/附件/任务/办案指引）",
               "按我方案号查案件，并带出案件费用、附件、任务和办案指引（含付款三要素是否齐全的提示）。",
               CASE_REF, write=False,
               uses=("oa_search_ordinary_cases_post", "oa_get_record_get", "oa_list_case_relations_get", "oa_list_attachments_get",
                     "oa_list_case_tasks_get", "oa_get_case_workflow_guide_get"))
async def _case_overview(run: Run, args: dict) -> dict:
    case = await find_case(run, args)
    detail = await run.read("oa_get_record_get", {"path": {"record_id": case["id"]}}, "案件详情")
    relations = await run.read("oa_list_case_relations_get", {"path": {"case_id": case["id"]}, "query": {"include": "fees"}}, "案件费用")
    fees = (relations or {}).get("fees") or [] if isinstance(relations, dict) else []
    files = await run.read("oa_list_attachments_get", {"query": {"record_id": case["id"], "page_size": 100}}, "案件附件")
    tasks = await run.read("oa_list_case_tasks_get", {"path": {"case_id": case["id"]}}, "案件任务")
    guide = await run.read("oa_get_case_workflow_guide_get", {"path": {"case_id": case["id"]}}, "办案指引")
    return {"case": detail, "fees": [_brief(row, "id", "serial_no", "title", "status") | {
        key: (row.get("data") or {}).get(key) for key in ("fee_type", "amount", "expense_scope", "paid_amount", "payment_requested_amount", "refund_amount")}
        for row in _items(fees)], "attachments": [_brief(row, "id", "original_name", "category", "created_at") for row in _items(files)],
            "tasks": _items(tasks) or tasks, "workflow_guide": guide}


PARTY_LIST = {"type": "array", "maxItems": 50, "items": {"type": "object", "additionalProperties": False, "required": ["name", "organization_type", "identity_no"],
              "properties": {"name": _desc(S, "名称/姓名"), "organization_type": {"type": "string", "enum": ["公司企业", "个人", "个体工商户", "事业单位", "机关团体", "其他"]},
                             "identity_no": _desc(S, "统一社会信用代码或身份证号")}}}


@business_tool("biz_case_create_from_contract", "从合同新建案件",
               "个案模式：选合同新建案件（无合同不能建案；批量维权案件应从线索生成）。建案后写入当事人。",
               {**CONTRACT_REF, "title": _desc(S, "案件名称"), "case_type": _desc(S, "案件类型，如 民事案件、刑事案件、法律顾问"), "client_position": {"type": "string", "enum": ["原告/申请人", "被告/被申请人", "第三人"], "description": "客户诉讼地位"},
                "cause_or_charge": _desc(S, "案由"), "status": _desc(S, "案件阶段"), "handling_lawyers": _desc(NAMES, "经办律师账号"),
                "assistant": _desc(S, "律师助理账号"), "investigator": _desc(S, "调查员"), "source_person": _desc(S, "案源人"),
                "right_type": _desc(S, "权利类型"), "investigation_clue": _desc(S, "调查线索编号"),
                "court": _desc(S, "一审法院"), "court_case_no": _desc(S, "法院案号"), "courtroom": _desc(S, "法庭"), "judge": _desc(S, "法官"),
                "filing_date": _desc(DATE, "立案日期"), "hearing_date": _desc(DATE, "开庭日期"), "description": _desc(S, "案情说明"),
                "plaintiffs": _desc(PARTY_LIST, "原告"), "defendants": _desc(PARTY_LIST, "被告"), "third_parties": _desc(PARTY_LIST, "第三人")},
               ("title", "case_type", "client_position", "handling_lawyers"), write=True,
               uses=("oa_list_case_eligible_contracts_get", "oa_list_records_get", "oa_get_record_get", "oa_create_case_post", "oa_update_case_litigants_put",
                     "oa_complete_case_creation_put", "oa_update_case_judicial_put"))
async def _case_create(run: Run, args: dict) -> dict:
    contract = await find_record(run, "contract", args.get("contract_no"), args.get("contract_id"), "合同")
    eligible = await run.read("oa_list_case_eligible_contracts_get", {}, "核对合同可建案")
    if contract["id"] not in {row.get("id") for row in _items(eligible)}:
        raise HTTPException(409, "该合同当前不能新建案件（未审批通过、已归档或无权）")
    body = _drop_empty({key: args.get(key) for key in ("title", "case_type", "client_position", "cause_or_charge", "status", "handling_lawyers",
                                                      "assistant", "investigator", "source_person", "right_type", "investigation_clue", "court",
                                                      "court_case_no", "courtroom", "judge", "filing_date", "hearing_date", "description")})
    created = await run.write("oa_create_case_post", {"body": {"contract_record_id": contract["id"], "customer": contract.get("customer"), **body}}, "新建案件")
    parties = {}
    for key, singular in (("plaintiffs", "plaintiff"), ("defendants", "defendant"), ("third_parties", "third_party")):
        if args.get(key):
            parties[key] = [item["name"] for item in args[key]]
            parties[singular + "_identities"] = args[key]
    if parties:
        await run.write("oa_update_case_litigants_put", {"path": {"case_id": created.get("id")}, "body": parties}, "写入当事人")
    if args["case_type"] == "法律顾问":  # 与新建案件页面一致：顾问案件直接完成，其余案件经司法机关步骤完成
        await run.write("oa_complete_case_creation_put", {"path": {"case_id": created.get("id")}, "body": {"comment": args.get("description") or ""}}, "完成新建")
    else:
        judicial = _drop_empty({key: args.get(key) for key in ("court", "court_case_no", "courtroom", "judge", "filing_date", "hearing_date")})
        await run.write("oa_update_case_judicial_put", {"path": {"case_id": created.get("id")}, "body": judicial}, "写入法院信息并完成新建")
    return {"contract": _brief(contract), "case": _created_ref(created)}


@business_tool("biz_case_fill_payment_elements", "补齐付款三要素",
               "申请官费付款前补齐三要素：人员要素（案源人、调查员、文书、开庭律师）、法院要素（法院、案号、法庭、开庭时间）、文档要素（缴费通知书/公证书）。只做传入的部分。",
               {**CASE_REF,
                "people": {"type": "object", "additionalProperties": False, "description": "人员要素", "properties": {
                    "hearing_lawyer": _desc(S, "开庭律师"), "handling_lawyers": _desc(NAMES, "经办律师"), "assistant": _desc(S, "律师助理/文书"),
                    "source_lawyer": _desc(S, "案源人"), "case_stage": _desc(S, "案件阶段")}},
                "court": {"type": "object", "additionalProperties": False, "description": "法院要素（同页面“修改法院信息”）", "properties": {
                    "level": {"type": "string", "enum": ["first", "second", "retrial"], "default": "first", "description": "审级：first 一审、second 二审、retrial 再审"},
                    "court": _desc(S, "法院名称"), "court_case_no": _desc(S, "法院案号"), "courtroom": _desc(S, "法庭"),
                    "hearing_date": _desc(DATE, "开庭日期"), "hearing_time": _desc(S, "开庭时间 HH:MM"), "judge": _desc(S, "法官"), "clerk": _desc(S, "书记员"),
                    "filing_date": _desc(DATE, "立案日期")}},
                "documents": {"type": "object", "additionalProperties": False, "required": ["category", "attachment_ids"], "description": "文档要素",
                              "properties": {"category": _desc(S, "文档类型文件夹，如 法院缴费通知书、公证书"), "attachment_ids": ATTACHMENTS}},
                "comment": _desc(S, "修改说明")},
               write=True,
               uses=("oa_search_ordinary_cases_post", "oa_get_record_get", "oa_batch_update_cases_post", "oa_update_case_court_info_put", "oa_upload_attachment_post"))
async def _payment_elements(run: Run, args: dict) -> dict:
    if not any(args.get(key) for key in ("people", "court", "documents")):
        raise HTTPException(422, "请至少提供 people、court、documents 中的一项")
    case = await find_case(run, args)
    if args.get("people"):
        await run.write("oa_batch_update_cases_post", {"body": _drop_empty({"case_ids": [case["id"]], **args["people"], "comment": args.get("comment")})}, "补人员要素")
    if args.get("court"):
        court = args["court"]
        prefix = court.get("level", "first") + "_court"
        hearing = court.get("hearing_date") and f"{court['hearing_date']} {court.get('hearing_time') or '00:00'}:00"[:19]
        body = {f"{prefix}_name": court.get("court"), f"{prefix}_case_no": court.get("court_case_no"), f"{prefix}_courtroom": court.get("courtroom"),
                f"{prefix}_judge": court.get("judge"), f"{prefix}_clerk": court.get("clerk"), f"{prefix}_filing_date": court.get("filing_date"),
                f"{prefix}_hearing_date": hearing}
        if prefix == "first_court":
            body.update(courtroom=court.get("courtroom"), judge=court.get("judge"), clerk=court.get("clerk"))
        await run.write("oa_update_case_court_info_put", {"path": {"case_id": case["id"]}, "body": {**_drop_empty(body), "comment": "补付款法院要素"}}, "补法院要素")
    for attachment_id in (args.get("documents") or {}).get("attachment_ids") or []:
        await run.write("oa_upload_attachment_post", {"body": {"record_id": case["id"], "category": args["documents"]["category"], "remark": "补付款文档要素"},
                                                      "files": {"file": attachment_id}}, f"上传文档要素 {attachment_id}")
    return {"case": _brief(case)}


@business_tool("biz_case_fee_create_and_request_payment", "新增案件费用并申请付款",
               "在案件里新增官费/代理费/第三方费用/其他费用/内部费用；request_payment=true 时先检查付款三要素，再申请付款。"
               "费用范围：律所费用→财务中心；平台费用→平台财务中心；内部费用→内部结算。",
               {**CASE_REF, "expense_scope": {"type": "string", "enum": ["律所", "平台", "内部"], "description": "费用范围"},
                "fee_type": _desc(S, "费用大类：官费/代理费/第三方费用/其他费用/内部费用"), "fee_type_id": _desc(INT, "费用类型 ID（如 一审诉讼费），见 oa_list_finance_payment_types_get"),
                "expense_subtype": _desc(S, "费用子类，如 诉讼费、公证费"), "title": _desc(S, "费用名称"), "amount": MONEY,
                "handler": _desc(S, "经办人员账号"), "payee": _desc(S, "收款单位"), "court": _desc(S, "缴费法院/机构"),
                "document_no": _desc(S, "缴费通知文号"), "description": _desc(S, "说明"), "contract_record_id": _desc(INT, "费用归属合同 ID；不传时取案件合同"),
                "request_payment": {"type": "boolean", "default": False, "description": "建好后直接申请付款"},
                "payment_type_id": _desc(INT, "付款方式 ID"), "payment_account": _desc(S, "收款账户"), "payment_payee": _desc(S, "收款人"),
                "payment_remark": _desc(S, "付款备注")},
               ("expense_scope", "fee_type", "title", "amount", "handler"), write=True,
               uses=("oa_search_ordinary_cases_post", "oa_get_record_get", "oa_list_case_fee_contracts_get", "oa_create_finance_fee_post",
                     "oa_finance_fee_readiness_get", "oa_submit_finance_fee_post"))
async def _case_fee(run: Run, args: dict) -> dict:
    case = await find_case(run, args)
    body_scope = "平台" if args["expense_scope"] == "平台" else "律所"
    contracts = await run.read("oa_list_case_fee_contracts_get", {"path": {"case_id": case["id"]}, "query": {"expense_scope": body_scope}}, "费用可归属合同")
    contract_id = args.get("contract_record_id")
    scoped = _items(contracts)
    if contract_id and contract_id not in {row.get("id") for row in scoped}:
        raise HTTPException(409, f"合同 {contract_id} 不是这个案件可归属{body_scope}费用的合同")
    if not contract_id:
        if args["expense_scope"] != "内部" and not scoped:
            raise HTTPException(409, "案件没有可归属的合同；客户只有律所合同时不能新增平台费用，需先新建平台合同")
        contract_id = scoped[0].get("id") if len(scoped) == 1 else None
        if args["expense_scope"] != "内部" and contract_id is None:
            raise HTTPException(409, detail={"msg": "案件有多份可归属合同，请用 contract_record_id 指定", "candidates": [_brief(row) for row in scoped[:10]]})
    body = _drop_empty({"title": args["title"], "customer": case.get("customer"), "amount": args["amount"], "fee_type": args["fee_type"],
                        "fee_type_id": args.get("fee_type_id"), "expense_scope": args["expense_scope"], "expense_subtype": args.get("expense_subtype"),
                        "case_no": case.get("serial_no"), "case_record_id": case["id"], "contract_record_id": contract_id, "handler": args["handler"],
                        "court": args.get("court"), "document_no": args.get("document_no"), "payee": args.get("payee"), "description": args.get("description")})
    created = await run.write("oa_create_finance_fee_post", {"body": body}, "新增费用（草稿）")
    readiness = None
    if args.get("request_payment"):
        if run.confirm:
            readiness = await run.read("oa_finance_fee_readiness_get", {"path": {"fee_id": created.get("id")}}, "检查付款三要素")
            if isinstance(readiness, dict) and readiness.get("ready") is False:
                run.notes.append("费用已建为草稿，但付款三要素不全，未申请付款；补齐后再申请。")
                return {"case": _brief(case), "fee": _created_ref(created), "readiness": readiness}
        else:
            run.notes.append("执行时会先检查付款三要素，不齐全则只建草稿不申请付款。")
        await run.write("oa_submit_finance_fee_post", {"path": {"fee_id": created.get("id")}, "body": _drop_empty({
            "amount": args["amount"], "payment_type_id": args.get("payment_type_id"), "payment_account": args.get("payment_account"),
            "payment_payee": args.get("payment_payee"), "payment_remark": args.get("payment_remark")})}, "申请付款")
    return {"case": _brief(case), "fee": _created_ref(created), "readiness": readiness}


@business_tool("biz_case_invoice_request", "案件申请开票",
               "选案件的律师费申请开票（成本费用不可开票）；开票信息从客户档案带出。",
               {**CASE_REF, **INVOICE_FIELDS, "fee_ids": {"type": "array", "items": INT, "maxItems": 100, "description": "只开这些费用 ID（可选）"}},
               write=True,
               uses=("oa_search_ordinary_cases_post", "oa_get_record_get", "oa_list_records_get", "oa_contract_invoice_candidates_get",
                     "oa_list_customers_get", "oa_create_invoice_application_post", "oa_submit_invoice_application_post"))
async def _case_invoice(run: Run, args: dict) -> dict:
    case = await find_case(run, args)
    data = case.get("data") or {}
    contract_id = data.get("contract_record_id") or data.get("contract_id")
    if not contract_id:
        raise HTTPException(409, "案件没有关联合同，不能开票")
    contract = await run.read("oa_get_record_get", {"path": {"record_id": contract_id}}, "案件合同")
    candidates = await run.read("oa_contract_invoice_candidates_get", {"path": {"contract_id": contract_id}}, "可开票费用")
    subjects = [row for row in _items(candidates) if row.get("case_no") == case.get("serial_no")]
    customer_id = (contract.get("data") or {}).get("customer_id")
    customer = await find_customer(run, {"customer_id": customer_id} if customer_id else {"customer_name": case.get("customer")})
    detail = await _invoice(run, args, subjects, customer, contract=contract, case=case)
    return {"case": _brief(case), **detail}


@business_tool("biz_case_court_refund", "诉讼费法院退费",
               "判决/调解/裁定诉讼费由法院退还时，把退费金额关联到案件的具体费用，首页“待退费”会跟踪到账。金额为 0 表示撤销退费。",
               {**CASE_REF, "fee_id": _desc(INT, "要退费的案件费用 ID（见 biz_case_overview 的 fees）"), "amount": {"type": "number", "minimum": 0, "description": "退费金额"},
                "expected_date": _desc(DATE, "预计到账日"), "remark": _desc(S, "备注")},
               ("fee_id", "amount"), write=True,
               uses=("oa_search_ordinary_cases_post", "oa_get_record_get", "oa_create_litigation_refund_post", "oa_clear_finance_fee_court_refund_projection_post"))
async def _court_refund(run: Run, args: dict) -> dict:
    case = await find_case(run, args)
    fee = await run.read("oa_get_record_get", {"path": {"record_id": args["fee_id"]}}, "读取费用")
    fee_data = fee.get("data") or {}
    if fee.get("module") != "finance" or fee_data.get("case_no") not in (None, "", case.get("serial_no")):
        raise HTTPException(409, "该费用不属于这个案件")
    if args["amount"] == 0:
        await run.write("oa_clear_finance_fee_court_refund_projection_post", {"path": {"fee_id": fee["id"]}}, "法院退费金额归零")
        return {"case": _brief(case), "fee": _brief(fee)}
    from uuid import uuid5, NAMESPACE_URL
    request_key = uuid5(NAMESPACE_URL, f"biz-court-refund:{fee['id']}:{args['amount']}").hex
    identity = await authenticated_identity()
    body = _drop_empty({"request_key": request_key, "fee_record_id": fee["id"], "customer": case.get("customer"), "case_no": case.get("serial_no"),
                        "court": fee_data.get("court") or (case.get("data") or {}).get("court") or "", "original_payment_no": fee_data.get("document_no") or fee.get("serial_no"),
                        "amount": args["amount"], "applicant": identity.get("display_name") or identity["username"], "expected_date": args.get("expected_date"),
                        "reason": "代理费法院退费" if fee_data.get("fee_type") == "代理费" else "诉讼费退款", "remark": args.get("remark")})
    created = await run.write("oa_create_litigation_refund_post", {"body": body}, "登记法院退费")
    return {"case": _brief(case), "fee": _brief(fee), "refund": _created_ref(created)}


@business_tool("biz_task_create", "发起案件任务",
               "给自己或他人发起任务（手动任务），设定负责人、期限（一般 30 日内），可关联案件、协作人。",
               {"title": _desc(S, "任务内容"), "owner": _desc(S, "负责人账号"), "deadline": _desc(DATE, "截止日期"),
                "start_at": _desc(S, "开始时间"), "end_at": _desc(S, "结束时间"), "priority": _desc(S, "优先级"),
                "collaborators": _desc(NAMES, "协作人"), "case_nos": _desc(NAMES, "关联案号"), "customer": _desc(S, "客户"),
                "description": _desc(S, "任务说明")},
               ("title", "owner", "deadline"), write=True, uses=("oa_create_task_post",))
async def _task_create(run: Run, args: dict) -> dict:
    created = await run.write("oa_create_task_post", {"body": _drop_empty({**args, "task_type": "手动任务"})}, "发起任务")
    return {"task": _created_ref(created)}


TASK_ACTIONS = {"accept": ("oa_accept_task_post", "接受任务"), "reject": ("oa_reject_task_post", "拒绝任务"),
                "handoff": ("oa_handoff_task_post", "转交任务"), "complete": ("oa_complete_task_post", "完成任务"),
                "confirm": ("oa_confirm_task_post", "发起人确认完成"), "restart": ("oa_restart_task_post", "重启任务"),
                "feedback": ("oa_create_task_feedback_post", "任务沟通留言")}


@business_tool("biz_task_act", "任务流转与沟通",
               "任务负责人/发起人办理任务：accept 接受、reject 拒绝（须写理由）、handoff 转交（不要先点完成）、complete 完成、confirm 发起人确认、restart 重启、feedback 留言。",
               {"task_id": INT, "action": {"type": "string", "enum": list(TASK_ACTIONS)}, "comment": _desc(S, "理由/说明/留言"),
                "recipient": _desc(S, "转交接收人账号（handoff 必填）"), "end_at": _desc(S, "转交结束时间")},
               ("task_id", "action"), write=True, uses=tuple(item[0] for item in TASK_ACTIONS.values()))
async def _task_act(run: Run, args: dict) -> dict:
    action = args["action"]
    if action == "reject" and not args.get("comment"):
        raise HTTPException(422, "拒绝任务必须写明理由（comment）")
    if action == "handoff" and not args.get("recipient"):
        raise HTTPException(422, "转交任务需要 recipient（接收人）")
    if action == "feedback" and not args.get("comment"):
        raise HTTPException(422, "留言内容 comment 不能为空")
    tool, purpose = TASK_ACTIONS[action]
    body = _drop_empty({"comment": args.get("comment"), **({"recipient": args.get("recipient"), "end_at": args.get("end_at")} if action == "handoff" else {})})
    await run.write(tool, {"path": {"task_id": args["task_id"]}, "body": body}, purpose)
    return {}


# ---------- 05 控制台 ----------

@business_tool("biz_dashboard_todo", "控制台待办",
               "我的待办事项（待处理任务、待审批线索）、待确认事项（待缴官费、待退费、待上诉、待执行、补充证据/意见）、驳回事项；传 queue 看某个队列明细。",
               {"queue": _desc(S, "队列键（取自返回的 queues），可选")}, write=False,
               uses=("oa_dashboard_get", "oa_list_dashboard_personal_queue_get"))
async def _dashboard(run: Run, args: dict) -> dict:
    summary = await run.read("oa_dashboard_get", {}, "控制台汇总")
    detail = None
    if args.get("queue"):
        detail = await run.read("oa_list_dashboard_personal_queue_get", {"path": {"queue_key": args["queue"]}}, "队列明细")
    return {"dashboard": summary, "queue_detail": detail}


# ---------- 06 财务中心 ----------

@business_tool("biz_my_payment_requests", "我的请款单",
               "查请款是否申请成功、审批到哪一步：律所费用、平台费用、内部结算分别查。",
               {"finance_scope": FINANCE_SCOPE, "case_no": _desc(S, "案号"), "customer": _desc(S, "客户"), "keyword": _desc(S, "关键字"),
                "statuses": _desc(NAMES, "状态筛选"), "page": {"type": "integer", "minimum": 1, "default": 1}},
               write=False, uses=("oa_query_payment_applications_get",))
async def _my_payments(run: Run, args: dict) -> dict:
    query = _drop_empty({"scope": "mine", "finance_scope": args.get("finance_scope", "firm"),
                         "case_no": args.get("case_no"), "customer": args.get("customer"), "keyword": args.get("keyword"),
                         "statuses": ",".join(args.get("statuses") or []), "page": args.get("page", 1), "page_size": 50})
    return {"payment_requests": await run.read("oa_query_payment_applications_get", {"query": query}, "我的请款单")}


@business_tool("biz_incoming_payment_find", "查询到账（回款管理）",
               "按付款单位、关键字、状态查银行到账，含待领取、待分配。",
               {"finance_scope": FINANCE_SCOPE, "keyword": _desc(S, "付款单位/流水号/客户"), "payment_status": _desc(S, "状态，如 待领取、待分配"),
                "bank_source": _desc(S, "银行"), "page": {"type": "integer", "minimum": 1, "default": 1}},
               write=False, uses=("oa_list_incoming_payments_get",))
async def _incoming_find(run: Run, args: dict) -> dict:
    query = _drop_empty({"finance_scope": args.get("finance_scope", "firm"), "keyword": args.get("keyword"), "payment_status": args.get("payment_status"),
                         "bank_source": args.get("bank_source"), "page": args.get("page", 1), "page_size": 50})
    return {"incoming_payments": await run.read("oa_list_incoming_payments_get", {"query": query}, "查询到账")}


@business_tool("biz_incoming_payment_claim_allocate", "回款领取并分配",
               "把确定是自己客户的到账认领到客户名下，再分配到具体案件费用。认领和分配要明确无误，领错会导致结算错误。"
               "不传 allocations 时只认领（如需），并返回可分配的案件费用候选。",
               {"payment_id": _desc(INT, "到账 ID（见 biz_incoming_payment_find）"), "finance_scope": FINANCE_SCOPE,
                "customer": _desc(S, "认领到的客户名称（已自动匹配客户的到账可不传）"), "comment": _desc(S, "领取/分配说明"),
                "allocations": {"type": "array", "maxItems": 100, "description": "分配明细：案件费用 ID 与金额",
                                "items": {"type": "object", "additionalProperties": False, "required": ["fee_record_id", "amount"],
                                          "properties": {"fee_record_id": INT, "amount": MONEY, "case_no": S, "is_refund": {"type": "boolean"}}}}},
               ("payment_id",), write=True,
               uses=("oa_get_incoming_payment_get", "oa_claim_incoming_payment_post", "oa_incoming_payment_allocation_candidates_get", "oa_allocate_incoming_payment_post"))
async def _claim_allocate(run: Run, args: dict) -> dict:
    scope = {"finance_scope": args.get("finance_scope", "firm")}
    payment = await run.read("oa_get_incoming_payment_get", {"path": {"payment_id": args["payment_id"]}, "query": scope}, "读取到账")
    if args.get("customer"):
        await run.write("oa_claim_incoming_payment_post", {"path": {"payment_id": args["payment_id"]}, "query": scope,
                                                           "body": _drop_empty({"customer": args["customer"], "comment": args.get("comment")})}, "认领到客户")
    candidates = None
    if not args.get("allocations") or not run.confirm:
        candidates = await run.read("oa_incoming_payment_allocation_candidates_get", {"path": {"payment_id": args["payment_id"]},
                                                                                      "query": {"case_fees_only": True}}, "可分配的案件费用")
    if args.get("allocations"):
        await run.write("oa_allocate_incoming_payment_post", {"path": {"payment_id": args["payment_id"]}, "query": scope, "body": _drop_empty({
            "allocations": args["allocations"], "case_fees_only": True, "comment": args.get("comment")})}, "分配到案件费用")
    return {"payment": payment, "allocation_candidates": candidates}


@business_tool("biz_incoming_payment_register", "新增回款（个人登记）",
               "个人手工新增一笔到账（银行到账一般由财务按银行表格导入）。",
               {"finance_scope": FINANCE_SCOPE, "received_date": _desc(DATE, "到账日期"), "amount": MONEY, "payer_name": _desc(S, "付款单位/账户名"),
                "bank_reference": _desc(S, "银行流水号"), "bank_source": _desc(S, "到账银行"), "customer": _desc(S, "客户名称"),
                "contract_no": _desc(S, "合同编号"), "case_no": _desc(S, "案号"), "remark": _desc(S, "银行摘要/备注"),
                "claim": {"type": "boolean", "description": "同时认领到客户"}},
               ("received_date", "amount", "payer_name"), write=True, uses=("oa_create_incoming_payment_post",))
async def _incoming_register(run: Run, args: dict) -> dict:
    body = _drop_empty({key: value for key, value in args.items() if key != "finance_scope"})
    created = await run.write("oa_create_incoming_payment_post", {"query": {"finance_scope": args.get("finance_scope", "firm")}, "body": body}, "登记回款")
    return {"incoming_payment": _created_ref(created)}


@business_tool("biz_settlement_apply", "申请结算（结算管理-待结算）",
               "文书查自己的待结算到账并申请结算；只有文书申请结算，案件才进入财务待处理。一笔到账涉及多个案件时不能单独结算。不传 receipt_ids 只列候选。",
               {"finance_scope": FINANCE_SCOPE, "case_no": _desc(S, "案号"), "customer": _desc(S, "客户"),
                "receipt_ids": {"type": "array", "items": INT, "maxItems": 200, "description": "要申请结算的到账 ID"}, "comment": _desc(S, "说明")},
               write=True, uses=("oa_list_general_settlement_candidates_get", "oa_apply_general_settlements_post"))
async def _settlement(run: Run, args: dict) -> dict:
    scope = args.get("finance_scope", "firm")
    candidates = await run.read("oa_list_general_settlement_candidates_get", {"query": _drop_empty({
        "finance_scope": scope, "case_no": args.get("case_no"), "customer": args.get("customer"), "page_size": 100})}, "待结算到账")
    if args.get("receipt_ids"):
        await run.write("oa_apply_general_settlements_post", {"query": {"finance_scope": scope},
                                                              "body": _drop_empty({"receipt_ids": args["receipt_ids"], "comment": args.get("comment")})}, "申请结算")
    else:
        run.notes.append("未传 receipt_ids：只列出待结算候选，未申请。")
    return {"candidates": candidates}


@business_tool("biz_case_archive_apply", "申请归档审核",
               "案件结案且到账确认完毕、内部提成已建、结案文书/法院收据/律师费发票齐全后，提交归档审核（正常归档/亏损归档）。先返回归档准备检查结果。",
               {**CASE_REF, "archive_type": {"type": "string", "enum": ["正常归档", "亏损归档"]}, "case_closed": {"type": "boolean", "description": "已结案"},
                "fees_settled": {"type": "boolean", "description": "费用已结清/到账确认"}, "documents_complete": {"type": "boolean", "description": "文档齐全"},
                "finance_complete": {"type": "boolean", "description": "财务对账完成"}, "paper_volume_count": {"type": "integer", "minimum": 0, "description": "纸质卷数"},
                "paper_archive_location": _desc(S, "纸质档案存放位置"), "comment": _desc(S, "说明")},
               ("archive_type",), write=True,
               uses=("oa_search_ordinary_cases_post", "oa_get_record_get", "oa_archive_readiness_get", "oa_archive_case_post"))
async def _archive(run: Run, args: dict) -> dict:
    case = await find_case(run, args)
    readiness = await run.read("oa_archive_readiness_get", {"path": {"case_id": case["id"]}}, "归档准备检查")
    body = _drop_empty({key: args.get(key) for key in ("archive_type", "paper_volume_count", "paper_archive_location", "comment")})
    body.update({key: bool(args.get(key)) for key in ("case_closed", "fees_settled", "documents_complete", "finance_complete")}, submit=True)
    await run.write("oa_archive_case_post", {"path": {"case_id": case["id"]}, "body": body}, "提交归档审核")
    return {"case": _brief(case), "readiness": readiness}

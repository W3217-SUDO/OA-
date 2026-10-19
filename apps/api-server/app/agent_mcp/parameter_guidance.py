"""补充工具参数说明，不改变原 OpenAPI 的结构或校验约束。"""

from copy import deepcopy
import json


SEMANTIC_GUIDANCE_MARKER = "\n[OA_PARAMETER_GUIDANCE]\n"
STRUCTURAL_GUIDANCE_MARKER = "\n[OA_PARAMETER_CONSTRAINTS]\n"


_CASE_SEARCH_ENDPOINTS = {
    "search_counsel_cases", "search_ordinary_cases", "export_counsel_cases",
    "export_current_ordinary_cases_excel", "case_statistics",
}
_GROUPS = {
    "path": "URL 路径参数，按路由占位符填写",
    "query": "URL 查询参数，按属性名填写筛选或控制值",
    "body": "请求体，按原请求模型填写 JSON 值",
    "files": "上传文件引用，填写当前用户可访问的已有 FileAttachment ID，不填路径、URL 或文件内容",
}
_CONSTRAINT_LABELS = {
    "type": "JSON 类型", "format": "格式", "enum": "合法枚举值", "const": "固定值",
    "minimum": "最小值（含）", "maximum": "最大值（含）",
    "exclusiveMinimum": "必须大于", "exclusiveMaximum": "必须小于",
    "multipleOf": "数值必须为其倍数", "minLength": "最少字符数", "maxLength": "最多字符数",
    "pattern": "必须匹配的正则", "minItems": "最少元素数", "maxItems": "最多元素数",
    "uniqueItems": "元素是否唯一", "minProperties": "最少属性数", "maxProperties": "最多属性数",
    "nullable": "是否允许 null",
}


def _literal(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _resolve(schema: dict, root: dict, document: dict) -> dict:
    """只读取本地引用用于说明，保留调用方的原始引用。"""
    current = schema
    seen = set()
    while "$ref" in current:
        reference = current["$ref"]
        if reference in seen:
            break
        seen.add(reference)
        if not reference.startswith("#/"):
            raise ValueError(f"参数说明不支持外部模式引用：{reference}")
        target = root if reference.startswith(("#/$defs/", "#/definitions/")) else document
        for part in reference[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        current = {**target, **{key: value for key, value in current.items() if key != "$ref"}}
    return current


def _constraints(schema: dict) -> str:
    parts = [f"{label}：{_literal(schema[key])}" for key, label in _CONSTRAINT_LABELS.items() if key in schema]
    if "default" in schema:
        parts.append(f"默认值：{_literal(schema['default'])}")
    else:
        parts.append("无模式默认值")
    if "enum" not in schema and "const" not in schema:
        parts.append("枚举未声明")
    return "；".join(parts)


def _business_guidance(route, method: str, path: tuple[str, ...], model: str) -> str:
    name = next((part for part in reversed(path) if part != "[]"), "")
    endpoint = route.endpoint.__name__
    route_path = route.path
    case_search = endpoint in _CASE_SEARCH_ENDPOINTS or model == "CounselCaseSearchInput"
    if case_search and name in {"source_from", "source_to"}:
        bound = "开始下界（含）" if name == "source_from" else "结束上界（含）"
        return (f"案件案源日期{bound}，筛选案件 data.source_date/source_at，不是线索日期或案件创建时间。"
                "来源：已有案件的案源日期或用户指定的案源日期范围；两端填写时开始不能晚于结束。"
                "证据：core/cases.py 的案件筛选 date_condition(value(data, 'source_date', 'source_at'), ...)；api_schemas/cases.py:CounselCaseSearchInput。")
    if endpoint in {"report_analytics", "export_report_analytics"} and name in {"source_from", "source_to"}:
        return ("报表案源日期筛选参数；当前实现实际按案件 created_at.date() 筛选（含边界），不是线索日期，"
                "也不是案件查询的 source_date/source_at。来源：用户要求的案件创建日期范围。证据：core/system.py:_report_analytics。")
    if case_search and name == "handling_lawyer":
        return ("经办律师姓名筛选，对案件 data.handling_lawyers 的中文姓名串做包含匹配；不是账号筛选。"
                "先查询 /people/options，使用返回的 value/label，或从可见案件经办律师姓名取值。"
                "证据：core/cases.py 的 contains('、'.join(data.get('handling_lawyers') or []), body.handling_lawyer)。")
    if case_search and name == "hearing_lawyer":
        return ("开庭律师筛选，按案件 hearing_lawyer/hearing_lawyers/court_lawyer 原字段做包含匹配；"
                "历史 hearing_lawyer 存在账号值，不能假定全部是中文姓名。先读取目标可见案件原字段，"
                "需要人员映射时查询 /people/options 的 username 与 value/label，使用实际存储值。证据：core/cases.py 案件筛选。")
    if name == "fee_type_id" and "/finance/" in route_path:
        return ("系统费用类型主数据 ID，不是费用名称、代码或案件费用记录 ID。先查询 /system/parameters/options?category=fee_type，"
                "选择启用、selectable 的末级项 id，并核对 expense_scopes 与本次费用归属；不得猜测 ID。"
                "证据：areas/system/router.py:list_system_parameter_options；core/finance.py:_resolve_case_fee_type_master。")
    customer_context = "/customers" in route_path or model.startswith("Customer")
    if name == "customer_type" and customer_context:
        return ("客户类型名称，不填主键或 code。先查询 /customers/reference-options，使用 customer_types[].value；"
                "合法值来自启用的 SystemParameter(category='customer_type').name，不凭固定示例猜测。"
                "证据：areas/crm/router.py:customer_reference_options、list_customers 及客户保存校验。")
    if name == "organization_type" and customer_context:
        return ("客户组织类型；先读取目标客户 data.organization_type（已有客户），新增时按用户真实主体身份选择。"
                "它不来自 customer_type 主数据，当前无组织类型查询接口；源码 CUSTOMER_ORGANIZATION_TYPES 明确允许："
                "公司企业、事业单位、机关团体、个人、个体工商户、其他。个人关联 identity_no，其余关联 credit_code。"
                "证据：core/customer_identity.py:validate_customer_identity；不将这些文字追加为 schema enum。")
    if name in _GROUPS and len(path) == 1:
        return _GROUPS[name]
    if path and path[0] == "files":
        return "来源：先通过原附件上传或查询接口取得当前用户可访问的 FileAttachment ID；不填写本机路径、URL、Base64 或文件正文。"
    if path and path[0] == "path":
        return (f"定位路由 {route_path} 中的 {{{name}}} 目标；先调用该业务的可见列表/详情查询，"
                f"读取对应 {name}，不要把同名的其他业务 ID、编号或显示名称混用。具体对象关联以原接口说明为准。")
    return ""


def enrich_parameter_schema(route, method: str, schema: dict, document: dict) -> dict:
    """返回仅增强 description 的独立副本；文档、路由和原 schema 均只读。"""
    result = deepcopy(schema)
    operation = document.get("paths", {}).get(route.path, {}).get(method.lower(), {})
    parameters = {}
    path_item = document.get("paths", {}).get(route.path, {})
    for parameter in [*path_item.get("parameters", []), *operation.get("parameters", [])]:
        parameter = _resolve(parameter, result, document)
        parameters[(parameter.get("in"), parameter.get("name"))] = parameter

    def visit(node: dict, path: tuple[str, ...], required: bool | None, model: str = "", branch: bool = False) -> None:
        effective = _resolve(node, schema, document)
        reference = node.get("$ref")
        current_model = reference.rsplit("/", 1)[-1] if reference else model
        name = ".".join(path) or "工具参数"
        original = node.get("description") or effective.get("description")
        parameter = parameters.get(tuple(path)) if len(path) == 2 else None
        if parameter and parameter.get("description") and not original:
            original = parameter["description"]
        title = effective.get("title")
        parts = []
        guidance = "" if branch else _business_guidance(route, method, path, current_model)
        if guidance:
            parts.append(guidance)
        elif not original and not branch:
            parts.append("业务用途/来源尚未核实，不猜值。")
        if effective.get("format") == "date":
            parts.append("日期填写 YYYY-MM-DD。")
        elif effective.get("format") == "date-time":
            parts.append("填写 date-time 日期时间。")
        if effective.get("type") == "boolean":
            parts.append("填写 JSON true/false。")
        structural = [f"参数位置：{name}"]
        if title:
            structural.append(f"原模式标题：{title}")
        if branch:
            structural.append("类型分支，必填性见父级 required")
        elif required is not None:
            structural.append("父对象提供时必填" if required else "可省略，不等于可传 null")
        structural.append(_constraints(effective))
        node["description"] = (original or "") + SEMANTIC_GUIDANCE_MARKER + "\n".join(parts) + STRUCTURAL_GUIDANCE_MARKER + "；".join(structural)

        for key, child in node.get("properties", {}).items():
            if isinstance(child, dict):
                visit(child, (*path, key), key in node.get("required", []), current_model)
        for keyword in ("$defs", "definitions"):
            for key, child in node.get(keyword, {}).items():
                if isinstance(child, dict):
                    visit(child, (keyword, key), None, key)
        for keyword in ("anyOf", "oneOf", "allOf", "prefixItems"):
            for child in node.get(keyword, []):
                if isinstance(child, dict):
                    visit(child, path, None, current_model, branch=True)
        items = node.get("items")
        if isinstance(items, dict):
            visit(items, (*path, "[]"), None, current_model)
        elif isinstance(items, list):
            for child in items:
                if isinstance(child, dict):
                    visit(child, (*path, "[]"), None, current_model)
        for keyword in ("additionalProperties", "patternProperties", "dependentSchemas"):
            children = node.get(keyword)
            if keyword == "additionalProperties" and isinstance(children, dict):
                visit(children, (*path, "*"), None, current_model)
            elif isinstance(children, dict):
                for key, child in children.items():
                    if isinstance(child, dict):
                        visit(child, (*path, key), None, current_model)
        for keyword in ("not", "if", "then", "else", "contains", "propertyNames"):
            if isinstance(node.get(keyword), dict):
                visit(node[keyword], path, None, current_model, branch=True)

    visit(result, (), None)
    return result

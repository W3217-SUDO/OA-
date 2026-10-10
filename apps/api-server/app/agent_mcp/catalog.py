"""从实际挂载的 FastAPI 业务操作生成 MCP 目录及原模型参数校验。"""

from collections import Counter
from copy import copy, deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import inspect
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.dependencies.utils import (
    get_flat_dependant, get_flat_params,
    is_uploadfile_or_nonable_uploadfile_annotation, is_uploadfile_sequence_annotation,
)
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.agent_mcp.semantic_metadata import (
    READ_ONLY_POSTS, RESPONSE_MEDIA_TYPES, SIDE_EFFECT_GETS, describe, disabled_credential_fields, domain_for, exclusion_reasons,
    is_write, operation_key, title_for,
)


def _invalid(loc: tuple, message: str, kind: str = "value_error") -> None:
    raise HTTPException(422, detail=[{"loc": list(loc), "msg": message, "type": kind}])


def _reference(schema: dict, document: dict) -> dict:
    if "$ref" not in schema:
        return schema
    reference = schema["$ref"]
    if not reference.startswith("#/"):
        raise ValueError(f"MCP 参数模式不能引用外部文档：{reference}")
    target: Any = document
    for part in reference[2:].split("/"):
        target = target[part.replace("~1", "/").replace("~0", "~")]
    return {**target, **{key: value for key, value in schema.items() if key != "$ref"}}


def _local_schema(schema: dict, document: dict) -> dict:
    definitions = {}

    def convert(value):
        if isinstance(value, list):
            return [convert(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: convert(item) for key, item in value.items() if key != "$ref"}
        if "$ref" in value:
            reference = value["$ref"]
            # 仅携带本工具可达的定义，递归模型仍使用本地引用，避免截断原模型。
            name = reference.rsplit("/", 1)[-1]
            if name not in definitions:
                definitions[name] = {}
                definitions[name] = convert(_reference({"$ref": reference}, document))
            result["$ref"] = f"#/$defs/{name}"
        return result

    result = convert(schema)
    if definitions:
        result["$defs"] = definitions
    return result


def _restrict_credentials(schema: dict, document: dict, restrictions: list, loc: tuple = (), active: tuple = ()) -> dict:
    reference = schema.get("$ref")
    if reference in active:
        return deepcopy(schema)
    schema = deepcopy(_reference(schema, document))
    active = (*active, reference) if reference else active
    disabled = disabled_credential_fields(schema)
    for name in disabled:
        if name in schema.get("required", []):
            raise ValueError(f"原接口必填凭据不能成为模型参数：{'.'.join((*loc, name))}")
        del schema["properties"][name]
        restrictions.append({"field": ".".join((*loc, name)), "reason": "凭据参数不向模型开放，只能在原人工安全入口填写"})
    if disabled:
        schema["additionalProperties"] = False
    if "properties" in schema:
        schema["properties"] = {name: _restrict_credentials(item, document, restrictions, (*loc, name), active)
                                for name, item in schema["properties"].items()}
    for keyword in ("anyOf", "oneOf", "allOf"):
        if keyword in schema:
            schema[keyword] = [_restrict_credentials(item, document, restrictions, loc, active) for item in schema[keyword]]
    if isinstance(schema.get("items"), dict):
        schema["items"] = _restrict_credentials(schema["items"], document, restrictions, (*loc, "[]"), active)
    return schema


def _strict_objects(value, schema: dict, document: dict, loc: tuple) -> None:
    schema = _reference(schema, document)
    if "const" in schema and value != schema["const"]:
        _invalid(loc, "参数值不在此工具开放范围内")
    if "enum" in schema and value not in schema["enum"]:
        _invalid(loc, "参数值不在原接口或此工具开放的枚举范围内")
    if "allOf" in schema:
        for branch in schema["allOf"]:
            _strict_objects(value, branch, document, loc)
    branches = schema.get("anyOf", schema.get("oneOf", []))
    if branches:
        applicable = [_reference(branch, document) for branch in branches]
        applicable = [branch for branch in applicable if
                      isinstance(value, dict) and branch.get("type") == "object" or
                      isinstance(value, list) and branch.get("type") == "array"]
        if len(applicable) == 1:
            _strict_objects(value, applicable[0], document, loc)
        elif isinstance(value, dict) and applicable:
            merged = {key: item for branch in applicable for key, item in branch.get("properties", {}).items()}
            _strict_objects(value, {"type": "object", "properties": merged}, document, loc)
        return
    if isinstance(value, dict) and schema.get("type") == "object":
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", False if properties else True)
        for name in schema.get("required", []):
            if name not in value:
                _invalid((*loc, name), "缺少必填参数", "missing")
        for key, item in value.items():
            if key in properties:
                _strict_objects(item, properties[key], document, (*loc, key))
            elif additional is False:
                _invalid((*loc, key), "不允许未声明的参数", "extra_forbidden")
            elif isinstance(additional, dict):
                _strict_objects(item, additional, document, (*loc, key))
    elif isinstance(value, list) and schema.get("type") == "array":
        for index, item in enumerate(value):
            _strict_objects(item, schema.get("items", {}), document, (*loc, index))


def _field_value(model_field, value, loc: tuple):
    normalized, errors = model_field.validate(value, {}, loc=loc)
    if errors:
        # 不回传参数值，避免错误消息把敏感输入写入模型会话。
        details = [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in errors]
        raise HTTPException(422, detail=details)
    return jsonable_encoder(normalized, by_alias=True, exclude_unset=True)


def _object_schema() -> dict:
    return {"type": "object", "properties": {}, "additionalProperties": False}


def _binary_field(schema: dict, document: dict, model_field=None) -> bool | None:
    if model_field is not None:
        annotation = model_field.field_info.annotation
        if is_uploadfile_sequence_annotation(annotation):
            return True
        if is_uploadfile_or_nonable_uploadfile_annotation(annotation):
            return False
    schema = _reference(schema, document)
    # 新版 Pydantic 使用 contentMediaType，真实 UploadFile 类型优先于模式表现形式。
    if schema.get("format") == "binary" or schema.get("contentMediaType") == "application/octet-stream":
        return False
    if schema.get("type") == "array" and _binary_field(schema.get("items", {}), document) is not None:
        return True
    for branch in schema.get("anyOf", []):
        result = _binary_field(branch, document)
        if result is not None:
            return result
    return None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    title: str
    description: str
    input_schema: dict
    method: str
    path: str
    is_write: bool
    request_media_type: str | None
    domain: str
    file_fields: dict[str, bool]
    response_media_types: tuple[str, ...]
    is_binary_response: bool
    _route: APIRoute = field(repr=False, compare=False)

    def to_mcp(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": deepcopy(self.input_schema),
            "annotations": {
                "readOnlyHint": not self.is_write,
                "destructiveHint": self.is_write,
                "idempotentHint": not self.is_write,
                "openWorldHint": False,
            },
        }

    def validate_arguments(self, arguments: dict) -> dict:
        if not isinstance(arguments, dict):
            _invalid((), "工具参数必须是 JSON 对象", "dict_type")
        _strict_objects(arguments, self.input_schema, self.input_schema, ())
        result: dict[str, Any] = {"path": {}, "query": {}, "body": None, "files": {}}
        params = get_flat_params(self._route.dependant)
        for group in ("path", "query", "files"):
            values = arguments.get(group, {})
            if not isinstance(values, dict):
                _invalid((group,), "参数分组必须是 JSON 对象", "dict_type")
            schema = self.input_schema["properties"][group]
            for required in schema.get("required", []):
                if required not in values:
                    _invalid((group, required), "缺少必填参数", "missing")
            if group == "files":
                for key, value in values.items():
                    items = value if self.file_fields[key] else [value]
                    if not isinstance(items, list) or not items:
                        _invalid((group, key), "上传参数必须是有效附件 ID 或非空附件 ID 数组")
                    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in items):
                        _invalid((group, key), "只允许正整数 FileAttachment ID，禁止路径、URL 或文件内容")
                    result[group][key] = list(items) if self.file_fields[key] else items[0]
                continue
            fields = {item.alias: item for item in params if item.field_info.in_.value == group}
            for key, value in values.items():
                result[group][key] = _field_value(fields[key], value, (group, key))
        body_field = self._route.body_field
        if body_field is None:
            if arguments.get("body") not in (None, {}):
                _invalid(("body",), "此接口不接收请求体")
            return result
        if "body" not in arguments:
            if "body" in self.input_schema.get("required", []):
                _invalid(("body",), "缺少必填请求体", "missing")
            return result
        body = arguments["body"]
        if self.request_media_type in {"multipart/form-data", "application/x-www-form-urlencoded"}:
            if not isinstance(body, dict):
                _invalid(("body",), "表单字段必须是 JSON 对象", "dict_type")
            body_schema = self.input_schema["properties"]["body"]
            for required in body_schema.get("required", []):
                if required not in body:
                    _invalid(("body", required), "缺少必填表单字段", "missing")
            fields = {item.alias: item for item in get_flat_dependant(self._route.dependant).body_params}
            result["body"] = {key: _field_value(fields[key], value, ("body", key)) for key, value in body.items()}
        else:
            result["body"] = _field_value(body_field, body, ("body",))
        return result


def _tool_input(route: APIRoute, operation: dict, document: dict) -> tuple[dict, str | None, dict[str, bool], list]:
    groups = {"path": _object_schema(), "query": _object_schema(), "body": {"type": "null"}, "files": _object_schema()}
    required_groups = []
    for parameter in operation.get("parameters", []):
        parameter = _reference(parameter, document)
        group = parameter["in"]
        if group not in {"path", "query"}:
            raise ValueError(f"{route.path} 存在无法由模型提供的 {group} 参数：{parameter['name']}")
        name = parameter["name"]
        groups[group]["properties"][name] = deepcopy(parameter["schema"])
        if parameter.get("description"):
            groups[group]["properties"][name]["description"] = parameter["description"]
        if parameter.get("required"):
            groups[group].setdefault("required", []).append(name)
            if group not in required_groups:
                required_groups.append(group)
    request = operation.get("requestBody")
    media_type = None
    files = {}
    if request:
        request = _reference(request, document)
        content = request["content"]
        declared = route.body_field.field_info.media_type
        media_type = declared if declared in content else next(iter(content))
        body_schema = deepcopy(_reference(content[media_type]["schema"], document))
        if media_type in {"multipart/form-data", "application/x-www-form-urlencoded"}:
            groups["body"] = _object_schema()
            body_required = set(body_schema.get("required", []))
            body_fields = {item.alias: item for item in get_flat_dependant(route.dependant).body_params}
            for name, schema in body_schema.get("properties", {}).items():
                array = _binary_field(schema, document, body_fields[name])
                group = "files" if array is not None else "body"
                if array is not None:
                    files[name] = array
                    attachment = {"type": "integer", "minimum": 1, "description": "当前用户可访问的已有 FileAttachment ID"}
                    groups[group]["properties"][name] = {"type": "array", "items": attachment, "minItems": 1} if array else attachment
                else:
                    groups[group]["properties"][name] = deepcopy(schema)
                if name in body_required:
                    groups[group].setdefault("required", []).append(name)
                    if group not in required_groups:
                        required_groups.append(group)
        else:
            groups["body"] = body_schema
            if request.get("required"):
                required_groups.append("body")
    result = {"type": "object", "properties": groups, "additionalProperties": False}
    if required_groups:
        result["required"] = required_groups
    restrictions = []
    result = _restrict_credentials(result, document, restrictions)
    if route.endpoint.__name__ == "create_hr_employee":
        body = result["properties"]["body"]
        body["properties"]["account_type"].update({"enum": ["外部合作账号"], "description": "仅开放不创建登录凭据的外部合作员工档案"})
        body["properties"]["account_type"].pop("default", None)
        body.setdefault("required", []).append("account_type")
        body["properties"]["username"].update({"const": "", "description": "外部合作员工档案不创建登录账号，必须留空"})
        restrictions.append({"field": "body.account_type", "reason": "仅开放外部合作账号无登录子业务；员工和客户登录凭据在原人工入口办理"})
    return _local_schema(result, document), media_type, files, restrictions


def _response_types(route: APIRoute, method: str, operation: dict) -> tuple[tuple[str, ...], bool]:
    media_types = {media for code, response in operation.get("responses", {}).items()
                   if str(code).startswith("2") for media in response.get("content", {})}
    if operation_key(route, method) in RESPONSE_MEDIA_TYPES:
        media_types = set(RESPONSE_MEDIA_TYPES[operation_key(route, method)])
    binary = any(not (media.startswith("application/json") or media.endswith("+json")) for media in media_types)
    annotation = inspect.signature(route.endpoint).return_annotation
    if annotation is not inspect.Signature.empty:
        binary |= any(name in str(annotation) for name in ("FileResponse", "StreamingResponse", "bytes"))
    binary |= bool(set(route.endpoint.__name__.split("_")).intersection({"download", "export"}))
    binary |= route.name in {"feedback_screenshot", "feedback_event_screenshot", "render_pdf_preview_page", "get_ipr_fee_bill_attachment"}
    return tuple(sorted(media_types)), binary


class ToolCatalog:
    def __init__(self, app: FastAPI):
        routes = [route for route in app.routes if isinstance(route, APIRoute)]
        self.tools: list[ToolDefinition] = []
        self._by_name: dict[str, ToolDefinition] = {}
        self._inventory = {
            "mounted_api_routes": len(routes),
            "http_method_operations": sum(len(route.methods) for route in routes),
            "methods": dict(sorted(Counter(method for route in routes for method in route.methods).items())),
            "excluded": [], "description_corrections": [], "credential_field_restrictions": [], "operations": [],
        }
        included = []
        for route in routes:
            reasons = exclusion_reasons(route)
            for method in sorted(route.methods):
                if reasons:
                    self._inventory["excluded"].append({"method": method, "path": route.path, "endpoint": route.name, "reasons": reasons})
                else:
                    included.append((route, method))
        # 隐藏的已挂载业务别名同样纳入，不修改应用路由或应用的 OpenAPI 缓存。
        schema_routes = [copy(route) for route in routes]
        for route in schema_routes:
            route.include_in_schema = True
        document = get_openapi(title=app.title, version=app.version, routes=schema_routes, separate_input_output_schemas=False)
        stems = Counter(_name_stem(route, method) for route, method in included)
        for route, method in included:
            stem = _name_stem(route, method)
            suffix = "_" + sha256(f"{method} {route.path}".encode("utf-8")).hexdigest()[:8] if stems[stem] > 1 else ""
            name = stem[:64 - len(suffix)] + suffix
            if name in self._by_name:
                raise ValueError(f"MCP 工具名称冲突：{method} {route.path}")
            operation = document["paths"][route.path_format][method.lower()]
            schema, media_type, files, restrictions = _tool_input(route, operation, document)
            write = is_write(route, method)
            description, corrupted = describe(route, method, write)
            response_types, binary = _response_types(route, method, operation)
            tool = ToolDefinition(name, title_for(route, method), description, schema, method, route.path, write, media_type,
                                  domain_for(route), files, response_types, binary, route)
            self.tools.append(tool)
            self._by_name[name] = tool
            self._inventory["operations"].append({"name": name, "title": tool.title, "method": method, "path": route.path, "endpoint": route.name,
                                                  "handler": route.endpoint.__name__,
                                                  "domain": tool.domain, "is_write": write, "request_media_type": media_type,
                                                  "file_fields": files, "is_binary_response": binary})
            if restrictions:
                self._inventory["credential_field_restrictions"].append({"method": method, "path": route.path,
                                                                         "endpoint": route.name, "fields": restrictions})
            if corrupted:
                self._inventory["description_corrections"].append({"method": method, "path": route.path, "endpoint": route.name,
                    "reason": "原说明包含编码损坏，不复制乱码；使用中文领域、动作、原接口名及路径生成说明"})
        self._inventory.update({
            "tool_count": len(self.tools), "excluded_count": len(self._inventory["excluded"]),
            "read_count": sum(not tool.is_write for tool in self.tools), "write_count": sum(tool.is_write for tool in self.tools),
            "domains": dict(sorted(Counter(tool.domain for tool in self.tools).items())),
            "included_methods": dict(sorted(Counter(tool.method for tool in self.tools).items())),
            "multipart_count": sum(tool.request_media_type == "multipart/form-data" for tool in self.tools),
            "binary_response_count": sum(tool.is_binary_response for tool in self.tools),
            "binary_read_count": sum(tool.is_binary_response and not tool.is_write for tool in self.tools),
            "binary_write_count": sum(tool.is_binary_response and tool.is_write for tool in self.tools),
            "read_only_posts": [{"name": tool.name, "path": tool.path, "reason": READ_ONLY_POSTS[operation_key(tool._route, tool.method)]}
                                for tool in self.tools if tool.method == "POST" and not tool.is_write],
            "side_effect_gets": [{"name": tool.name, "path": tool.path,
                                 "reason": SIDE_EFFECT_GETS.get(operation_key(tool._route, tool.method), "GET 实际处理函数具有业务写入语义，须人工确认")}
                                for tool in self.tools if tool.method == "GET" and tool.is_write],
        })

    def get(self, name: str) -> ToolDefinition:
        if not isinstance(name, str) or name not in self._by_name:
            raise HTTPException(422, detail="未知或未开放的 OA MCP 工具")
        return self._by_name[name]

    def search(self, query: str, limit: int = 8) -> list[ToolDefinition]:
        if not isinstance(query, str) or not query.strip():
            raise HTTPException(422, detail="请输入业务目标或接口关键词")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise HTTPException(422, detail="目录检索数量必须为 1 至 50")
        terms = re.findall(r"[a-z0-9_/-]+|[\u4e00-\u9fff]", query.lower())
        scored = []
        for tool in self.tools:
            text = tool.description.lower()
            subject = " ".join((tool.domain, tool._route.name, tool.path)).lower()
            score = sum(4 if term in subject else 1 if term in text else 0 for term in terms)
            if query.lower() in text:
                score += 8
            if score:
                scored.append((score, tool.name, tool))
        return [tool for _, _, tool in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]]

    def inventory(self) -> dict:
        return deepcopy(self._inventory)


def _name_stem(route: APIRoute, method: str) -> str:
    endpoint = re.sub(r"[^a-zA-Z0-9_]+", "_", route.name).strip("_").lower()
    return f"oa_{endpoint[:51]}_{method.lower()}"


def get_catalog(app: FastAPI) -> ToolCatalog:
    signature = tuple((id(route), tuple(sorted(route.methods))) for route in app.routes if isinstance(route, APIRoute))
    cached = getattr(app.state, "_agent_mcp_catalog", None)
    if cached is None or cached[0] != signature:
        catalog = ToolCatalog(app)
        app.state._agent_mcp_catalog = (signature, catalog)
        return catalog
    return cached[1]

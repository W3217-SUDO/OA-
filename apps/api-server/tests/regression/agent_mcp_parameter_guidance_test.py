"""参数语义、目录排序和确认门禁的隔离定向契约，不执行真实业务写入。"""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.agent_mcp import catalog as catalog_module, service
from app.agent_mcp.auth import AuthContext, _auth_context
from app.agent_mcp.operation_guidance import parameter_documentation
from app.agent_mcp.model_context import _discovery_tool, discovered_tools_view, encoded_size
from app.agent_mcp.parameter_guidance import (
    SEMANTIC_GUIDANCE_MARKER, STRUCTURAL_GUIDANCE_MARKER, enrich_parameter_schema,
)
from app.main import app


def without_descriptions(value):
    if isinstance(value, dict):
        return {key: without_descriptions(item) for key, item in value.items() if key != "description"}
    if isinstance(value, list):
        return [without_descriptions(item) for item in value]
    return value


def schema_fields(schema):
    for name, child in schema.get("properties", {}).items():
        if isinstance(child, dict):
            yield name, child
            yield from schema_fields(child)
    for keyword in ("$defs", "definitions", "patternProperties", "dependentSchemas"):
        for child in schema.get(keyword, {}).values():
            if isinstance(child, dict):
                yield from schema_fields(child)
    for keyword in ("anyOf", "oneOf", "allOf", "prefixItems"):
        for child in schema.get(keyword, []):
            if isinstance(child, dict):
                yield from schema_fields(child)
    for keyword in ("items", "additionalProperties", "not", "if", "then", "else", "contains", "propertyNames"):
        child = schema.get(keyword)
        if isinstance(child, dict):
            yield from schema_fields(child)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, dict):
                    yield from schema_fields(item)


def original_fingerprint(spec):
    """逐字保留说明增强前的摘要字段及序列化选项，独立核对兼容性。"""
    descriptor = {
        "name": spec.name, "method": spec.method, "path": spec.path,
        "input_schema": spec.input_schema, "is_write": spec.is_write,
        "request_media_type": spec.request_media_type, "file_fields": spec.file_fields,
        "response_media_types": spec.response_media_types, "is_binary_response": spec.is_binary_response,
        "handler": spec._route.endpoint.__module__ + "." + spec._route.endpoint.__qualname__,
    }
    encoded = json.dumps(descriptor, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ParameterGuidanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 只构建挂载路由的描述，不启动应用生命周期或连接业务数据库。
        cls.catalog = catalog_module.ToolCatalog(app)

    def route(self, endpoint="search_ordinary_cases", path="/api/v1/cases/search"):
        return SimpleNamespace(path=path, endpoint=SimpleNamespace(__name__=endpoint))

    def enrich(self, properties, *, endpoint="search_ordinary_cases", path="/api/v1/cases/search"):
        schema = {"type": "object", "properties": {"body": {"type": "object", "properties": properties}}}
        return enrich_parameter_schema(self.route(endpoint, path), "POST", schema, {})["properties"]["body"]["properties"]

    def test_deep_copy_preserves_all_constraints_and_inputs(self):
        schema = {
            "type": "object", "required": ["body"], "additionalProperties": False,
            "properties": {"body": {
                "type": "object", "required": ["name"], "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "title": "业务名称", "description": "原始业务说明",
                             "default": "", "enum": ["", "甲"], "minLength": 0, "maxLength": 20, "pattern": "^.*$"},
                    "amount": {"type": "number", "exclusiveMinimum": 0, "maximum": 100, "multipleOf": 0.01},
                    "data": {"type": "object", "default": {"description": "这是业务数据，不是模式说明"}},
                },
            }},
        }
        document = {"paths": {}}
        before, document_before = deepcopy(schema), deepcopy(document)
        result = enrich_parameter_schema(self.route(), "POST", schema, document)
        self.assertEqual(schema, before)
        self.assertEqual(document, document_before)
        self.assertEqual(without_descriptions(result), without_descriptions(before))
        body = result["properties"]["body"]
        self.assertIsNot(body, schema["properties"]["body"])
        description = body["properties"]["name"]["description"]
        for term in ("原始业务说明", "业务名称", "必填", "默认值", "合法枚举值"):
            self.assertIn(term, description)
        self.assertEqual(body["properties"]["data"]["default"], before["properties"]["body"]["properties"]["data"]["default"])

    def test_nested_arrays_unions_and_recursive_refs_keep_original_shapes(self):
        schema = {"type": "object", "properties": {"body": {"$ref": "#/$defs/Node"}}, "$defs": {
            "Node": {"title": "层级记录", "type": "object", "required": ["id"], "properties": {
                "id": {"type": "integer", "minimum": 1},
                "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
                "choice": {"anyOf": [{"type": "string", "enum": ["是"]}, {"type": "null"}], "default": None},
                "labels": {"type": "object", "additionalProperties": {"type": "string"}},
            }},
        }}
        before = deepcopy(schema)
        result = enrich_parameter_schema(self.route(), "POST", schema, {})
        self.assertEqual(schema, before)
        self.assertEqual(without_descriptions(result), without_descriptions(before))
        node = result["$defs"]["Node"]
        self.assertIn("层级记录", node["description"])
        self.assertIn("Node", node["properties"]["id"]["description"])
        self.assertIn("children.[]", node["properties"]["children"]["items"]["description"])
        self.assertIn("类型分支", node["properties"]["choice"]["anyOf"][1]["description"])
        self.assertIn("labels.*", node["properties"]["labels"]["additionalProperties"]["description"])

    def test_openapi_parameter_description_has_priority(self):
        route = self.route("get_example", "/api/v1/example")
        schema = {"properties": {"query": {"properties": {"name": {"type": "string", "title": "原名称"}}}}}
        document = {"paths": {route.path: {"get": {"parameters": [{
            "in": "query", "name": "name", "description": "真实接口名称筛选说明", "schema": {"type": "string"},
        }]}}}}
        result = enrich_parameter_schema(route, "GET", schema, document)
        description = result["properties"]["query"]["properties"]["name"]["description"]
        self.assertTrue(description.startswith("真实接口名称筛选说明"))
        self.assertIn("原名称", description)

    def test_same_named_ids_and_names_keep_route_and_parent_context(self):
        fields = {"customer": {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}},
                  "contract": {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}}
        result = self.enrich(fields)
        self.assertIn("body.customer.id", result["customer"]["properties"]["id"]["description"])
        self.assertIn("body.contract.name", result["contract"]["properties"]["name"]["description"])
        self.assertIn("尚未核实", result["customer"]["properties"]["id"]["description"])

    def test_case_dates_and_lawyer_values_follow_actual_storage(self):
        result = self.enrich({name: {"type": "string"} for name in ("source_from", "source_to", "handling_lawyer", "hearing_lawyer")})
        for name in ("source_from", "source_to"):
            self.assertIn("source_date/source_at", result[name]["description"])
            self.assertIn("不是线索日期", result[name]["description"])
        self.assertIn("中文姓名", result["handling_lawyer"]["description"])
        self.assertIn("不是账号筛选", result["handling_lawyer"]["description"])
        self.assertIn("账号值", result["hearing_lawyer"]["description"])
        self.assertIn("username", result["hearing_lawyer"]["description"])

    def test_report_dates_are_not_relabelled_as_case_source_dates(self):
        result = self.enrich({"source_from": {"format": "date"}}, endpoint="report_analytics", path="/api/v1/reports/analytics/{view}")
        self.assertIn("created_at.date()", result["source_from"]["description"])
        self.assertIn("YYYY-MM-DD", result["source_from"]["description"])
        unknown = self.enrich({"source_from": {"type": "string"}}, endpoint="unknown", path="/api/v1/investigations/example")
        self.assertIn("尚未核实", unknown["source_from"]["description"])
        self.assertNotIn("案件案源日期", unknown["source_from"]["description"])

    def test_master_data_guidance_does_not_invent_schema_enum(self):
        fee = self.enrich({"fee_type_id": {"type": "integer"}}, endpoint="create_finance_fee", path="/api/v1/finance/fees")["fee_type_id"]
        self.assertIn("category=fee_type", fee["description"])
        self.assertIn("末级", fee["description"])
        customer = self.enrich({"customer_type": {"type": "string"}, "organization_type": {"type": "string"}},
                               endpoint="create_customer", path="/api/v1/customers")
        self.assertIn("/customers/reference-options", customer["customer_type"]["description"])
        self.assertIn("CUSTOMER_ORGANIZATION_TYPES", customer["organization_type"]["description"])
        self.assertIn("无组织类型查询接口", customer["organization_type"]["description"])
        for field in (fee, *customer.values()):
            self.assertNotIn("enum", field)

    def test_user_fields_are_not_globally_assumed_to_be_accounts(self):
        result = self.enrich({"user": {"type": "string"}, "requested_by": {"type": "string"}})
        for field in result.values():
            self.assertIn("尚未核实", field["description"])
            self.assertNotIn("填写登录账号", field["description"])

    def test_every_mounted_tool_preserves_schema_and_describes_all_properties(self):
        with patch.object(catalog_module, "enrich_parameter_schema", side_effect=lambda route, method, schema, document: schema):
            baseline = catalog_module.ToolCatalog(app)
        old = {tool.name: tool for tool in baseline.tools}
        self.assertEqual(set(old), {tool.name for tool in self.catalog.tools})
        fields = missing = 0
        for tool in self.catalog.tools:
            with self.subTest(tool=tool.name):
                self.assertEqual(without_descriptions(old[tool.name].input_schema), without_descriptions(tool.input_schema))
                for name, field in schema_fields(tool.input_schema):
                    fields += 1
                    description = field.get("description", "")
                    self.assertTrue(description, f"{tool.name}: {name}")
                    self.assertNotIn("\ufffd", description)
                    missing += "业务用途/来源尚未核实" in description
        print(f"参数说明覆盖：{len(old)} 个工具，{fields} 个属性出现位置；其中 {missing} 个位置明确缺失专属业务说明。")

    def test_all_825_pending_request_fingerprints_keep_pre_enrichment_bytes(self):
        with patch.object(catalog_module, "enrich_parameter_schema", side_effect=lambda route, method, schema, document: schema):
            baseline = catalog_module.ToolCatalog(app)
        originals = {tool.name: tool for tool in baseline.tools}
        self.assertEqual(len(originals), 825)
        mismatches = []
        for tool in self.catalog.tools:
            original = originals[tool.name]
            with self.subTest(tool=tool.name):
                for key in ("name", "method", "path", "is_write", "request_media_type", "file_fields",
                            "response_media_types", "is_binary_response"):
                    self.assertEqual(getattr(original, key), getattr(tool, key))
                self.assertIs(original._route.endpoint, tool._route.endpoint)
                self.assertEqual(original.input_schema, tool.original_input_schema)
                self.assertEqual(service.descriptor_fingerprint(original), original_fingerprint(original))
                if original_fingerprint(original) != service.descriptor_fingerprint(tool):
                    mismatches.append(tool.name)
        print(f"Pre-enrichment fingerprint compatibility: {len(originals) - len(mismatches)}/825")
        self.assertEqual(mismatches, [])

    def test_fingerprint_keeps_original_descriptions_and_real_contract_changes(self):
        tool = self.catalog.get("oa_create_finance_fee_post")
        changed_description = deepcopy(tool.input_schema)
        changed_description["description"] = "只修改模型说明"
        self.assertEqual(service.descriptor_fingerprint(tool),
                         service.descriptor_fingerprint(replace(tool, input_schema=changed_description)))
        raw = replace(tool, input_schema=tool.original_input_schema, original_input_schema=None)
        self.assertEqual(service.descriptor_fingerprint(tool), original_fingerprint(raw))
        for key, value in (("description", "原说明确实发生变更"), ("additionalProperties", True),
                           ("required", ["body", "files"])):
            schema = deepcopy(tool.original_input_schema)
            schema[key] = value
            changed = replace(tool, input_schema=schema, original_input_schema=schema)
            with self.subTest(key=key):
                self.assertNotEqual(service.descriptor_fingerprint(tool), service.descriptor_fingerprint(changed))
        for key, value in (("method", "DELETE"), ("path", "/CODEX-changed"), ("is_write", False),
                           ("file_fields", {"CODEX-file": True}), ("is_binary_response", True),
                           ("response_media_types", ("application/CODEX-changed",)), ("request_media_type", "text/CODEX")):
            with self.subTest(key=key):
                self.assertNotEqual(service.descriptor_fingerprint(tool),
                                    service.descriptor_fingerprint(replace(tool, **{key: value})))

    def test_discovery_compaction_preserves_original_semantics_and_public_metadata(self):
        tool = self.catalog.get("oa_upload_attachment_post")
        descriptor = service.public_tool(tool)
        original = "原接口未提供字段 这一行属于原始说明，不能按前缀删除。\nJSON 类型：这一行也是原始业务说明。"
        node = descriptor["inputSchema"]["properties"]["body"]
        node["description"] = original + SEMANTIC_GUIDANCE_MARKER + "业务用途/来源尚未核实。" + STRUCTURAL_GUIDANCE_MARKER + "JSON 类型：object"
        before = deepcopy(descriptor)
        projected = _discovery_tool(descriptor)
        self.assertEqual(descriptor, before)
        text = projected["inputSchema"]["properties"]["body"]["description"]
        self.assertIn(original, text)
        self.assertIn("业务用途/来源尚未核实", text)
        self.assertNotIn(STRUCTURAL_GUIDANCE_MARKER, text)
        for key in ("request_media_type", "annotations"):
            self.assertEqual(projected[key], descriptor[key])
        self.assertEqual(without_descriptions(projected["inputSchema"]), without_descriptions(descriptor["inputSchema"]))

    def test_chinese_near_synonyms_find_expected_tools_in_top_three(self):
        cases = (
            ("查客户", {"oa_list_customers_get"}),
            ("查询客户", {"oa_list_customers_get"}),
            ("新增客户", {"oa_create_customer_post"}),
            ("新建客户", {"oa_create_customer_post"}),
            ("修改客户", {"oa_patch_customer_patch"}),
            ("编辑客户", {"oa_patch_customer_patch"}),
            ("上传附件", {"oa_upload_attachment_post"}),
            ("导出案件", {"oa_export_current_ordinary_cases_excel_post"}),
            ("案件多少件", {"oa_case_statistics_post"}),
            ("统计案件数量", {"oa_case_statistics_post"}),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                names = [tool.name for tool in self.catalog.search(query, limit=3)]
                self.assertTrue(set(names).intersection(expected), f"{query}: {names}")

    def test_every_single_tool_is_discoverable_with_complete_schema(self):
        sizes = []
        failures = []
        raw_discoverable = 0
        for tool in self.catalog.tools:
            descriptor = service.public_tool(tool)
            raw_discoverable += encoded_size({"tools": [descriptor]}) <= 21_600
            compact = _discovery_tool(descriptor)
            self.assertEqual(without_descriptions(compact["inputSchema"]), without_descriptions(tool.input_schema))
            try:
                result = discovered_tools_view([descriptor])
            except RuntimeError as exc:
                failures.append((tool.name, encoded_size({"tools": [compact]}), str(exc)))
                continue
            self.assertEqual([entry["name"] for entry in result["tools"]], [tool.name])
            sizes.append((encoded_size(result), tool.name, encoded_size({"tools": [descriptor]})))
        print(f"Single-tool discovery: {len(sizes)}/{len(self.catalog.tools)}; raw descriptors fitting 21600 bytes: {raw_discoverable}; largest (result bytes, name, raw input bytes): {sorted(sizes, reverse=True)[:8]}; failures: {failures}")
        self.assertEqual(failures, [])

    def test_parameter_documentation_counts_known_and_unknown_without_schema_extensions(self):
        fields = self.enrich({"source_from": {"type": "string"},
                              "known": {"type": "string", "description": "真实原字段说明"},
                              "unknown": {"type": "string"}})
        schema = {"properties": {"body": {"properties": fields}}}
        before = deepcopy(schema)
        counts = parameter_documentation(schema)
        self.assertEqual(schema, before)
        self.assertEqual({key: counts[key] for key in ("total", "source_verified", "documented", "unknown")},
                         {"total": 3, "source_verified": 1, "documented": 1, "unknown": 1})
        self.assertEqual([gap["field"] for gap in counts["gaps"]], ["body.unknown"])
        totals = {key: 0 for key in ("total", "source_verified", "documented", "unknown")}
        for tool in self.catalog.tools:
            counts = parameter_documentation(tool.input_schema)
            self.assertEqual(counts["total"], counts["source_verified"] + counts["documented"] + counts["unknown"])
            self.assertEqual(len(counts["gaps"]), counts["unknown"])
            for key in totals:
                totals[key] += counts[key]
        print(f"Parameter documentation by field occurrence (not business acceptance): {totals}")

    def test_receipt_alias_retains_real_required_schema_and_validation(self):
        tool = self.catalog.get("oa_transact_ipr_case_assisted_fee_post")
        fields = {item.name: item for item in tool._route.dependant.body_params}
        self.assertEqual(fields["receipt_file"].alias, "file")
        self.assertEqual(tool.file_fields, {"file": False})
        schema = tool.input_schema
        self.assertIn("files", schema["required"])
        self.assertIn("file", schema["properties"]["files"]["required"])
        self.assertEqual(schema["properties"]["files"]["properties"]["file"]["minimum"], 1)
        arguments = {"path": {"case_id": 1, "assisted_fee_id": 2},
                     "body": {"response_date": "2026-10-19"}, "files": {"file": 3}}
        self.assertEqual(tool.validate_arguments(arguments)["files"], {"file": 3})
        for files in ({}, {"file": 0}, {"file": True}, {"file": "C:/receipt.pdf"}, {"receipt_file": 3}):
            with self.subTest(files=files), self.assertRaises(HTTPException):
                tool.validate_arguments({**arguments, "files": files})
        projected = discovered_tools_view([service.public_tool(tool)])["tools"][0]
        self.assertEqual(without_descriptions(projected["inputSchema"]), without_descriptions(schema))

    def test_discovery_does_not_rewrite_business_data_descriptions(self):
        original = "JSON 类型：原接口未提供字段，仍为真实说明。"
        schema = {"type": "object", "properties": {"body": {
            "type": "object", "default": {"description": original + SEMANTIC_GUIDANCE_MARKER + "data"},
            "description": original,
        }}}
        descriptor = {"name": "CODEX-schema", "inputSchema": schema,
                      "annotations": {"readOnlyHint": False}, "usage": {"limitations": ["必须人工确认"]}}
        projected = _discovery_tool(descriptor)
        self.assertEqual(projected, descriptor)


class ToolConfirmationSafetyTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = catalog_module.ToolCatalog(app)

    async def asyncSetUp(self):
        self.token = _auth_context.set(AuthContext(app, "CODEX-isolated-token", {
            "type": "http", "path": "/api/v1/mcp", "method": "POST", "headers": [],
        }))
        self.identity = {"username": "CODEX-isolated-user", "department": "隔离部门"}
        self.db = MagicMock()
        self.db.flush = AsyncMock()
        self.db.commit = AsyncMock()
        self.db.scalar = AsyncMock()
        self.session = MagicMock()
        self.session.__aenter__ = AsyncMock(return_value=self.db)
        self.session.__aexit__ = AsyncMock(return_value=False)

    async def asyncTearDown(self):
        _auth_context.reset(self.token)

    async def call_isolated(self, name, arguments):
        with patch.object(service, "get_catalog", return_value=self.catalog), \
             patch.object(service, "authenticated_identity", new=AsyncMock(return_value=self.identity)), \
             patch.object(service, "SessionLocal", return_value=self.session), \
             patch.object(service, "require_business_record_target", new=AsyncMock()), \
             patch.object(service, "trusted_case_origin", return_value=None), \
             patch.object(service, "prepare_business_arguments", new=AsyncMock(side_effect=lambda spec, args, params, identity, db: args)), \
             patch.object(service, "execute_original", new=AsyncMock(return_value={"items": []})) as execute:
            result = await service.call_tool(name, arguments)
            return result, execute

    async def test_query_post_executes_read_without_creating_confirmation(self):
        tool = self.catalog.get("oa_search_ordinary_cases_post")
        self.assertFalse(tool.is_write)
        result, execute = await self.call_isolated(tool.name, {"body": {}})
        self.assertEqual(result, {"items": []})
        execute.assert_awaited_once()
        self.db.add.assert_not_called()
        self.db.commit.assert_not_awaited()

    async def test_write_only_prepares_confirmation_without_executing_business(self):
        tool = self.catalog.get("oa_delete_customer_contact_delete")
        self.assertTrue(tool.is_write)
        result, execute = await self.call_isolated(tool.name, {"path": {"customer_id": 1, "contact_id": "CODEX-contact"}})
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["preview"]["requires_confirmation"])
        execute.assert_not_awaited()
        self.db.commit.assert_awaited_once()
        self.assertEqual(self.db.add.call_args_list[0].args[0].module, "agent_mcp_action")

    async def test_model_entry_cannot_approve_even_with_valid_arguments(self):
        with patch.object(service, "execute_original", new=AsyncMock()) as execute, self.assertRaises(HTTPException) as raised:
            await service.decide_tool_request("CODEX-request", "approved", self.identity, self.db)
        self.assertEqual(raised.exception.status_code, 403)
        self.db.scalar.assert_not_awaited()
        execute.assert_not_awaited()

    async def test_confirmation_path_without_trusted_frontend_headers_cannot_execute(self):
        token = _auth_context.set(AuthContext(app, "CODEX-isolated-token", {
            "type": "http", "path": "/api/v1/agent-tools/requests/CODEX-request/decision", "method": "POST", "headers": [],
        }))
        try:
            with patch.object(service, "execute_original", new=AsyncMock()) as execute, self.assertRaises(HTTPException) as raised:
                await service.decide_tool_request("CODEX-request", "approved", self.identity, self.db)
            self.assertEqual(raised.exception.status_code, 403)
            self.db.scalar.assert_not_awaited()
            execute.assert_not_awaited()
        finally:
            _auth_context.reset(token)


if __name__ == "__main__":
    unittest.main()

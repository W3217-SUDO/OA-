"""MVP contract tests for the LangGraph-backed case agent."""

import json
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.areas.legal.case_space as case_space_module
import app.main as main_module
from app.agent_mcp.auth import AuthContext, _auth_context
from app.agent_mcp.model_tools import MODEL_TOOLS, request_completion
from app.case_agent import RESPONSE_STYLE_RULES, CaseAgentRuntime, _MODEL_CHUNK_CALLBACK, _checkpoint_url, _extract_proposed_action
from app.agent_skills import AgentSkill
from app.database import Base
from app.main import (
    CaseAgentDecisionInput,
    CaseAgentMessageInput,
    CaseAgentProposedAction,
    case_agent_state,
    case_agent_status,
    decide_case_agent_action,
    get_case_workflow_guide,
    send_case_agent_message,
)
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent


class CaseAgentRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = CaseAgentRuntime(enabled=True, database_url="sqlite+aiosqlite:///:memory:")
        await self.runtime.start()

    async def asyncTearDown(self):
        await self.runtime.stop()

    def test_response_style_is_conclusion_first_and_actionable(self):
        self.assertIn("重点结论", RESPONSE_STYLE_RULES)
        self.assertIn("谁处理、做什么、何时完成", RESPONSE_STYLE_RULES)
        self.assertIn("不要输出 Markdown 标记字符", RESPONSE_STYLE_RULES)

    def test_model_action_block_is_removed_from_chat_and_normalized(self):
        content, action = _extract_proposed_action(
            '我可以为你更新案件说明。<proposed_action>{"type":"case.update","summary":"更新说明","payload":{"changes":{"description":"已沟通"}}}</proposed_action>'
        )
        self.assertEqual(content, "我可以为你更新案件说明。")
        self.assertEqual(action["type"], "case.update")
        self.assertEqual(action["payload"]["changes"]["description"], "已沟通")

    async def test_case_thread_persists_messages_and_approval_state(self):
        snapshot = {
            "case": {"id": 7, "serial_no": "SHMS-MVP-007"},
            "capabilities": {"can_create_reminder": True},
            "contracts": [{}],
            "documents": [{}, {}],
            "deadlines": [{}],
            "tasks": [],
            "finances": {"fees": [{}], "invoices": [{}]},
        }
        first = await self.runtime.invoke(
            case_id=7,
            operator="lawyer",
            message="请概括案件空间",
            case_snapshot=snapshot,
        )
        self.assertEqual(first["thread_id"], self.runtime.thread_id(7, "lawyer"))
        self.assertEqual(first["shared_space_id"], "case:7")
        self.assertIn("SHMS-MVP-007", first["last_response"])
        self.assertEqual(len(first["messages"]), 2)

        second = await self.runtime.invoke(
            case_id=7,
            operator="lawyer",
            message="准备新增案件提醒",
            case_snapshot=snapshot,
            proposed_action={
                "type": "case.reminder.create",
                "summary": "新增上诉期限提醒",
                "payload": {"deadline": "2026-08-31"},
            },
        )
        self.assertEqual(len(second["messages"]), 4)
        self.assertEqual(second["pending_actions"][0]["status"], "pending")
        action_id = second["pending_actions"][0]["id"]

        decided = await self.runtime.decide_action(
            case_id=7,
            action_id=action_id,
            decision="approved",
            operator="lawyer",
            comment="同意测试",
        )
        self.assertEqual(decided["pending_actions"][0]["status"], "approved")
        self.assertEqual(decided["pending_actions"][0]["decided_by"], "lawyer")
        self.assertEqual(len((await self.runtime.get_state(8, "lawyer"))["messages"]), 0)

    async def test_same_case_keeps_private_conversations_separate(self):
        snapshot = {"case": {"id": 17, "serial_no": "SHMS-SHARED-017"}, "documents": [{"id": 1}]}
        lawyer_state = await self.runtime.invoke(
            case_id=17,
            operator="lawyer",
            message="private lawyer note",
            case_snapshot=snapshot,
        )
        assistant_before = await self.runtime.get_state(17, "assistant")
        self.assertEqual(assistant_before["messages"], [])
        self.assertEqual(assistant_before["pending_actions"], [])
        self.assertEqual(assistant_before["shared_space_id"], lawyer_state["shared_space_id"])
        self.assertNotEqual(assistant_before["thread_id"], lawyer_state["thread_id"])

        assistant_state = await self.runtime.invoke(
            case_id=17,
            operator="assistant",
            message="private assistant note",
            case_snapshot=snapshot,
        )
        self.assertIn("SHMS-SHARED-017", assistant_state["last_response"])
        self.assertEqual(len(assistant_state["messages"]), 2)
        lawyer_after = await self.runtime.get_state(17, "lawyer")
        self.assertEqual(len(lawyer_after["messages"]), 2)
        self.assertEqual(lawyer_after["messages"][0]["content"], "private lawyer note")

    async def test_legacy_shared_thread_is_partitioned_by_message_owner(self):
        snapshot = {"case": {"id": 18, "serial_no": "SHMS-LEGACY-018"}, "capabilities": {"can_edit_basic": True}}
        for operator, message in (("lawyer", "legacy lawyer note"), ("assistant", "legacy assistant note")):
            await self.runtime.graph.ainvoke(
                {
                    "messages": [{
                        "id": operator,
                        "role": "user",
                        "content": message,
                        "operator": operator,
                        "created_at": "2026-08-11T00:00:00+00:00",
                    }],
                    "case_snapshot": snapshot,
                },
                self.runtime.legacy_config(18),
            )

        lawyer_state = await self.runtime.get_state(18, "lawyer")
        assistant_state = await self.runtime.get_state(18, "assistant")
        self.assertEqual([item["content"] for item in lawyer_state["messages"] if item["role"] == "user"], ["legacy lawyer note"])
        self.assertEqual([item["content"] for item in assistant_state["messages"] if item["role"] == "user"], ["legacy assistant note"])
        self.assertEqual(lawyer_state["shared_space_id"], assistant_state["shared_space_id"])
        self.assertNotEqual(lawyer_state["thread_id"], assistant_state["thread_id"])

    async def test_configured_model_receives_authorized_case_snapshot(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model_provider = "openai-compatible"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="这是基于案件空间生成的回答。")
        result = await self.runtime.invoke(
            case_id=9,
            operator="lawyer",
            message="案件有哪些期限风险？",
            case_snapshot={"case": {"id": 9, "serial_no": "SHMS-MODEL-009"}, "deadlines": [{}]},
        )
        self.assertTrue(self.runtime.status()["model_configured"])
        self.assertEqual(result["last_response"], "这是基于案件空间生成的回答。")
        snapshot, messages, skill, images = self.runtime._request_model.await_args.args
        self.assertEqual(snapshot["case"]["serial_no"], "SHMS-MODEL-009")
        self.assertEqual(messages[-1]["content"], "案件有哪些期限风险？")
        self.assertEqual(skill.id, "general-office")
        self.assertEqual(images, [])

    async def test_streaming_http_400_falls_back_to_non_stream_and_emits_content(self):
        class FakeResponse:
            def __init__(self, status_code, payload=None):
                self.status_code = status_code
                self.is_error = status_code >= 400
                self._payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def aiter_lines(self):
                if False:
                    yield ""

            def json(self):
                return self._payload

        class FakeClient:
            post_payloads = []
            stream_payloads = []

            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            def stream(self, *_args, **kwargs):
                self.stream_payloads.append(kwargs["json"])
                return FakeResponse(400)

            async def post(self, *_args, **kwargs):
                self.post_payloads.append(kwargs["json"])
                return FakeResponse(200, {"choices": [{"message": {"content": "民事起诉状完整正文"}}]})

        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        chunks = []
        token = _MODEL_CHUNK_CALLBACK.set(chunks.append)
        try:
            with patch("app.case_agent.httpx.AsyncClient", FakeClient):
                content, action = await self.runtime._request_model(
                    {"case": {"id": 9}},
                    [{"role": "user", "content": "帮我生成一个起诉状模板"}],
                )
                first_chunks = "".join(chunks)
                chunks.clear()
                second_content, second_action = await self.runtime._request_model(
                    {"case": {"id": 9}},
                    [{"role": "user", "content": "帮我再生成一个起诉状模板"}],
                )
        finally:
            _MODEL_CHUNK_CALLBACK.reset(token)

        self.assertEqual(content, "民事起诉状完整正文")
        self.assertIsNone(action)
        self.assertEqual(first_chunks, content)
        self.assertEqual(second_content, content)
        self.assertIsNone(second_action)
        self.assertEqual("".join(chunks), second_content)
        self.assertEqual(len(FakeClient.stream_payloads), 1)
        self.assertEqual(len(FakeClient.post_payloads), 2)
        self.assertFalse(FakeClient.post_payloads[0]["stream"])
        self.assertFalse(FakeClient.post_payloads[1]["stream"])
        self.assertEqual(FakeClient.stream_payloads[0]["tools"], MODEL_TOOLS)
        self.assertEqual(FakeClient.post_payloads[1]["tools"], MODEL_TOOLS)
        self.assertIs(self.runtime._model_stream_supported, False)

    async def test_stream_protocol_rejection_retries_once_with_unchanged_tools(self):
        payload = {"model": "gpt-test", "messages": [{"role": "user", "content": "query"}], "tools": MODEL_TOOLS}
        message = {
            "role": "assistant",
            "content": "可见正文<proposed_action>{\"type\":\"case.update\"}</proposed_action>",
            "reasoning_content": "private reasoning",
            "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "oa_search_tools", "arguments": "{}"}}],
        }
        for status in (400, 404, 405, 415, 422, 501):
            with self.subTest(status=status):
                requests = []
                closed = []
                chunks = []
                stream_support = []

                class RejectedStream(httpx.AsyncByteStream):
                    async def __aiter__(self):
                        yield b"stream unsupported"

                    async def aclose(self):
                        closed.append(True)

                def respond(request):
                    requests.append(json.loads(request.content))
                    if len(requests) == 1:
                        return httpx.Response(status, stream=RejectedStream())
                    self.assertEqual(closed, [True])
                    return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": "tool_calls"}]})

                async def on_delta(content):
                    chunks.append(content)

                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    result = await request_completion(client, "https://model.example/v1/chat/completions", {}, payload, stream=True, on_delta=on_delta, on_stream_support=stream_support.append)
                self.assertEqual(requests, [{**payload, "stream": True}, {**payload, "stream": False}])
                self.assertEqual(result, message)
                self.assertEqual("".join(chunks), "可见正文")
                self.assertEqual(stream_support, [False])

    async def test_non_stream_retry_does_not_hide_genuine_http_error(self):
        requests = []
        on_delta = AsyncMock()
        stream_support = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(400, json={"error": {"message": "invalid tools schema"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaisesRegex(RuntimeError, "^model_http_400$"):
                await request_completion(client, "https://model.example/v1/chat/completions", {}, {"tools": MODEL_TOOLS}, stream=True, on_delta=on_delta, on_stream_support=stream_support.append)
        self.assertEqual([item["stream"] for item in requests], [True, False])
        self.assertEqual(stream_support, [False])
        on_delta.assert_not_awaited()

    async def test_successful_stream_preserves_tool_fragments_and_visible_content(self):
        chunks = []
        requests = []
        stream_support = []
        events = [
            {"choices": [{"delta": {
                "content": "可见正文<proposed_", "reasoning_content": "private ",
                "tool_calls": [{"index": 0, "id": "call-", "function": {"name": "oa_", "arguments": '{"query":'}}],
            }}]},
            {"choices": [{"delta": {
                "content": "action>{}</proposed_action>", "reasoning_content": "reasoning",
                "tool_calls": [{"index": 0, "id": "1", "function": {"name": "search_tools", "arguments": '"案件"}'}}],
            }, "finish_reason": "tool_calls"}]},
        ]

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, text="".join(f"data: {json.dumps(event)}\n\n" for event in events))

        async def on_delta(content):
            chunks.append(content)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            result = await request_completion(client, "https://model.example/v1/chat/completions", {}, {"tools": MODEL_TOOLS}, stream=True, on_delta=on_delta, on_stream_support=stream_support.append)
        self.assertEqual(requests, [{"tools": MODEL_TOOLS, "stream": True}])
        self.assertEqual(stream_support, [True])
        self.assertEqual("".join(chunks), "可见正文")
        self.assertEqual(result, {
            "role": "assistant", "content": "可见正文<proposed_action>{}</proposed_action>",
            "reasoning_content": "private reasoning",
            "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "oa_search_tools", "arguments": '{"query":"案件"}'}}],
        })

    async def test_stream_auth_rate_limit_and_server_errors_are_not_retried(self):
        for status in (401, 403, 429, 500, 502, 503):
            with self.subTest(status=status):
                requests = []
                stream_support = []

                def respond(request):
                    requests.append(json.loads(request.content))
                    return httpx.Response(status, json={"error": "request failed"})

                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    with self.assertRaisesRegex(RuntimeError, f"^model_http_{status}$"):
                        await request_completion(client, "https://model.example/v1/chat/completions", {}, {}, stream=True, on_stream_support=stream_support.append)
                self.assertEqual(requests, [{"stream": True}])
                self.assertEqual(stream_support, [])

    async def test_failed_or_incomplete_stream_is_not_retried(self):
        for event, error in (
            ({"error": {"message": "provider failure"}}, "model_stream_error"),
            ({"choices": [{"delta": {"content": "partial"}}]}, "model_stream_incomplete"),
            ({"choices": [{"delta": {}, "finish_reason": "length"}]}, "model_response_incomplete"),
            ({"choices": [{"delta": {}, "finish_reason": "content_filter"}]}, "model_response_incomplete"),
        ):
            with self.subTest(error=error):
                requests = []
                stream_support = []

                def respond(request):
                    requests.append(json.loads(request.content))
                    return httpx.Response(200, text=f"data: {json.dumps(event)}\n\n")

                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    with self.assertRaisesRegex(RuntimeError, f"^{error}$"):
                        await request_completion(client, "https://model.example/v1/chat/completions", {}, {}, stream=True, on_stream_support=stream_support.append)
                self.assertEqual(requests, [{"stream": True}])
                self.assertEqual(stream_support, [])

    async def test_non_stream_emission_hides_personal_action_and_rejects_truncation(self):
        chunks = []

        async def on_delta(content):
            chunks.append(content)

        message = {"role": "assistant", "content": "可见正文<personal_action>{}</personal_action>"}
        for reason in ("stop", "length", "content_filter"):
            with self.subTest(reason=reason):
                chunks.clear()

                def respond(_request):
                    return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": reason}]})

                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                    if reason == "stop":
                        result = await request_completion(client, "https://model.example/v1/chat/completions", {}, {}, stream=False, on_delta=on_delta)
                        self.assertEqual(result, message)
                        self.assertEqual("".join(chunks), "可见正文")
                    else:
                        with self.assertRaisesRegex(RuntimeError, "^model_response_incomplete$"):
                            await request_completion(client, "https://model.example/v1/chat/completions", {}, {}, stream=False, on_delta=on_delta)
                        self.assertEqual(chunks, [])

    async def test_user_skill_override_reaches_model_without_changing_case_scope(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="custom skill response")
        custom_skill = AgentSkill(
            id="custom-test",
            name="Custom Review",
            category="Custom",
            description="Review",
            source="user-custom",
            available=True,
            unavailable_reason="",
            instruction="User preference with system boundary.",
            quick_prompts=(),
        )
        await self.runtime.invoke(
            case_id=19,
            operator="lawyer",
            message="[[skill:custom-test]]\nreview this case",
            case_snapshot={"case": {"id": 19, "serial_no": "SHMS-CUSTOM-019"}},
            skill_override=custom_skill,
        )
        snapshot, messages, selected_skill, _ = self.runtime._request_model.await_args.args
        self.assertEqual(snapshot["case"]["serial_no"], "SHMS-CUSTOM-019")
        self.assertEqual(messages[-1]["content"], "review this case")
        self.assertEqual(selected_skill.id, "custom-test")

    async def test_model_write_proposal_is_blocked_by_original_user_capability(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value=(
            "我可以修改案件说明。",
            {"type": "case.update", "summary": "越权修改案件", "payload": {"changes": {"description": "不应写入"}}},
        ))
        result = await self.runtime.invoke(
            case_id=12,
            operator="assistant",
            message="修改案件说明",
            case_snapshot={
                "case": {"id": 12, "serial_no": "SHMS-MODEL-012"},
                "capabilities": {"can_write": True, "can_edit_basic": False},
            },
        )
        self.assertEqual(result["pending_actions"], [])
        self.assertIn("原有业务权限不允许", result["last_response"])

    async def test_selected_office_skill_routes_without_exposing_marker(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="已完成数据分析。")
        result = await self.runtime.invoke(
            case_id=10,
            operator="lawyer",
            message="[[skill:data-analysis]]\n检查费用异常",
            case_snapshot={"case": {"id": 10}, "finances": {"fees": []}},
        )
        self.assertEqual(result["active_skill"], "data-analysis")
        self.assertEqual(result["messages"][0]["content"], "检查费用异常")
        self.assertNotIn("[[skill:", result["messages"][0]["content"])
        self.assertEqual(self.runtime._request_model.await_args.args[2].id, "data-analysis")

    async def test_screenshot_skill_forwards_images_without_persisting_base64(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="已分析截图。")
        result = await self.runtime.invoke(
            case_id=11,
            operator="lawyer",
            message="[[skill:screenshot-evidence]]\n分析截图证据",
            case_snapshot={"case": {"id": 11}},
            images=[{"id": 91, "name": "evidence.png", "mime_type": "image/png", "data_url": "data:image/png;base64,dGVzdA=="}],
        )
        self.assertEqual(result["active_skill"], "screenshot-evidence")
        self.assertEqual(result["messages"][0]["attachments"][0]["name"], "evidence.png")
        self.assertNotIn("data_url", result["messages"][0]["attachments"][0])
        self.assertEqual(self.runtime._request_model.await_args.args[3][0]["data_url"], "data:image/png;base64,dGVzdA==")

    def test_sqlalchemy_postgres_url_is_normalized_for_psycopg(self):
        self.assertEqual(
            _checkpoint_url("postgresql+asyncpg://user:pass@postgres:5432/legal", ""),
            "postgresql://user:pass@postgres:5432/legal",
        )


class CaseAgentApiContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.runtime = CaseAgentRuntime(enabled=True, database_url="sqlite+aiosqlite:///:memory:")
        await self.runtime.start()
        self.original_runtime = case_space_module.case_agent_runtime
        case_space_module.case_agent_runtime = self.runtime

    async def asyncTearDown(self):
        case_space_module.case_agent_runtime = self.original_runtime
        await self.runtime.stop()
        await self.engine.dispose()

    async def _decide_action(self, case_id, action_id, body, identity, db, *, confirmation="frontend", origin="http://localhost"):
        # 直接调用路由时补齐前端请求上下文，仍执行真实确认门禁和业务权限校验。
        context = AuthContext(main_module.app, "test-only", {
            "type": "http", "method": "POST",
            "path": f"{main_module.settings.api_prefix}/case-spaces/{case_id}/agent/actions/{action_id}/decision",
            "headers": [
                (b"origin", origin.encode("ascii")),
                (b"x-oa-agent-confirmation", confirmation.encode("ascii")),
            ],
        })
        token = _auth_context.set(context)
        try:
            return await decide_case_agent_action(case_id, action_id, body, identity, db)
        finally:
            context.active = False
            context.bearer = ""
            context.scope.clear()
            _auth_context.reset(token)

    async def _seed(self, db: AsyncSession) -> BusinessRecord:
        db.add_all([
            User(username="lawyer", display_name="范文玲", department="上海", password_hash="x", role="admin"),
            User(username="assistant", display_name="律师助理", department="上海", password_hash="x", role="user"),
            User(username="outsider", display_name="外部人员", department="北京", password_hash="x", role="user"),
        ])
        case = BusinessRecord(
            module="case",
            serial_no="SHMS-MVP-001",
            title="LangGraph MVP 案件",
            customer="测试客户",
            status="办理中",
            owner="lawyer",
            department="上海",
            data={"case_type": "民事案件", "handling_lawyer_usernames": ["lawyer"], "assistant_username": "assistant", "case_team_usernames": ["lawyer", "assistant"]},
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        return case

    async def _seed_linked_customer_and_contract(self, db: AsyncSession, case: BusinessRecord):
        customer = BusinessRecord(
            module="customer", serial_no="SHKH-MVP-001", title="测试客户", customer="测试客户",
            status="签约", owner="lawyer", department="上海", description="原客户说明",
            data={"customer_type": "企业客户", "customer_managers": ["lawyer"]},
        )
        db.add(customer)
        await db.flush()
        contract = BusinessRecord(
            module="contract", serial_no="HT-MVP-001", title="测试客户服务合同", customer=customer.title,
            status="草稿", owner="lawyer", department="上海", description="原合同说明",
            data={"customer_id": customer.id, "customer_no": customer.serial_no, "amount": 1000},
        )
        db.add(contract)
        await db.flush()
        case.customer = customer.title
        case.data = {**(case.data or {}), "customer_id": customer.id, "contract_id": contract.id, "contract_no": contract.serial_no}
        await db.commit()
        await db.refresh(customer)
        await db.refresh(contract)
        await db.refresh(case)
        return customer, contract

    async def test_authorized_api_flow_and_action_decision(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            status = await case_agent_status(case.id, identity, db)
            self.assertTrue(status["ready"])
            workflow = await get_case_workflow_guide(case.id, identity, db)
            self.assertEqual(workflow["manual"]["version"], "2026-08")
            self.assertEqual(workflow["current_phase"]["code"], "document-preparation")
            self.assertTrue(workflow["materials"])
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="准备更新案件信息",
                    proposed_action=CaseAgentProposedAction(
                        type="case.update",
                        summary="更新案件备注",
                        payload={"description": "MVP only"},
                    ),
                ),
                identity,
                db,
            )
            self.assertEqual(result["pending_actions"][0]["status"], "pending")
            state = await case_agent_state(case.id, identity, db)
            self.assertEqual(state["thread_id"], case_space_module.case_agent_runtime.thread_id(case.id, identity["username"]))
            self.assertEqual(state["shared_space_id"], f"case:{case.id}")
            action_id = result["pending_actions"][0]["id"]
            decision = CaseAgentDecisionInput(decision="rejected", comment="测试不落库")
            with self.assertRaises(HTTPException) as missing_request:
                await decide_case_agent_action(case.id, action_id, decision, identity, db)
            self.assertEqual(missing_request.exception.status_code, 401)
            for headers in ({"confirmation": ""}, {"origin": "https://untrusted.example"}):
                with self.assertRaises(HTTPException) as invalid_confirmation:
                    await self._decide_action(case.id, action_id, decision, identity, db, **headers)
                self.assertEqual(invalid_confirmation.exception.status_code, 403)
            self.assertEqual((await self.runtime.get_state(case.id, identity["username"]))["pending_actions"][0]["status"], "pending")
            self.assertEqual(list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "agent_action"))).all()), [])
            result = await self._decide_action(
                case.id,
                action_id,
                decision,
                identity,
                db,
            )
            self.assertEqual(result["pending_actions"][0]["status"], "rejected")
            unchanged = await db.get(BusinessRecord, case.id)
            self.assertEqual(unchanged.description, "")

    async def test_approved_case_update_is_applied_and_audited(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="把案件说明改为已完成客户沟通",
                    proposed_action=CaseAgentProposedAction(
                        type="case.update",
                        summary="更新案件说明",
                        payload={"changes": {"description": "已完成客户沟通"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][0]
            self.assertEqual(action["preview"]["changes"][0]["before"], "")
            self.assertEqual(action["preview"]["changes"][0]["after"], "已完成客户沟通")
            decided = await self._decide_action(
                case.id,
                action["id"],
                CaseAgentDecisionInput(decision="approved", comment="同意执行"),
                identity,
                db,
            )
            approved = decided["pending_actions"][0]
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["execution_result"]["updated_fields"]["description"], "已完成客户沟通")
            updated = await db.get(BusinessRecord, case.id)
            self.assertEqual(updated.description, "已完成客户沟通")
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == case.id))).all())
            self.assertTrue(any(item.action == "智能体审批后更新案件" for item in events))

    async def test_approved_linked_customer_update_uses_customer_business_guard(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            customer, _ = await self._seed_linked_customer_and_contract(db, case)
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="修改关联客户说明",
                    proposed_action=CaseAgentProposedAction(
                        type="customer.update",
                        summary="更新客户说明",
                        payload={"target_id": customer.id, "changes": {"description": "智能体审批后的客户说明"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][-1]
            self.assertEqual(action["preview"]["target"], customer.serial_no)
            await self._decide_action(case.id, action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            updated = await db.get(BusinessRecord, customer.id)
            self.assertEqual(updated.description, "智能体审批后的客户说明")

    async def test_approved_linked_contract_update_uses_contract_draft_guard(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            _, contract = await self._seed_linked_customer_and_contract(db, case)
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="修改关联合同说明",
                    proposed_action=CaseAgentProposedAction(
                        type="contract.update",
                        summary="更新合同说明",
                        payload={"target_id": contract.id, "changes": {"description": "智能体审批后的合同说明"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][-1]
            self.assertEqual(action["preview"]["target"], contract.serial_no)
            await self._decide_action(case.id, action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            updated = await db.get(BusinessRecord, contract.id)
            self.assertEqual(updated.description, "智能体审批后的合同说明")

    async def test_agent_cannot_update_customer_outside_current_case_space(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            _, _ = await self._seed_linked_customer_and_contract(db, case)
            outsider = BusinessRecord(
                module="customer", serial_no="SHKH-MVP-OUTSIDE", title="其他客户", customer="其他客户",
                status="签约", owner="lawyer", department="上海", description="不可修改",
            )
            db.add(outsider)
            await db.commit()
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="尝试修改空间外客户",
                    proposed_action=CaseAgentProposedAction(
                        type="customer.update",
                        summary="错误目标测试",
                        payload={"target_id": outsider.id, "changes": {"description": "不应写入"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][-1]
            with self.assertRaises(HTTPException) as raised:
                await self._decide_action(case.id, action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            self.assertEqual(raised.exception.status_code, 404)
            unchanged = await db.get(BusinessRecord, outsider.id)
            self.assertEqual(unchanged.description, "不可修改")

    async def test_assistant_cannot_see_or_approve_another_users_pending_action(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            manager_identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="修改案件说明",
                    proposed_action=CaseAgentProposedAction(
                        type="case.update",
                        summary="修改案件说明",
                        payload={"changes": {"description": "不应由助理写入"}},
                    ),
                ),
                manager_identity,
                db,
            )
            action = result["pending_actions"][0]
            assistant_identity = {"username": "assistant", "role": "user"}
            assistant_state = await case_agent_state(case.id, assistant_identity, db)
            self.assertEqual(assistant_state["messages"], [])
            self.assertEqual(assistant_state["pending_actions"], [])
            self.assertEqual(assistant_state["shared_space_id"], result["shared_space_id"])
            self.assertNotEqual(assistant_state["thread_id"], result["thread_id"])
            with self.assertRaises(HTTPException) as raised:
                await self._decide_action(
                    case.id,
                    action["id"],
                    CaseAgentDecisionInput(decision="approved"),
                    assistant_identity,
                    db,
                )
            self.assertEqual(raised.exception.status_code, 404)
            unchanged = await db.get(BusinessRecord, case.id)
            self.assertEqual(unchanged.description, "")

    async def test_approved_task_and_reminder_proposals_create_linked_records(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            deadline = date.today() + timedelta(days=5)
            task_result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="创建案件任务",
                    proposed_action=CaseAgentProposedAction(
                        type="case.task.create",
                        summary="创建补充材料任务",
                        payload={"title": "补充立案材料", "owner": "lawyer", "deadline": str(deadline), "priority": "普通"},
                    ),
                ),
                identity,
                db,
            )
            task_action = task_result["pending_actions"][-1]
            await self._decide_action(case.id, task_action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all())
            self.assertTrue(any((item.data or {}).get("case_record_id") == case.id for item in tasks))

            reminder_result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="创建案件提醒",
                    proposed_action=CaseAgentProposedAction(
                        type="case.reminder.create",
                        summary="创建材料期限提醒",
                        payload={"content": "检查立案材料", "reminder_date": str(date.today() + timedelta(days=2)), "deadline": str(deadline)},
                    ),
                ),
                identity,
                db,
            )
            reminder_action = reminder_result["pending_actions"][-1]
            await self._decide_action(case.id, reminder_action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            reminders = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case_reminder"))).all())
            self.assertTrue(any((item.data or {}).get("case_id") == case.id for item in reminders))

    async def test_unauthorized_user_cannot_open_case_agent(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            with self.assertRaises(HTTPException) as raised:
                await case_agent_status(
                    case.id,
                    {"username": "outsider", "role": "user"},
                    db,
                )
        self.assertEqual(raised.exception.status_code, 404)

    async def test_screenshot_attachment_is_scoped_to_case_and_forwarded(self):
        target = main_module.UPLOAD_ROOT / "case-agent-contract-screenshot.png"
        target.write_bytes(b"test-png")
        try:
            async with self.sessions() as db:
                case = await self._seed(db)
                attachment = FileAttachment(
                    record_id=case.id,
                    category="智能体截图证据",
                    original_name="contract-screenshot.png",
                    stored_name=target.name,
                    content_type="image/png",
                    size=target.stat().st_size,
                    path=str(target),
                    uploader="lawyer",
                    remark="test",
                )
                db.add(attachment)
                await db.commit()
                await db.refresh(attachment)
                result = await send_case_agent_message(
                    case.id,
                    CaseAgentMessageInput(
                        message="[[skill:screenshot-evidence]]\n分析截图证据",
                        attachment_ids=[attachment.id],
                    ),
                    {"username": "lawyer", "role": "admin"},
                    db,
                )
                self.assertEqual(result["messages"][0]["attachments"][0]["id"], attachment.id)
                self.assertEqual(result["messages"][0]["attachments"][0]["name"], "contract-screenshot.png")
        finally:
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

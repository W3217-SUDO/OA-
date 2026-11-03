"""云端智能体（火山 Managed Agents）：事件流解析、自定义工具回传、增量输出和连接测试，全部用假接口，不访问火山。"""
import asyncio
import json

import httpx
from fastapi import HTTPException

from app.areas.agent_admin.cloud_runtime import probe
from app.cloud_agent.client import ArkClient
from app.cloud_agent.runtime import agent_body, content_blocks, custom_tool, run_turn

FAKE_KEY = "ark-test-fake-key"


def _sse(events):
    lines = [": ready", ""]
    for event in events:
        lines += ["data: " + json.dumps(event, ensure_ascii=False), ""]
    return "\n".join(lines) + "\n"


class FakeArk:
    """按顺序返回两段事件流：第一段要求调用 OA 工具，回传结果后第二段给出最终回复。"""

    def __init__(self, phases):
        self.phases = list(phases)
        self.posted = []

    def handler(self, request: httpx.Request):
        assert request.headers["authorization"] == "Bearer " + FAKE_KEY
        if request.url.path.endswith("/events/stream"):
            assert request.url.params.get("event_deltas") == "agent.message"
            events = [event for phase in self.phases for event in phase]
            return httpx.Response(200, text=_sse(events), headers={"content-type": "text/event-stream"})
        if request.url.path.endswith("/events") and request.method == "POST":
            self.posted.append(json.loads(request.content))
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404, json={"error": {"code": "NotFound", "message": "x"}})


class FakeTools:
    def __init__(self):
        self.calls = []

    async def execute(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "forbidden":
            raise HTTPException(403, "无权限")
        return {"case_no": arguments.get("case_no"), "status": "已立案"}


def test_turn_runs_custom_tool_and_streams_reply():
    phases = [[
        {"id": "e1", "type": "session.status_running"},
        {"id": "t1", "type": "agent.custom_tool_use", "name": "query_case", "input": {"case_no": "A1"}},
        {"id": "i1", "type": "session.status_idle", "stop_reason": {"type": "requires_action", "event_ids": ["t1"]}},
    ], [
        {"id": "f1", "type": "event_start", "event": {"id": "m1", "type": "agent.message"}},
        {"id": "f2", "type": "event_delta", "event_id": "m1", "delta": {"type": "content_delta", "content": {"type": "text", "text": "案件"}, "index": 0}},
        {"id": "f3", "type": "event_delta", "event_id": "m1", "delta": {"type": "content_delta", "content": {"type": "text", "text": "已立案"}, "index": 0}},
        {"id": "m1", "type": "agent.message", "content": [{"type": "text", "text": "案件已立案。"}]},
        {"id": "u1", "type": "session.usage", "usage": {}},
        {"id": "i2", "type": "session.status_idle", "stop_reason": {"type": "end_turn"}},
    ]]
    fake, tools, deltas = FakeArk(phases), FakeTools(), []

    async def on_delta(text):
        deltas.append(text)

    async def scenario():
        async with ArkClient(FAKE_KEY, base_url="https://ark.test/api/v3", transport=httpx.MockTransport(fake.handler)) as client:
            return await run_turn(client, "sesn-1", [{"type": "text", "text": "[USER]\n查 A1"}], tools, on_delta, None)

    answer = asyncio.run(scenario())
    assert answer == "案件已立案。"
    assert "".join(deltas) == "案件已立案。"
    assert tools.calls == [("query_case", {"case_no": "A1"})]
    assert fake.posted[0]["events"][0]["type"] == "user.message"
    result = fake.posted[1]["events"][0]
    assert result["type"] == "user.custom_tool_result" and result["custom_tool_use_id"] == "t1" and result["is_error"] is False
    assert json.loads(result["content"][0]["text"])["status"] == "已立案"


def test_tool_permission_error_is_returned_not_swallowed_as_success():
    phases = [[
        {"id": "t1", "type": "agent.custom_tool_use", "name": "forbidden", "input": {}},
        {"id": "i1", "type": "session.status_idle", "stop_reason": {"type": "requires_action", "event_ids": ["t1"]}},
        {"id": "m1", "type": "agent.message", "content": [{"type": "text", "text": "没有权限。"}]},
        {"id": "i2", "type": "session.status_idle", "stop_reason": {"type": "end_turn"}},
    ]]
    fake = FakeArk(phases)

    async def scenario():
        async with ArkClient(FAKE_KEY, base_url="https://ark.test/api/v3", transport=httpx.MockTransport(fake.handler)) as client:
            return await run_turn(client, "sesn-1", [], FakeTools(), _noop, None)

    assert asyncio.run(scenario()) == "没有权限。"
    result = fake.posted[1]["events"][0]
    assert result["is_error"] is True and "无权限" in result["content"][0]["text"]


def test_stream_ending_without_end_turn_is_an_error():
    fake = FakeArk([[{"id": "m1", "type": "agent.message", "content": [{"type": "text", "text": "半截"}]}]])

    async def scenario():
        async with ArkClient(FAKE_KEY, base_url="https://ark.test/api/v3", transport=httpx.MockTransport(fake.handler)) as client:
            return await run_turn(client, "sesn-1", [], FakeTools(), _noop, None)

    try:
        asyncio.run(scenario())
    except HTTPException as exc:
        assert exc.status_code == 502
    else:
        raise AssertionError("断流不能当成功")


async def _noop(_text):
    return None


def test_content_blocks_resume_only_sends_system_and_last_message():
    messages = [{"role": "system", "content": "规则"}, {"role": "user", "content": "一"}, {"role": "assistant", "content": "答"},
                {"role": "user", "content": [{"type": "text", "text": "二"},
                                             {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}]}]
    blocks = content_blocks(messages, resumed=True, catalog="")
    assert [block.get("text") for block in blocks if block["type"] == "text"] == ["[SYSTEM]\n规则", "二"]
    assert blocks[-1] == {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"}}
    assert len(content_blocks(messages, resumed=False, catalog="技能")) == 6


def test_agent_definition_keeps_oa_tools_custom_and_sandbox_limited():
    schema = {"type": "function", "function": {"name": "query_case", "description": "查案件",
                                               "parameters": {"type": "object", "properties": {}}}}
    assert custom_tool(schema) == {"type": "custom", "name": "query_case", "description": "查案件",
                                   "input_schema": {"type": "object", "properties": {}}}
    body = agent_body("deepseek-v4-1-flash-261017", [schema])
    sandbox = body["tools"][0]
    assert sandbox["default_config"]["enabled"] is False
    assert {item["name"] for item in sandbox["configs"]} == {"bash", "read", "write", "edit", "glob", "grep", "web_fetch", "web_search"}


def test_probe_reports_model_not_open_and_cleans_up_agent():
    deleted = []

    def handler(request: httpx.Request):
        if request.method == "POST":
            body = json.loads(request.content)
            if body["model"]["id"] == "closed":
                return httpx.Response(400, json={"error": {"code": "InvalidParameter", "message": "service not open"}})
            return httpx.Response(200, json={"id": "agent-1"})
        deleted.append(request.url.path)
        return httpx.Response(200, json={})

    ok, message = asyncio.run(probe(FAKE_KEY, "closed", transport=httpx.MockTransport(handler)))
    assert not ok and "开通" in message
    ok, _ = asyncio.run(probe(FAKE_KEY, "open", transport=httpx.MockTransport(handler)))
    assert ok and deleted == ["/api/v3/agents/agent-1"]


def test_doubao_search_uses_plan_key_and_official_payload():
    from app.cloud_agent.harness import doubao_search
    seen = {}

    def handler(request: httpx.Request):
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], json.loads(request.content)
        return httpx.Response(200, json={"Result": {"WebResults": [{"Title": "测试"}]}})

    result = asyncio.run(doubao_search("plan-fake", {"Query": "上海 律师 新规", "AuthLevel": 1, "NeedContent": True},
                                       transport=httpx.MockTransport(handler)))
    assert seen["url"] == "https://open.feedcoopapi.com/search_api/web_search" and seen["auth"] == "Bearer plan-fake"
    assert seen["body"]["Filter"] == {"NeedUrl": True, "AuthInfoLevel": 1, "NeedContent": True}
    assert "测试" in result["result"]


def test_harness_tools_route_and_fall_through_to_oa_tools():
    from app.cloud_agent import harness

    calls = []

    async def fake_datapro(key, arguments):
        calls.append(("datapro", key, arguments["query"]))
        return {"result": "法条"}

    original = harness.datapro
    harness.datapro = fake_datapro
    try:
        oa = FakeTools()
        tools = harness.HarnessTools(oa, "plan-fake")
        assert asyncio.run(tools.execute("volc_professional_data", {"query": "民法典第577条"})) == {"result": "法条"}
        assert asyncio.run(tools.execute("query_case", {"case_no": "A1"}))["status"] == "已立案"
    finally:
        harness.datapro = original
    assert calls == [("datapro", "plan-fake", "民法典第577条")] and oa.calls == [("query_case", {"case_no": "A1"})]


def test_builtin_web_search_off_when_doubao_search_on():
    body = agent_body("m", [], web_search=False)
    assert "web_search" not in {item["name"] for item in body["tools"][0]["configs"]}


def test_usage_peak_hours_and_cost():
    from datetime import datetime
    from app.cloud_agent.usage import BEIJING, TurnUsage, peak

    assert peak(datetime(2026, 11, 3, 10, 0, tzinfo=BEIJING)) and peak(datetime(2026, 11, 3, 17, 59, tzinfo=BEIJING))
    assert not peak(datetime(2026, 11, 3, 12, 30, tzinfo=BEIJING)) and not peak(datetime(2026, 11, 8, 10, 0, tzinfo=BEIJING))
    usage = TurnUsage()
    # 空闲：100 万未缓存输入 + 100 万缓存 + 100 万输出 = 0.8 + 0.016 + 3.2；高峰同量 = 1.6 + 0.032 + 6.4
    usage.model_request({"processed_at": "2026-11-03T12:30:00+08:00",
                         "model_usage": {"input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000, "output_tokens": 1_000_000}})
    usage.model_request({"processed_at": "2026-11-03T02:00:00Z",
                         "model_usage": {"input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000, "output_tokens": 1_000_000}})
    assert usage.session_usage({"usage": {"active_seconds": 3700}}, 100) == 3700
    usage.tool("volc_professional_data", {"result": json.dumps({"dataset_type": "legal_case"})})
    usage.tool("doubao_search", {"result": "{}"})
    usage.tool("biz_my_tasks", {"items": []})
    record = usage.record(username="u1", display_name="张三", workspace="personal", conversation="c", model="deepseek-v4-1-flash-economy-261017", ok=True)
    assert round(record["model_yuan"], 4) == round(0.8 + 0.016 + 3.2 + 1.6 + 0.032 + 6.4, 4)
    assert record["runtime_yuan"] == 0.5 and record["harness_afp"] == 48 + 5 and record["oa_tools"] == 1
    assert record["datapro"] == {"legal_case": 1} and record["peak_tokens"] == 3_000_000


def test_usage_ledger_summarizes_per_person(tmp_path=None):
    import tempfile
    from pathlib import Path
    from app.cloud_agent.usage import append, read_month, summarize

    directory = Path(tmp_path or tempfile.mkdtemp())
    base = {"conversation": "c", "model": "m", "ok": True, "requests": 1, "input_tokens": 10, "cache_tokens": 90, "output_tokens": 5,
            "active_seconds": 2, "oa_tools": 1, "datapro": {}, "searches": 0, "harness_afp": 0, "model_yuan": 0.01,
            "runtime_yuan": 0.001, "harness_yuan": 0}
    append({**base, "time": "2026-11-03T10:00:00+08:00", "username": "a", "display_name": "甲", "workspace": "personal"}, directory)
    append({**base, "time": "2026-11-03T11:00:00+08:00", "username": "a", "display_name": "甲", "workspace": "case:9", "ok": False}, directory)
    append({**base, "time": "2026-11-04T09:00:00+08:00", "username": "b", "display_name": "乙", "workspace": "personal",
            "datapro": {"legal_case": 2}, "harness_afp": 96, "harness_yuan": 0.192}, directory)
    summary = summarize(read_month("2026-11", directory))
    first = summary["people"][0]
    assert first["username"] == "b" and first["datapro"] == 2 and first["total_yuan"] == round(0.01 + 0.001 + 0.192, 4)
    person_a = summary["people"][1]
    assert (person_a["turns"], person_a["personal_turns"], person_a["case_turns"], person_a["failed"]) == (2, 1, 1, 1)
    assert summary["total"]["turns"] == 3 and [day["date"] for day in summary["days"]] == ["2026-11-03", "2026-11-04"]


def test_turn_collects_usage_events():
    from app.cloud_agent.usage import TurnUsage

    phases = [[
        {"id": "s1", "type": "span.model_request_end", "processed_at": "2026-11-03T12:30:00+08:00",
         "model_usage": {"input_tokens": 100, "cache_read_input_tokens": 900, "output_tokens": 20}},
        {"id": "t1", "type": "agent.custom_tool_use", "name": "query_case", "input": {"case_no": "A1"}},
        {"id": "i1", "type": "session.status_idle", "stop_reason": {"type": "requires_action", "event_ids": ["t1"]}},
        {"id": "m1", "type": "agent.message", "content": [{"type": "text", "text": "好"}]},
        {"id": "u1", "type": "session.usage", "usage": {"active_seconds": 12.5}},
        {"id": "i2", "type": "session.status_idle", "stop_reason": {"type": "end_turn"}},
    ]]
    fake, usage = FakeArk(phases), TurnUsage()

    async def scenario():
        async with ArkClient(FAKE_KEY, base_url="https://ark.test/api/v3", transport=httpx.MockTransport(fake.handler)) as client:
            return await run_turn(client, "sesn-1", [], FakeTools(), _noop, None, usage, 10.0)

    assert asyncio.run(scenario()) == "好"
    assert usage.requests == 1 and usage.tokens["offpeak"] == [100, 900, 20] and usage.oa_tools == 1
    assert usage.active_seconds == 2.5 and usage.active_total == 12.5


def test_harness_network_failure_returns_error_instead_of_failing_turn():
    from app.cloud_agent import harness

    async def broken(key, arguments):
        raise OSError("dns")

    original = harness.datapro
    harness.datapro = broken
    try:
        result = asyncio.run(harness.HarnessTools(FakeTools(), "k").execute("volc_professional_data", {"query": "民法典"}))
    finally:
        harness.datapro = original
    assert result["isError"] is True and "连接失败" in result["message"]


def test_cloud_prompt_keeps_deliverables_out_of_sandbox():
    from app.cloud_agent.runtime import system_prompt

    prompt = system_prompt()
    assert "不要在沙箱里生成要交给用户的 Word" in prompt and "把完整正文直接写在本次回答里" in prompt
    assert "mcp__oa__" not in prompt and "普通写入参数齐全即直接执行" in prompt  # OA 业务规则仍随云端一起生效

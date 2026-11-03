"""Agent Plan 的 Harness 服务（陶威 11-03：全面接入）：专业数据集、豆包搜索。

两者都用 Agent Plan 专属 Key 鉴权、用套餐 AFP 抵扣；由 OA 服务器代为调用，Key 不进入火山云沙箱，也不交给模型。
- 专业数据集：远程 MCP https://datapro.hqd.cn-beijing.volces.com/mcp，请求头 X-Agent-Plan-Key；服务端按问题自动路由到
  法律法规、司法案例、法律幻觉校验、企业工商、企业风险等数据库（在火山“专业数据集管理后台”可单独开关各类）。
- 豆包搜索：POST https://open.feedcoopapi.com/search_api/web_search，Bearer 专属 Key（官方 MCP 同一接口）。
"""
from __future__ import annotations

import json
from contextlib import AsyncExitStack

import httpx
from fastapi import HTTPException

DATAPRO_URL = "https://datapro.hqd.cn-beijing.volces.com/mcp"
SEARCH_URL = "https://open.feedcoopapi.com/search_api/web_search"
MAX_RESULT_CHARS = 60000

DATAPRO_TOOL = {"type": "function", "function": {
    "name": "volc_professional_data",
    "description": ("火山专业数据集（权威数据源）。按问题自动路由：元典法律法规库（法条原文、时效、效力级别）、元典司法案例库"
                    "（1.8 亿裁判文书，类案检索、裁判观点、案号查询）、法律幻觉校验（把含法条/案号引用的文书正文传进来，逐条核对真实性和时效）、"
                    "企业工商、企业风险（司法诉讼、行政处罚）、金融、宏观经济等。query 写清要查的对象和维度，用全称，不用简称；"
                    "做法律幻觉校验时 query 写“请校验以下文本中的法条和案例引用：”加正文（50～20000 字）。每次调用按次计费，不要重复查同一问题。"),
    "parameters": {"type": "object", "properties": {"query": {"type": "string", "minLength": 2, "maxLength": 20000}},
                   "required": ["query"], "additionalProperties": False}}}

SEARCH_TOOL = {"type": "function", "function": {
    "name": "doubao_search",
    "description": ("豆包联网搜索：查最新公开信息、新闻、政策公告、官网内容。Query 1～100 字；需要正文时 NeedContent=true；"
                    "只查官方来源时 AuthLevel=1；可用 Sites 限定站点（| 分隔），TimeRange 可选 OneDay/OneWeek/OneMonth/OneYear 或 YYYY-MM-DD..YYYY-MM-DD。"
                    "查法条、判例优先用 volc_professional_data。"),
    "parameters": {"type": "object", "properties": {
        "Query": {"type": "string", "minLength": 1, "maxLength": 100},
        "Count": {"type": "integer", "minimum": 1, "maximum": 20},
        "TimeRange": {"type": "string", "maxLength": 30},
        "AuthLevel": {"type": "integer", "enum": [0, 1]},
        "NeedContent": {"type": "boolean"},
        "Sites": {"type": "string", "maxLength": 1000}},
        "required": ["Query"], "additionalProperties": False}}}

NAMES = {DATAPRO_TOOL["function"]["name"], SEARCH_TOOL["function"]["name"]}


def schemas(*, datapro: bool, search: bool) -> list[dict]:
    return [item for item, on in ((DATAPRO_TOOL, datapro), (SEARCH_TOOL, search)) if on]


def _clip(value) -> dict:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return {"result": text[:MAX_RESULT_CHARS], "truncated": len(text) > MAX_RESULT_CHARS}


async def datapro(plan_key: str, arguments: dict) -> dict:
    query = arguments.get("query") if isinstance(arguments, dict) else None
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 20000:
        raise HTTPException(422, "专业数据集 query 需为 2～20000 字")
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(httpx2.AsyncClient(
            headers={"X-Agent-Plan-Key": plan_key}, timeout=httpx2.Timeout(15, read=90), follow_redirects=False, trust_env=False))
        streams = await stack.enter_async_context(streamable_http_client(DATAPRO_URL, http_client=client))
        session = await stack.enter_async_context(ClientSession(*streams[:2]))
        await session.initialize()
        tools = (await session.list_tools()).tools
        if not tools:
            raise HTTPException(502, "专业数据集没有返回可用工具")
        tool = next((item for item in tools if "search" in item.name.lower()), tools[0])
        required = (tool.input_schema or {}).get("required") or ["query"]
        result = await session.call_tool(tool.name, {required[0]: query.strip()})
    text = "\n".join(getattr(block, "text", "") for block in result.content if getattr(block, "type", "") == "text")
    if result.is_error:
        return {"isError": True, "message": "专业数据集查询失败", **_clip(text)}
    return _clip(text)


async def doubao_search(plan_key: str, arguments: dict, transport=None) -> dict:
    if not isinstance(arguments, dict) or not isinstance(arguments.get("Query"), str) or not 1 <= len(arguments["Query"].strip()) <= 100:
        raise HTTPException(422, "搜索词需为 1～100 字")
    body = {"Query": arguments["Query"].strip(), "SearchType": "web", "Count": int(arguments.get("Count") or 10)}
    if arguments.get("TimeRange"):
        body["TimeRange"] = str(arguments["TimeRange"])
    filters = {"NeedUrl": True}
    if arguments.get("AuthLevel") == 1:
        filters["AuthInfoLevel"] = 1
    if arguments.get("NeedContent"):
        filters["NeedContent"] = True
        body["ContentFormats"] = "text"
    if arguments.get("Sites"):
        filters["Sites"] = str(arguments["Sites"])
    body["Filter"] = filters
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, transport=transport) as client:
        response = await client.post(SEARCH_URL, json=body, headers={"Authorization": "Bearer " + plan_key,
                                                                      "X-Traffic-Tag": "ark_mcp_server_web_search"})
    if response.status_code >= 300:
        return {"isError": True, "message": f"豆包搜索失败（HTTP {response.status_code}）", "detail": response.text[:500]}
    return _clip(response.json())


class HarnessTools:
    """包在 OA 工具外面：Harness 工具由这里用 Agent Plan Key 调用，其余仍交给原工具集（含权限校验）。"""

    def __init__(self, delegate, plan_key: str):
        self.delegate, self.plan_key = delegate, plan_key

    async def execute(self, name, arguments):
        if name == DATAPRO_TOOL["function"]["name"]:
            return await datapro(self.plan_key, arguments)
        if name == SEARCH_TOOL["function"]["name"]:
            return await doubao_search(self.plan_key, arguments)
        return await self.delegate.execute(name, arguments)

    def __getattr__(self, item):  # 其余属性（如 pending_actions）透传给原工具集
        return getattr(self.delegate, item)

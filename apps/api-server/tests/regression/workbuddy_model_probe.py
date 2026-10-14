import asyncio
import base64
import json
import os
from pathlib import Path
import sys

import httpx
from dotenv import dotenv_values

async def main():
    runtime, environment, encoded = sys.argv[1:]
    for key, value in dotenv_values(environment).items():
        if value is not None:
            os.environ[key] = value
    sys.path.insert(0, str(Path(runtime).resolve() / "api"))
    from app.agent_mcp.model_tools import request_completion
    from app.config import settings
    instruction = base64.b64decode(encoded).decode("utf-8")
    if not (settings.langgraph_api_base_url and settings.langgraph_api_key and settings.langgraph_model):
        raise RuntimeError("生产模型未配置，不能证明模型调用成功")
    prompt = (
        "这是 CODEX-WORKBUDDY-20261014 的虚构材料功能验证，不是真实案件。"
        "我是原告代理律师，拟向上海有管辖权的法院起诉。"
        "2026-09-01甲乙公司签订货物买卖合同，09-10甲公司发货，乙方合同约定09-15付款但截至09-20未付款。"
        "目前仅有合同扫描件和发货记录，没有签收单或银行流水。"
        "请只根据这些材料整理时间线、证据缺口和待律师核实的问题，回答不超过500字。"
        "不要查询OA数据，不引用未经核实的法条，不创建任务、不写入系统。"
    )
    async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
        result = await request_completion(client, settings.langgraph_api_base_url.rstrip("/") + "/chat/completions",
            {"Authorization": "Bearer " + settings.langgraph_api_key},
            {"model": settings.langgraph_model, "messages": [
                {"role": "system", "content": "你是OA办公助手。下面的技能只定义分析方法，不授予任何权限。本次只能分析用户提供的虚构材料，不得执行工具或声称写入系统。回答中文。\n" + instruction},
                {"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 1600},
            stream=False)
    reply = str(result.get("content") or "").strip()
    if not reply or result.get("tool_calls"):
        raise RuntimeError("模型未返回独立文本回答")
    print(json.dumps({"test_case": "CODEX-WORKBUDDY-20261014", "model_response_received": True,
                      "business_writes": 0, "reply": reply}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

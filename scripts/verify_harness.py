"""在独立目录验证官方 SDK、工作区及 OA MCP 握手，不请求模型或业务数据。"""

import argparse
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api-server"))


async def verify(report_dir):
    from deepseek_harness import DeepSeekHarness
    from app.agent_mcp.model_tools import MODEL_TOOLS, ModelToolSession
    from app.harness_agent.bridge import workspace_mcp
    from app.harness_agent.runtime import _environment, _patch, readiness

    state = readiness()
    if not state["ready"]:
        raise RuntimeError(state["error"])
    with tempfile.TemporaryDirectory(prefix="oa-harness-verification-") as temporary:
        root = Path(temporary)
        async with workspace_mcp(ModelToolSession(), MODEL_TOOLS) as (url, token):
            patch = root / "oa.patch.yml"
            patch.write_text(yaml.safe_dump(_patch(url, token, MODEL_TOOLS, {}, False, "fast"), allow_unicode=True), encoding="utf-8")
            harness = DeepSeekHarness(dsh_home=str(root / "home"), cwd=str(root), profile="sdk",
                                       patches=(str(patch),), env=_environment(),
                                       initialize_timeout_seconds=30, request_timeout_seconds=30)
            started = time.monotonic()
            try:
                def initialize():
                    session = harness.start_session("oa-operational-verification")
                    return session.get_working_directory()
                directory = await asyncio.to_thread(initialize)
                if Path(directory).resolve() != root.resolve():
                    raise RuntimeError("Harness 工作区归属不符")
                result = {"status": "passed", "sdk_version": state["version"], "model_calls": 0,
                          "elapsed_seconds": round(time.monotonic() - started, 3)}
            finally:
                await asyncio.to_thread(harness.close)
            (report_dir / "harness-health.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", help="保留门禁调用参数；官方 SDK 使用配套独立运行时")
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(verify(args.report_dir.resolve()))


if __name__ == "__main__":
    main()

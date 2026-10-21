"""与现用 DSH 发布族对齐的官方插件目录，不在浏览时下载或执行插件。"""

from importlib.metadata import version

from fastapi import HTTPException

RELEASE = "0.2.1-rc.2"
SOURCE = "https://github.com/deepseek-ai/deepseek-harness"
ENTRIES = (
    ("codex", "@deepseek-ai/dsh-subagent-codex", "Codex 子智能体", "智能体协作",
     "将明确的任务交给 Codex 执行，使用其原生认证和设置。",
     "需要在服务器配置 Codex 原生认证；安装插件不会自动开通模型账号。", "subagent/subagent-codex"),
    ("claude-code", "@deepseek-ai/dsh-subagent-claude-code", "Claude Code 子智能体", "智能体协作",
     "通过官方 Agent SDK 将单个任务交给 Claude Code。",
     "需要在服务器配置 Claude Code 原生认证；安装插件不会自动开通模型账号。", "subagent/subagent-claude-code"),
    ("ralph", "@deepseek-ai/dsh-experimental-ralph-bundle", "Ralph 循环任务", "任务执行",
     "对用户明确要求重复执行的工作，使用新的智能体逐轮处理。",
     "实验性插件；仅在明确请求循环任务时使用，执行仍消耗模型额度。", "experimental/ralph-bundle"),
    ("terminal", "@deepseek-ai/dsh-experimental-terminal-bundle", "持久终端", "任务执行",
     "在多次工具调用之间保留 shell 进程，支持持续执行的终端任务。",
     "实验性插件；终端运行在服务器插件进程环境中，需要相应系统命令。", "experimental/terminal-bundle"),
    ("session-titles", "@deepseek-ai/dsh-experimental-session-titles-bundle", "会话标题更新", "会话增强",
     "随着新的用户提示进入，更新 DSH 原生会话标题。",
     "实验性插件；更新 DSH 会话元数据，OA 历史列表仍使用现有标题显示规则。", "experimental/session-titles-bundle"),
)


def catalog() -> dict:
    runtime = version("deepseek-harness-runtime-bin")
    reason = "" if runtime == "0.2.1rc2" else "此目录需要 DSH 0.2.1-rc.2，请先对齐运行版本"
    return {"runtime_version": runtime, "source": SOURCE, "items": [
        {"id": key, "name": name, "title": title, "category": category,
         "description": description, "requirements": requirements, "version": RELEASE,
         "author": "DeepSeek", "source": "https://www.npmjs.com/package/" + name + "/v/" + RELEASE,
         "spec": name + "@" + RELEASE, "unavailable_reason": reason,
         "experimental": path.startswith("experimental/")}
        for key, name, title, category, description, requirements, path in ENTRIES
    ]}


def install_spec(item_id: str) -> str:
    item = next((item for item in catalog()["items"] if item["id"] == item_id), None)
    if item is None:
        raise HTTPException(404, "插件目录中不存在此项目")
    if item["unavailable_reason"]:
        raise HTTPException(409, item["unavailable_reason"])
    return item["spec"]

# AI Agent 模块（AI Agent）

本目录是给学习和查看用的导航入口。AI Agent 相关代码分为两层：

- 业务侧 Agent API：`../apps/api-server/app/agent_mcp/`、`../apps/api-server/app/areas/personal_agent/`、`../apps/api-server/app/areas/agent_admin/`
- 独立运行时适配器：`../apps/deepseek-harness-host`

## 从哪里开始

- `../apps/api-server/app/agent_mcp/`：工具协议、工具调用和结果转换
- `../apps/api-server/app/areas/personal_agent/`：个人助手、会话、文件空间和技能
- `../apps/api-server/app/areas/agent_admin/`：管理员查看和配置 Agent
- `../apps/api-server/app/deepseek_harness.py`：DeepSeek Harness 后端适配
- `../apps/deepseek-harness-host/`：独立 Harness 进程、脚本和依赖

## 推荐学习顺序

1. 先看 `app/areas/personal_agent/router.py`，了解 API 入口
2. 再看 `response_runtime.py` 和 `service.py`，理解会话与执行流程
3. 接着看 `app/agent_mcp/`，理解工具如何被调用
4. 最后看 `deepseek-harness.py` 和 `deepseek-harness-host/`，理解运行时切换

AI Agent 的写入、审批和权限门禁必须沿现有业务链路执行，不要在前端伪造成功结果。

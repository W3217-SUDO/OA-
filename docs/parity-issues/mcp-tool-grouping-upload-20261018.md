# MCP 工具分组、同义词搜索与本地上传交接记录

## 本轮范围

本轮处理的是智能体 MCP 工具发现和调用链的新增能力：上传、附件、文件、导入等同义词搜索；查询、创建、修改、删除、审批、下载、导出、分配等常用动作的中文同义词搜索；工具按业务域分组；调用前展示 `path`、`query`、`body`、`files` 参数组及必填参数；支持先上传本地文件，再把得到的附件 ID 交给具体业务接口。

本轮属于 MCP 运行时能力增强，旧系统没有对应的智能体工具发现和调用链实现，旧系统代码不适用。本轮不以旧系统页面或旧接口实现替代 MCP 运行时契约。

## 根因与实现

- 原搜索将 824 个工具平铺评分，中文短词会被单字拆分，上传类接口可能被下载、查询或其他文件接口挤出结果。
- 搜索结果没有业务分组，也没有把每个接口的参数组和必填项直接告诉模型，导致模型可能在未完成参数收集时直接调用接口。
- multipart 工具原先只允许引用已有 `FileAttachment ID`，无法从智能体入口直接接收本地文件。
- 搜索目录现在增加上传、附件、文件、导入及对应英文词的同义词和动作意图加权；目录和模型搜索结果按业务域汇总。
- 工具公开描述补充 `parameter_groups`、`required_parameters` 和原始 `inputSchema`，调用仍严格按原路由校验。
- 新增 `/api/v1/agent-tools/upload` multipart 入口，先复用原附件存储逻辑生成真实 `FileAttachment`，再返回下一步 MCP `files` 参数。业务关联字段仍需由对应业务工具在人工确认后办理，不能通过上传入口绕过权限和确认门禁。

## 变更文件

- `apps/api-server/app/agent_mcp/catalog.py`
- `apps/api-server/app/agent_mcp/model_context.py`
- `apps/api-server/app/agent_mcp/service.py`
- `apps/api-server/app/agent_mcp/model_tools.py`
- `apps/api-server/app/agent_mcp/gateway.py`
- `apps/api-server/app/agent_mcp/router.py`
- `apps/api-server/app/areas/personal_agent/service.py`
- `apps/admin-web/src/personal-agent/usePersonalWorkspace.ts`
- `apps/api-server/tests/regression/agent_mcp_upload_contract_test.py`

## 本地验证

已通过：

- MCP 上传、目录分组、参数展示及动作同义词契约：5 项测试、11 个子场景；
- MCP 模型工具循环及附件读取既有回归：合计 37 passed、32 subtests passed；
- 相关 Python 文件 `py_compile`；
- 本轮测试文件 `git diff --check`。

契约覆盖真实目录工具，包括客户查询/创建/修改/删除、案件审批、附件下载、案件导出、回款分配，以及通用附件、财务票据上传和回款导入。未写入生产业务数据。

## 源码门禁与发布状态

- 本轮尚未执行 `git add`、`git commit` 或部署；当前状态为本地候选，待主线程统一收敛、精确暂存和提交。
- 完整 source 门禁仍有既有 `finance splitRuntime` 失败项，不能将本轮 MCP 定向测试通过等同于完整 source 门禁通过；该既有失败需单独修复或按门禁记录阻断。
- 当前未部署到测试服务器或生产服务器，未重启服务，未执行线上健康检查和目标接口验收。
- 后续部署前必须先完成完整源码门禁、前端生产构建、后端检查和直接上传/业务调用接口验收；部署后分别检查 `/health`、目录分组、上传入口和一个需要 `files` 参数的真实业务工具。

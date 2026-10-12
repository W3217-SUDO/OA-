# OA 环境参考

这些值可能因端口、进程或发布版本变化而改变。每次执行前先从当前工作区和运行进程确认，不得仅凭记忆使用。

## 新系统

- 工作区根目录：`C:\Users\Administrator\Desktop\OA系统`
- 新系统仓库：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\本地开发`
- 前端源码：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\本地开发\apps\admin-web`
- 后端源码：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\本地开发\apps\api-server`
- 本地 SQLite：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\本地开发\apps\api-server\legal_platform.db`
- 本地前端：端口会变化，常见地址为 `http://127.0.0.1:5182`
- 本地 API：端口会变化，常见地址为 `http://127.0.0.1:8000/api/v1`
- 线上前端：`http://150.158.3.104:8089`

## 旧系统

- 旧系统源码根目录：`C:\Users\Administrator\Desktop\OA系统\legacy-gdcrm-101-local-20260812\source`
- 旧系统 Web 源码：`C:\Users\Administrator\Desktop\OA系统\legacy-gdcrm-101-local-20260812\source\GD.CRM.WEB.VIP`
- 本地旧系统：常见地址为 `http://127.0.0.1:8091`
- 旧系统仅用于读取界面、源码和业务逻辑。不得修改、提交、部署或清理旧系统数据。

## 问题台账与证据

- 问题目录：`C:\Users\Administrator\Desktop\OA系统\问题`
- 验收证据目录：`C:\Users\Administrator\Desktop\OA系统\问题\_返工验收`
- 证据文件名必须包含工作表/日期、行号和阶段，例如：`8.18_第8行_local_accepted.png`。

## 阅读旧系统的方法

1. 尽量在 `8091` 执行同一业务流程，记录字段、顺序、链接、按钮、默认值、校验和角色权限。
2. 在 `GD.CRM.WEB.VIP` 中使用页面中文、路由、按钮文字、字段名和状态文字搜索 `.cshtml`、JavaScript、Controller 和 AJAX 地址。
3. 从页面动作追踪到 Controller、Service、Repository、实体、SQL 或存储过程。
4. 确认权限、校验、状态变化、数据库写入、日志、提醒、任务、通知、附件和下游页面。
5. 无法登录旧系统时使用用户截图和旧源码；仍无法确定业务行为时再向用户确认。

## 阅读新系统的方法

1. 前端从 `apps\admin-web\src` 中按页面 id、可见文字、路由、标签和 API 名称搜索。
2. 后端从 `apps\api-server` 中按 API 路径、模型、表名、状态值和服务函数搜索。
3. 编辑前读完整的请求、响应、权限和持久化逻辑。
4. 表结构先看模型、初始化和迁移，再用只读 SQL 核对本地数据。
5. 涉及关联业务时检查工作流、通知、附件、审计、任务、提醒、审批、计数器、归属和角色权限表。
6. 新系统表结构不能表达旧系统业务时，应完善模型和迁移，不得在前端伪造字段。

## 代码与数据边界

- 只修改新系统。
- 先读取仓库 `AGENTS.md`、git 状态、运行进程和部署说明。
- 不覆盖用户或其他任务的无关改动。
- 测试数据使用 `CODEX-<批次>-<行号>-` 前缀，只删除当前验收创建的数据和依赖记录。

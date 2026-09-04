# VIP 任务旧系统核对与验收记录

## 范围与证据

- 任务：事务中心新增独立 VIP 任务模块；需要任务、节点和消息/通知的真实数据闭环。
- 旧系统证据：`GD.CRM.WEB/Areas/TP/Controllers/VipTaskController.cs`、`VipTaskNodeController.cs`、`VipTaskMessageController.cs`，以及 `Views/VipTask`、`Views/VipTaskNode`、`Views/VipTaskMessage`。
- 新系统实现：已新增 `VipTaskCenterPage.tsx`、`vip-tasks` 事务中心子菜单、独立 `VipTask` / `VipTaskNode` / `VipTaskMessage` 数据模型与 12 条 `/api/v1/vip-tasks` 接口；普通任务仍使用原有 `/tasks`，两套数据不混存。
- CodeGraph：本工作树 `codegraph status` 返回 Not initialized；主线程明确不允许自行初始化，故本记录以定向源码检索补足。该定位结论不代替接口和浏览器验收。

## 旧系统功能矩阵（对照范围）

`VipTaskController` 有 16 个 Action，均受类级 `CheckUserLogin` 保护。下表的第三列是本轮需求对应的核对项，不表示逐 Action 复刻旧 URL、旧 PageId 或旧案件批量创建；旧消息附件、`caseNos` 一案一任务和两个兼容删除入口均保留为后续扩展参考，不纳入本轮完成断言。

| Action | 旧系统实际语义 | 本轮对应核对项 |
| --- | --- | --- |
| `TaskList` | 依据 PageId 初始化个人发起、负责人待处理、协作处理中三类列表；默认 15 条/页。 | VIP 左侧菜单入口、个人/部门/公司范围及分页真实生效。 |
| `TaskDetail` | 读取任务及当前节点，并生成本次消息 GUID。 | 详情同时返回 VIP 任务、节点和消息。 |
| `TaskSearchList` | 按搜索条件分页查询任务。 | 客户、状态、优先级过滤由服务端执行。 |
| `Create` / `TaskCreate` | 初始化任务、节点、消息 GUID 和开始时间。 | 新建 VIP 任务可持久化 VIP 标识及首节点。 |
| `CreateUpdate` | 校验结束时间不得早于开始时间；多案号逗号拆分后逐案创建。 | 时间校验、客户/案件关联与原子失败处理可验证。 |
| `Checked` | 验收任务。 | 合法状态才可验收；写入审计/消息。 |
| `Finished` | 办理人完成任务。 | 合法状态才可完成；节点和任务状态同步。 |
| `Rejected` | 拒绝任务。 | 拒绝原因和权限真实校验。 |
| `Stoped` | 停止任务。 | 停止状态和后续阻断真实生效。 |
| `ReOpen` | 将终止/拒绝/完成工作重新打开。 | 可重开且产生可追溯节点。 |
| `TaskDelete` / `Delete` | 删除任务（两个兼容入口）。 | 删除仅作用于有权限且可删除的 VIP 任务。 |
| `Process` | 将节点置为处理中。 | 办理人和节点状态机受服务端控制。 |
| `GetNewMessageTasks` | 取未读任务集合。 | VIP 未读聚合与普通任务隔离或可明确区分。 |
| `GetTaskNotificationMessages` | 取当前登录人的任务通知。 | 按收件人返回 VIP 通知。 |

`VipTaskNodeController`：`Create` 从既有任务派生一个新的节点/消息 GUID 并设置开始时间；`TaskNodeCreate` 在结束时间早于开始时间时拒绝，否则创建节点。节点状态在旧页面可见为待处理、进行中、完成、停止。

`VipTaskMessageController`：`TaskMeesages` 返回消息局部视图；`TaskNewMeesages` 返回刷新数据；`TaskMessageCreate` 持久化任务 GUID、节点 GUID、消息 GUID、发送时间、内容和消息类型；`TaskMeesageMarkRead`、`TaskMeesageMarkUnRead` 按任务和消息标记已读状态。旧视图仅向当前通知接收人显示读/未读按钮，且支持消息附件显示。

旧任务详情按状态和主体显示操作：发起人可重开/验收/停止，负责人可开始、完成、停止及新建节点；页面还显示任务编号、负责人、发起人、关联案件、截止时间、任务状态、关联人、消息和附件。Controller 只做登录门禁，细粒度岗位授权需由新系统在接口层明确实现，不能仅依赖前端隐藏。

## 当前实现验收台账

- [代码与 API 已验证] `vip-tasks` 是事务中心的独立菜单和页面；独立表/接口与普通 `/tasks` 分离。
- [代码与 API 已验证] VIP 任务 CRUD、客户/状态/优先级筛选、日期逆序 422、节点 CRUD 与节点未完成时任务完成 409。
- [代码与 API 已验证] 消息可关联节点，收件人限制为 VIP 参与人，支持按本人未读查询和标记已读；旁观者访问/修改和非参与人收件人均被 403 阻断。
- [已清理] 隔离测试仅创建 `CODEX-VIP-*` 数据；任务、节点、消息和两个临时 SQLite 数据库均已删除并回查无残留。
- [页面未证明] 浏览器客户端阻断本地页访问，尚未完成菜单点击、表单输入、刷新回显和前端错误提示的浏览器验收。

## 本轮环境结论

- 隔离 API 已在工作树 `127.0.0.1:8019` 成功启动并完成 HTTP 冒烟，随后主动停止；它只使用临时 SQLite 数据库，不接触现有业务库。
- 完整 `verify-local.ps1` 仍在预检因 `apps/api-server/.venv` 缺失而停止。前端已用可用的 `npx.cmd tsc -b` 与 `npx.cmd vite build --configLoader runner` 完成定向生产构建。
- 浏览器自动化会话可以建立，但对本地健康页的受控访问被 `ERR_BLOCKED_BY_CLIENT` 阻止；创建的标签已关闭。因此 API 已验证，页面浏览器验收仍未证明。

## 本轮命令记录

- `powershell -ExecutionPolicy Bypass -File .\\scripts\\verify-local.ps1`：未通过预检，原因是 `apps/api-server/.venv` 缺失；脚本未进入构建、API 冒烟或服务健康步骤。
- `python -m py_compile scripts\\smoke-api.py`：通过，包含新增 `--group vip_tasks` 的受控 API 冒烟路径。
- `python .\\scripts\\audit-menu-coverage.py`：在既有、与 VIP 无关的 `CaseCenterPage.tsx:3011` 日期格式静态守卫处中断，尚未运行到 VIP 覆盖断言；需在该既有失败修复或隔离后重跑。
- `python .\\scripts\\audit-client-api-coverage.py`：未通过，现有非 VIP 调用匹配器未识别 `CaseCenterPage.tsx:3091` 的 PDF 预览页 URL、以及 `InvestigationCenterPage.tsx:1605/1625` 的调查线索工作区 URL；VIP 请求不在该三条失败项内。该全局存量审计失败不影响上述 VIP HTTP 冒烟结论。
- `PYTHONPATH=apps/api-server python apps/api-server/test_vip_task_smoke.py`：通过。该隔离测试覆盖管理员/参与人可见范围、旁观者 403、未完成节点阻断任务完成（409）、节点完成后任务完成、非参与人收件人阻断（403），以及任务删除后的根/节点/消息零行；临时 SQLite 数据库及 journal 均已清理。
- 临时 HTTP API：以工作树内 `vip-http-smoke.db` 启动 `127.0.0.1:8019`，再运行 `API_BASE_URL=http://127.0.0.1:8019 python scripts/smoke-api.py --group vip_tasks` 通过。覆盖日期逆序 422、创建、客户/状态/优先级筛选、节点状态、未完成节点完成阻断 409、节点消息、已读、任务完成与删除；临时任务和临时数据库已精确清理。
- 客户端/API 静态覆盖已写入 `scripts/audit-menu-coverage.py`：要求声明 `vip-tasks` 菜单和页面、独立根/节点/消息模型及级联关系、CRUD 与状态机接口、客户/状态/优先级筛选、前端真实 API 调用、优先级枚举一致和 VIP 冒烟分组。完整菜单审计仍受上述既有日期守卫阻断。
- 前端定向构建：在 `apps/admin-web` 执行 `npx.cmd tsc -b`、`npx.cmd vite build --configLoader runner`、`git diff --check` 均通过；Vite 7.3.6 转换 5646 个模块、耗时 11.38 秒，产物包含 `VipTaskCenterPage-Bw4UPOfC.js`。标准 `npm.cmd run build` 的默认 Vite 配置打包器会读取工作树祖目录，受到沙箱目录读取限制而报 `Cannot read directory` / `Could not resolve vite.config.js`；`--configLoader runner` 绕开该配置加载限制，未跳过 TypeScript 或 Vite 打包。`node appMenuExpandedDefaultsParity.test.mjs` 与 `node appSidebarPermissionParity.test.mjs` 共 5/5 通过。
- 浏览器页面验收：未证明。虽然自动化浏览器会话可以建立，但访问本地健康页被浏览器客户端以 `ERR_BLOCKED_BY_CLIENT` 拦截；本轮没有可操作的前端页面标签。已停止隔离 API 并回收浏览器标签，未把 API 测试当作页面验收。

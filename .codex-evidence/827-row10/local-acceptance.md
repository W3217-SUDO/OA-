# 8.27 第10行本地验收记录

## 运行实例一致性

- 前端：`http://127.0.0.1:5300/`，命令为当前工作树 `apps/admin-web` 下执行的 `vite --host 127.0.0.1 --port 5300 --strictPort --mode staging`；验收页面路由分别为 `case-new-criminal`、`case-new-administrative`、`case-new-counsel`、`case-new-arbitration`。
- API：`http://127.0.0.1:8012/api/v1`，命令为当前工作树 `apps/api-server` 下执行的 `uvicorn.run('app.main:app', host='127.0.0.1', port=8012)`。
- 源码根目录：`C:\Users\Administrator\Desktop\OA系统\.codex-worktrees\827-row10`，分支 `codex/827-row10`。
- 验收数据库：隔离 SQLite `C:\codex-row10-rebase\legal_platform.db`；浏览器前先用前端代理登录成功、监听进程命令行和 API 直连确认 `5300` 到达 `8012`，API 返回任务合同 A/B 共 2 条。rebase 前或错误代理产生的页面结果全部作废，四张证据图均已由 rebase 后实例覆盖。
- 登录角色：任务专用 `admin` 角色账号 `codex-827-row10`；数据前缀 `CODEX-8.27-10-`。

## 浏览器验收

四个入口均执行同一真实操作：进入指定新建路由，确认未选客户时合同控件禁用；选择客户后控件解锁；打开合同下拉，只出现该客户的审批通过合同；选择合同后合同号、案源人和案件名称联动回填。

| 入口 | 客户 | 可见任务合同 | 不应出现的另一客户合同 | 证据 |
| --- | --- | --- | --- | --- |
| 刑事案件 | `CODEX-8.27-10-CUSTOMER-A` | A=1 | B=0 | `browser-criminal-contract-selected.png` |
| 行政案件及国家赔偿 | `CODEX-8.27-10-CUSTOMER-B` | B=1 | A=0 | `browser-administrative-contract-selected.png` |
| 法律顾问 | `CODEX-8.27-10-CUSTOMER-A` | A=1 | B=0 | `browser-counsel-contract-selected.png` |
| 仲裁 | `CODEX-8.27-10-CUSTOMER-B` | B=1 | A=0 | `browser-arbitration-contract-selected.png` |

失败/防错路径：仲裁入口已选客户 B 和合同 B 后切换为客户 A，页面立即清空合同、案源人和案件名称，合同控件保持可用并等待重新选择，未保留跨客户合同。

## 测试与构建

- `node --test src\caseContractPrefill.test.mjs src\caseContractSelectionRow10.test.mjs`：2 个测试通过。
- 项目 API venv 执行 `python -m unittest case_create_route_contract_test.py`：1 个测试通过，覆盖创建成功、客户不一致拒绝、类型菜单权限拒绝及持久化/清理。
- `python -m py_compile app\main.py case_create_route_contract_test.py`：通过。
- rebase `origin/dev@a3cfe02` 后再次运行以上聚焦测试，结果均通过。
- `npm.cmd run build`：rebase 后生产构建通过；沿用上游活动基线包版本 `1.0.275`，本任务未改正式版本。
- `git diff --check`：通过；CodeGraph 已同步。
- 浏览器错误日志只有隔离空库下 `NotificationCenter` 的 428 和既有 Ant Design 弃用警告；四个案件新建路由、合同接口和联动操作均正常，未出现案件中心数据加载错误。

## 测试数据清理

- rebase 后隔离数据库记录 ID `1,2,3,4` 及账号 `codex-827-row10` 已删除；前缀记录、账号、工作流事件剩余数均为 0；隔离数据库目录随后删除。
- 工作树本地数据库中早期准备的记录 ID `27,28,29,30` 和同名账号也已精确删除；前缀记录和账号剩余数均为 0。
- 所有本任务启动的验收 API/前端监听进程已停止。
- 原始 Excel、旧系统和线上数据库未修改；Excel `H10` 仍为空。

## 数据库补丁

无。现有后端已具备合同可见性、状态、客户一致性、菜单权限及案件关联字段的服务端校验与持久化；rebase 时上游第9行已包含共享的客户合同过滤、非民事路由解锁和切换客户清空联动，本行保留该实现并补充第10行四入口回归、后端测试夹具依赖表和独立验收证据。

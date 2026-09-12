# OA 主动对齐审计交接（2026-09-12）

## 2026-09-13 新证据补充

用户随后明确 GD/SH 是同一 OA 改名；不将下述哈希差异设为接续阻断。已继续建立 `docs/parity-issues/civil-case-detail-source-map-20260913.md`，按截图中的案件详情逐项定位主要前端与服务链，尚未逐按钮验收。

用户已新增服务层反编译源码，详见 `docs/parity-issues/decompiled-source-readiness-20260913.md`。下文“服务程序集尚未读取”是交接当时状态，不能再视为永久缺失；当前已抽查客户服务及 DAO。不过该反编译 README 来源是 GD.CRM.WEB/bin，与 SH.CRM.WEB/bin 四个核心 DLL 的哈希均不相同。后续先确认目标旧站版本，再把对应服务/SQL纳入全量审计。9 月 13 日本轮仅可行性评估，没有改业务代码或重跑下文测试。

## 0. 接手先读

用户最新指令：**“你把你这份工作 交接文档写好给我 我要换个智能体继续跑”**。本任务已停止新增排查；最后启动的测试已结束，没有待接管的测试会话。不要把交接理解成全部完成或发布授权。

目标保持不变：修正审计工具误报，按模块主动寻找并修复旧新系统的真实功能差异，覆盖菜单、路由、权限、数据范围、按钮、流程、异常及前端对应。用户问题表只是发现方法样本，不是审计范围上限。

**第一优先：收尾客户回收站“进入公海”的两项失败测试，详见第 3 节。不要从头重做已完成审计，也不要直接部署。**

## 1. 权威工作位置与 Git

- 唯一当前工作树：`C:\Users\Administrator\.codex\worktrees\45fd\9.2-batch4-task-center`。
- 实查 HEAD：`3533b8f07d5e71ada22ab173ba19badf5d0efdd4`，提交标题 `chore(release): v1.1.108`。
- `git branch --show-current` 为空：**当前是 detached HEAD，不是已切到 dev**。本批修改全部未提交、未推送；接手必须先保留 dirty worktree，不要直接 checkout/reset 或覆盖。
- GitHub remote 名 `github`：`https://github.com/W3217-SUDO/OA-.git`；`origin` 是服务器 SSH Git remote。本轮未 fetch，不能宣称已基于 GitHub 最新代码。
- 版本仍为前端 `1.1.108`；本轮没有递增版本、服务器同步、重启、部署或线上验收。
- 新智能体必须使用本工作树；在另一目录仅 checkout HEAD 会遗漏所有未提交修复和未跟踪测试/MD。
- 不属于本轮成果、不得删除或提交：`NUL`、`audit-last.txt`、`batch4a-prompt.txt`、`batch4b-prompt.txt`、`evidence/online-oa-20260912/`。它们已有且未核实归属。

## 2. 已完成的本地工作

以下测试数来自本轮实际运行及独立问题记录，均不是浏览器/线上验收；涉及身份的隔离 API 测试 override 了 current_identity，不能证明真实登录认证链。

| 项目 | 具体改动 | 当前证据与局限 |
|---|---|---|
| 审计工具 | 菜单审计改用已拆分源码；API 审计识别 FastAPI 分片注册、工厂重导出和动态 URL | 菜单审计通过，822 处前端调用匹配，8 项解析测试通过；静态 OK 不是功能验收 |
| 公司案件多选删除 | 完整选择集批量请求、整批预检与一次提交、失败回滚、任务附件清理、顾问案件删除后刷新 | 后端 10 项和前端 9 项通过；未验证 PostgreSQL 并发锁/浏览器；删除角色限制另有候选，未放宽 |
| 客户共享名单保存 | 从旧名单并集改为替换当前完整选择，支持显式空列表取消共享，保留人员/状态校验并记录前后名单 | 前期相关 19 项通过，最近共享后端 7 项重跑通过；未浏览器验收；不修改独立 shared_to 授权 |
| 最近联系/最近更新 | 加入旧 AddMonths(-1) 日历月窗口，处理月末和时区，先过滤再算总数/分页，统一排序时间 | 6 项真实 HTTP+内存 SQLite 测试通过；服务时区和旧库无时区字符串仍有待核实项 |
| 回收站进入公海 | release_customer 不再拒绝所有已回收记录 | 最新未全部通过，见下一节；不得标记完成 |

最近一次生产构建：TypeScript + Vite 通过，版本 1.1.108，有已有资源块过大警告。这次构建在“回收站进入公海”的最后一行后端改动之前；其后没有前端生产源码改动，但最终批次仍应统一复跑验证。

其他已通过：相关 Python 编译、git diff --check、CodeGraph sync。完整 `scripts/verify-local.ps1` 曾因缺少 `apps/api-server/.venv/Scripts/python.exe` 未通过；不能用系统 Python 定向测试替代“完整流水线通过”。

## 3. 当前准确断点：回收站进入公海

### 入口与根因

- 前端：客户管理 -> 个人/部门/公司回收站 -> 更多操作 -> 进入公海。
- route：`customer-recycle`、`customer-dept-recycle`、`customer-company-recycle`。
- `apps/admin-web/src/crm/CustomerCenterPage.tsx`：originalActionItems -> runOriginalAction -> releaseCustomer -> action -> POST `/customers/{id}/release` -> load。
- 旧 `CustomerList.cshtml` 的 PageId 6001002/6001004/6001010 均有 InOpen；旧 `CRM.Customer.js:164` 直接 POST CustomerOpen，不先恢复；旧控制器调用 OpenCustomer，服务程序集内部尚未读取。
- 现有 `scripts/smoke-api.py:890、990、1183` 同样明确要求回收站进入公海成功。
- 新 `apps/api-server/app/areas/crm/router.py:release_customer` 原先同时拒绝公海/已回收，与所有三个入口矛盾。
- 修改前测试已实际失败，返回 HTTP 200 + IsSuccess=false；本轮仅将拒绝条件改为已经公海，其他归属/共享/日志/行锁/事务不改。

### 最新测试结果，必须如实接续

命令在 `apps/api-server`：

```powershell
python -m unittest customer_recycle_release_test customer_backend_alignment_d6_contract_test.CustomerBackendAlignmentD6Contract.test_release_accepts_migrated_and_recycled_status_but_rejects_public customer_backend_alignment_d6_contract_test.CustomerBackendAlignmentD6Contract.test_recycle_blocks_customers_with_linked_contracts_or_cases -q
```

结果：**7 项，5 通过、2 失败，退出码 1**；会话 62416 已终止，无需再轮询或恢复。

失败用例：
- `test_personal_recycle_release_and_claim`
- `test_department_recycle_release_and_claim`

失败位置均为 `customer_recycle_release_test.py:86`。两条都已经通过进入公海、回收站列表消失、公海列表出现、日志检查和重复释放拒绝，随后测试错误地把“对公海再 restore”的所有角色响应都期待成 HTTP 200。

已读源码的原因：`core/permissions.py:_require_record_owner_or_manager` 对非 admin 且无 `_page_menu_capability` 的公海修改先抛 403；`core/legacy_sync.py:_legacy_customer_business_failure_response` 仅把 409/422 转成 HTTP 200 + IsSuccess=false，403 原样传播。因此当前夹具中的个人/部门角色收到 403，管理员收到状态冲突的业务失败。**不要为了测试全绿删除生产的既有保护。**

接手动作：根据该实际响应合同分别断言 restore 的 403 与业务失败，继续确保拒绝后客户/日志完全不变，再重跑整个链。个人/部门用例在失败点之后的拾回步骤本轮尚未跑到；不能因公司用例通过就声称三条都通过。还应补真实菜单能力身份路径；当前 override 身份不含 `_page_menu_capability`，不代表线上认证所有路径。

前端 `node --test customerRecycleRelease.test.mjs`：**6/6 通过**，执行实际 TypeScript initializer 转译出的菜单和 action，覆盖三入口、成功刷新、业务失败/网络失败保留选择。不是浏览器测试。

本轮已修正 D6 旧测试的错误断言：测试名从 rejects_public_or_recycled 改为 accepts_migrated_and_recycled_status_but_rejects_public。该项与关联合同/案件阻止删除的回归已通过。

## 4. 文件归属与集成清单

根目录均为第 1 节当前工作树，以下路径可用于逐项 diff，不得 `git add .`：

### 生产代码
- `apps/api-server/app/areas/legal/router.py`：批量删除及清理。
- `apps/api-server/app/main.py`：追加 legal route slice 141:142，不移动已有片段边界。
- `apps/api-server/app/models_shared.py`：批量删除输入与共享列表输入校验。
- `apps/admin-web/src/legal/CaseCenterPage.tsx`、`src/legal/services/workflowActions.tsx`：完整选择与批量 handler。
- `apps/api-server/app/areas/crm/router.py`：共享、最近时间窗口、本次回收站释放。
- `apps/api-server/app/core/formatters.py`：解析时间增加可选 naive_timezone，未传参数时保持默认行为。
- `apps/admin-web/src/crm/CustomerCenterPage.tsx`、`src/crm/CustomerModals.tsx`、`src/customerUiBatchI14.mjs`：共享保存。

### 新增测试
- API：`case_batch_delete_test.py`、`customer_share_replacement_test.py`、`customer_recent_time_window_test.py`、`customer_recycle_release_test.py`。
- 前端：`companyCaseBatchDelete.test.mjs`、`customerShareReplacement.test.mjs`、`customerRecycleRelease.test.mjs`。
- 工具：`scripts/test_audit_client_api_coverage.py`。

### 已有测试/工具调整
- `scripts/audit-menu-coverage.py`、`scripts/audit-client-api-coverage.py`。
- 前端 `companyCaseDeleteRow19.test.mjs`、`companyCaseListToolbarRow3.test.mjs`、`customerShareObjectParityI10.test.mjs`、`customerUiBatchI14.test.mjs`。
- 前端 `investigationClueMineIsolationRow3.test.mjs`、`investigationMyClueScopeRow22.test.mjs`、`taskMyCreatedA.test.mjs`：真实源码路径/语义修正，不代表新加业务功能。
- API `customer_backend_alignment_d6_contract_test.py`：回收站释放预期纠正。
- `docs/parity-issues/` 内独立记录与索引，以及 `docs/迁移交接与当前状态.md`、本交接文档。

## 5. 旧系统权威来源与不要重犯的判断

完整旧 Web 源码：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\旧系统归档源码\SH.CRM.WEB`，C# MVC + Razor + JavaScript。业务服务部分是程序集引用，不能把控制器当作完整服务证据；不要把零散 legacy-system-local 补丁目录当作完整旧项目。

- 本轮曾推断要新增通用任务列表“新建”按钮，后发现旧入口被隐藏/注释、独立创建模板不等于列表有效入口，已撤回，不算修复成果。
- 曾把个人线索与个人调查任务的管理员范围混淆，已撤回取消 owner 筛选的改动。个人语义必须单独核实，不能机械扩大全所数据。
- 旧共享客户只读动作与用户后续“菜单开放即动作开放”要求存在有意差异，保留新功能，不能复原旧角色限制。
- 公司客户状态范围、最近更新归属/修改人语义尚有需求证据待核实，不擅改。
- 每发现真实问题立即独立 MD，必须指明前端菜单、route、按钮/字段、组件/handler、旧新差异、改动、测试、当前状态及下一步。静态源码或空页面不作为完整验收。

## 6. 环境与执行边界

- 必须先读 `AGENTS.md`、README、功能清单、交接记录和 skills：`oa-parity-audit`、`problem-remediation`、`vibehub`（均在 `C:\Users\Administrator\.codex\skills`）。有冲突以用户最新指令为准。
- 当前主动审计只本地修改/验证，未获本批发布授权。不要因老 AGENTS 的自动部署条款去线上构建或发布。
- 禁止 IAB/browser-use；需要浏览器只能 Chrome。当前阶段未打开新浏览器标签；不要清理其他任务标签。页面验收尚未做。
- 不新建大量代理/会话；用户此刻要换智能体接续，不是要求再派工。
- 新旧线上系统/原有业务数据不写。仅独立内存 SQLite 和本任务临时 CODEX 测试文件允许写，测试 teardown 清理；不要运行原 smoke-api 对共享库的跨轮次 SMOKE 清理。
- 系统 Python 可用，API 依赖能导入。默认 `.venv` 缺失是完整验证脚本阻断，另行修复或建立等价的隔离流程并如实记录。
- 修改前 `codegraph status/sync/explore`，修改后 `codegraph sync`；必要时 rg 定向补查。图谱非业务证据。
- 发布如获授权：先核对本地与 dev/GitHub 最新状态并非破坏集成，本地构建，按 oa-fast-deploy 核对实际 systemd 目录；不能把本地 1.1.108 当线上当前版本。不在服务器全库备份，涉及数据库只按用户要求备份改动表且避免服务器占空间。

## 7. 接续验证与下一阶段

1. 核对 cwd、git status、HEAD 和本文件，确认未提交文件都在。不要重启任何已结束测试。
2. 收尾第 3 节两项预期断言及尚未走到的拾回步骤，保留权限/状态保护；补菜单能力身份路径，更新独立问题记录。
3. 在 API 目录执行隔离测试 `python -m unittest customer_recent_time_window_test customer_share_replacement_test customer_recycle_release_test case_batch_delete_test -q`，并运行第 3 节 D6 定向测试。每项失败查清根因，不盲改断言。
4. 在前端目录执行 `node --test companyCaseBatchDelete.test.mjs customerShareReplacement.test.mjs customerRecycleRelease.test.mjs`；前述测试不等于全部历史前端测试通过。
5. 根目录运行 `python scripts/audit-menu-coverage.py`、`python scripts/audit-client-api-coverage.py`；统一前端 `npm.cmd run build`、Python 编译、diff 检查、CodeGraph sync。原始完整 verify-local 阻断仍需如实说明。
6. 更新问题 MD、总索引、CRM 十页面矩阵。然后继续按 `legacy-area-baseline.md` 展开其他模块，不局限 CRM；当前只完成区域文件盘点，不是全系统业务对齐。
7. 仍未证明：真实菜单/登录身份链、浏览器、PostgreSQL 并发和历史时区、公司案件删除角色候选、CRM 其他动作/数据范围、全系统各模块逐按钮及关联闭环。未部署、未推送，目标继续保持未完成。

## 8. 可直接交给新智能体的接续指令

> 请先读取当前工作树 docs/AUDIT-HANDOFF-2026-09-12.md 和 docs/parity-issues/README.md，核对 detached HEAD 与未提交文件。不要重新开始，不要部署，不要创建并行任务。先收尾客户回收站进入公海的两项失败测试，区分业务失败 HTTP 200 与权限拒绝 403，并补齐后续拾回和身份路径验证。然后继续全系统旧新功能主动审计和本地修复；每个问题写独立 MD，明确页面/按钮/字段、新旧证据、整改及验证状态。仅使用 Chrome，不用内置浏览器，不修改现有业务数据。

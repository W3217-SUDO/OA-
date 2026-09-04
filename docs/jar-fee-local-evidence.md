# JAR 交案费管理整改定位

## 1. 清单原文
- 工作簿：不适用（当前为用户直接任务，不是 Excel 问题行）。
- 工作表：不适用。
- 行号：不适用。
- 原始问题（逐字）：【任务】财务中心-JAR交案费管理；【背景】旧系统FAM有JARController（6个Action）+ JARFileCenterController，是一种独立的应收费用类型（交案费）。新系统财务中心完全没有JAR概念。
- 补充说明（逐字）：功能包括 JAR交案费列表、新增/编辑/删除交案费、交案费状态管理、交案费文件管理（JARFileCenter）、支持导出；后端新增数据结构、增删改查接口、状态变更接口、文件上传下载接口、权限校验 + 操作日志；保持与财务中心其他模块风格一致；完成后本地构建验证无编译错误。
- 返工意见（逐字）：无。
- 当前状态：本地实现完成，独立验收中；浏览器和完整 API 冒烟尚未证明。

## 2. 截图分析
- 无截图附件；不以截图作为本次范围或验收依据。

## 3. 旧系统实现
- 入口、角色和数据状态：`JARController.List`（PageId `5001002001`）列出合同并可“新增回款”；`PaymentList` 根据 PageId `5001002002`/`5001002003` 和当前用户菜单校验返回回款列表；`PaymentCreate`、`PaymentEdit`、`PaymentView`、`PaymentCreateUpdate` 均复用 `PaymentService`。
- 页面载体和布局：`Areas/FAM/Views/JAR/List.cshtml`、`Payment/List.cshtml`、`Payment/Create.cshtml`、`Payment/Edit.cshtml`、`Payment/View.cshtml`；客户端为 `Scripts/FAM/AR/FAM.JAR.js`。
- 操作步骤与按钮行为：从合同清单新增回款；付款列表查看，`5001002003` 额外允许编辑；提交时需要回款方式和单据号，按案件的官费、非官费、代理费分项汇总回款金额；导出由 `JARFileCenterController.PaymentListExportToExcel` 生成临时 xls，下载端点按生成文件名读取。
- 状态流转及下游结果：旧实现没有独立 JAR 状态机，而是合同回款/应收记录写入 `PaymentService`；更改分项金额会标记 `IsChanged`。
- 数据表、字段及关联：旧控制器经合同 ID 初始化付款，付款持有合同、客户、付款单据、回款日期、回款金额，以及案件官费/非官费/代理费的回款分项。JARFileCenter 名称在该旧源中只承载导出临时文件，不提供交案费附件上传或文件列表。
- 采用证据：`legacy.../Areas/FAM/Controllers/JARController.cs`、`JARFileCenterController.cs`、`Views/JAR/*`、`Scripts/FAM/AR/FAM.JAR.js`。

## 4. 新系统当前实现
### 前端
- 页面和入口：财务中心菜单 `finance-jar`，`FinanceCenterPage` 在该路由渲染 `JarFeeManager`。
- 文件：`apps/admin-web/src/App.tsx`、`apps/admin-web/src/FinanceCenterPage.tsx`、`apps/admin-web/src/JarFeeManager.tsx`。
- 组件/函数：`JarFeeManager` 提供关键词/状态/合同筛选、分页、创建/编辑/删除、状态弹窗、附件抽屉、上传下载删除与 CSV 导出；列表展示合同编号而不是仅展示合同 ID。
- 状态、事件和 API 调用：使用 `/finance/jar-fees`、`/status`、`/files`、`/export` 专用接口；按后端 `capabilities` 控制可维护动作，并为已入账/已作废记录提供只读详情。

### 后端
- 文件：`apps/api-server/app/main.py`、`apps/api-server/app/models.py`。
- 路由：`GET/POST /finance/jar-fees`、`GET/PUT/DELETE /finance/jar-fees/{id}`、`POST /status`、`GET/POST /files`、`GET /files/{attachment_id}/download`、`DELETE /files/{attachment_id}`、`GET /export`。
- 服务/权限/校验函数：`_require_jar_fee_access` 强制 `finance-jar` 菜单权限（管理员例外）；合同由 `_jar_fee_contract` 确认可见且模块正确；分项合计不得超过总额；状态仅允许 `待确认→已确认/已作废`、`已确认→已入账/已作废`。通用 records 与 attachments 入口对 `jar_fee` 显式拒绝，不能绕过专用状态和文件规则。
- 持久化及下游逻辑：独立 `BusinessRecord.module == "jar_fee"`，不会写入普通 `finance` 费用；操作同时写 `WorkflowEvent` 与可在删除后保留的 `JarFeeAuditLog`。

### 数据库
- 表：`business_records`（模块 `jar_fee`）、`file_attachments`（`record_id` 关联交案费）、`workflow_events`、`jar_fee_audit_logs`。
- 主键/软关联字段：`data.contract_id` 与 `data.contract_no` 均由经过权限校验的合同写入；附件以 `FileAttachment.record_id` 关联。
- 状态/权限字段：`BusinessRecord.status` 为独立状态；专用接口在写入时记录操作人和审计事件。
- 历史数据兼容：新概念，需确认不把旧合同回款误解释为新独立交案费。

## 5. 新旧差异和根因
| 编号 | 具体页面/数据/功能/按钮 | 旧系统行为 | 新系统行为 | 证据 | 根因 |
|---|---|---|---|---|---|
| D1 | JAR 独立入口与清单 | 合同回款入口冠以 JAR，权限受页面菜单控制 | 当前任务开始时没有 JAR 概念 | 旧控制器/前端初始检索 | 财务中心没有映射此旧入口 |
| D2 | 独立数据模型 | 实际复用合同回款 PaymentService，并非独立交案费实体 | 用户要求新增独立应收费用类型 | 旧控制器、用户原文 | 新范围有意扩展，须避免与回款/普通费用重复记账 |
| D3 | 文件管理 | JARFileCenter 仅导出临时 xls | 用户要求上传、下载、列表与删除文件 | 旧文件控制器、用户原文 | 新范围有意扩展，需落实附件归属和权限 |

## 6. 精确修改清单
- [x] M1 前端 `apps/admin-web/src/App.tsx`、`FinanceCenterPage.tsx`、`JarFeeManager.tsx`：新增菜单、路由、列表、筛选、创建/编辑/删除、状态、文件和导出交互；对应 D1-D3。
- [x] M2 后端 `apps/api-server/app/main.py`、`models.py`：新增专用 JAR 请求模型、持久化字段、CRUD、状态、导出和文件接口，以及操作日志；对应 D1-D3。
- [x] M3 覆盖 `scripts/audit-menu-coverage.py`、`scripts/smoke-api.py`、`apps/admin-web/jarFeeFrontend.test.mjs`：增加菜单/结构和 API 成功失败路径覆盖；对应 D1-D3。
- 不涉及层及理由：不修改旧系统；它只作只读业务证据。
- 影响范围与回归风险：财务费用汇总、合同/案件关联、附件权限、导出数据范围和审计日志均须回归；JAR 不能通过普通费用入口造成双重金额或绕过状态控制。

## 7. 验证清单
- [ ] 完整 API 冒烟：已写入创建、读取、导出、分项越界、非法状态、通用 records/attachments 绕过、文件格式/上传下载和历史日志路径；受本地 API 实例与凭据限制尚未执行。
- [x] 后端隔离契约：在 `apps/api-server` 下以相邻工作树的 Python 虚拟环境执行 `...95-task23-ipr-annual-fee\apps\api-server\.venv\Scripts\python.exe -m unittest jar_fee_backend_contract_test.py -v`，4/4 通过（15.463 秒）。覆盖 CRUD、草稿更新回读、状态机、导出、附件上传/下载/删除后的物理清理、记录删除后审计保留、分项越界、通用 records/attachments 绕过、无 `finance-jar` 的 403、他人记录的 404、金额四字段在顶层置空且从 `data` 移除。
- [ ] 菜单覆盖审计：执行被 `CaseCenterPage.tsx:3011` 日期格式守卫失败提前阻断，未到 JAR 断言；`git show HEAD:apps/admin-web/src/CaseCenterPage.tsx` 与工作树一致，证实为本轮前已存在的基线问题，未改无关功能。
- [x] 前端生产构建：`npm.cmd run build -- --configLoader runner` 通过（`tsc -b` 与 Vite 生产构建）。
- [x] Python 编译：`python -m py_compile apps/api-server/app/main.py apps/api-server/app/models.py scripts/smoke-api.py scripts/audit-menu-coverage.py` 通过。
- [ ] 数据持久化及刷新回读。
- [ ] 权限、角色和操作日志。
- [ ] 测试数据及临时进程清理。
- [ ] 浏览器验收：内置浏览器运行时启动被 Windows sandbox `CreateProcessWithLogonW` 错误 1326 阻断，标签数为 0；当前未证明。

## 8. 实施记录
- 实际改动提交：待主会话统一安排，当前代理不提交。
- 与修改清单不一致之处及原因：旧 JARFileCenter 仅导出临时 xls；本次依据用户要求扩展为真实附件管理，未将其误写为旧系统既有能力。
- 测试结果与证据路径：前端结构测试 `node --test apps/admin-web/jarFeeFrontend.test.mjs` 通过；`npm.cmd run build -- --configLoader runner` 通过；Python 编译与 `git diff --check` 通过；完整验证仍见第 7 节阻断。
- 发布状态：本地实现/验收中，未部署。

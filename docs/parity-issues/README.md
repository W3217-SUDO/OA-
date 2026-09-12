# OA 新旧系统问题记录索引

2026-09-13 最新集成：[基线、分工与验证记录](./auto-rules-integration-20260913.md)。已在GitHub最新dev上整合原有修改，催收完成条件、交接期限、仅更新时事务提交已本地修复；未浏览器验收、未部署。28类完整生成规则仍未全部证明，见[覆盖矩阵](./auto-task-new-coverage-20260913.md)及[旧调度宿主追踪](./legacy-auto-task-host-followup-20260913.md)。

2026-09-13 补充：[旧系统28类自动任务与联动规则](./legacy-auto-task-rules-20260913.md)。已只读查询本地恢复旧库配置、调度配置和存储过程，完成候选与真实调度执行分开记录。

2026-09-13 新增：[案件固定自动任务来源追踪](./case-fixed-auto-task-trace-20260913.md)。已定位“立案登记/送达跟踪”的两处触发入口、7/14 日期限和负责人来源；旧系统自动生成器及线上记录来源仍未证明，未修改业务代码。

2026-09-13 新增：[反编译服务层评估](./decompiled-source-readiness-20260913.md)与[民事案件详情前端/逻辑映射](./civil-case-detail-source-map-20260913.md)。用户确认 GD/SH 是同一 OA 改名，继续按具体方法核对，不以名称或哈希差异阻断。

换智能体接续先读 [完整交接与当前断点](../AUDIT-HANDOFF-2026-09-12.md)。当前客户回收站进入公海已本地修复（后端 6/6、前端 6/6），未浏览器验收、未部署。

每条真实问题或待确认差异单独记录，必须对应到具体前端页面、路由、按钮、字段或组件。状态分为：已修复待验收、待确认、未通过、已验收。

| 文档 | 前端对应 | 当前状态 |
|---|---|---|
| [customer-recycle-release-blocked.md](./customer-recycle-release-blocked.md) | 三个客户回收站 -> 更多操作 -> 进入公海 | 本地修复；后端 6/6、前端 6/6，D6 定向两项通过；未浏览器验收/未部署 |
| [customer-claim-parity.md](./customer-claim-parity.md) | 公海客户 -> 拾回 | 源码级审计完成，无明确阻断差异；customer_managers/拾回后状态等服务层行为待数据库或业务确认 |
| [customer-assign-parity.md](./customer-assign-parity.md) | 部门/公司客户 -> 分配客户 | 服务层源码已核实；分配=换 owner（CustomerOwner/Holder/BusinessOwner），不改部门/管理人；新系统额外把分配人加入管理人列表，为功能扩展，保留；级联案件合同owner变更待核实 |
| [contract-customer-selector-placeholder.md](./contract-customer-selector-placeholder.md) | 合同新建 -> 客户选择字段 `customer`，`ContractCreateWizard` | 已修复，待本地页面验收 |
| [customer-shared-actions-parity.md](./customer-shared-actions-parity.md) | 客户管理 -> 我的共享客户，`CustomerCenterPage.originalActionItems` | 旧模板差异已核实，按用户菜单授权要求保留动作 |
| [customer-share-removal.md](./customer-share-removal.md) | 客户列表 -> 共享客户弹窗 -> 共享人员移除和保存 | 本地 19 项自动化及构建通过，未浏览器验收/部署 |
| [customer-recent-time-window.md](./customer-recent-time-window.md) | 最近联系/最近更新 -> 日期列、查询和分页总数 | 本地修复，6 项定向和 7 项共享回归通过；构建通过，未页面验收/部署 |
| [crm-page-audit-matrix.md](./crm-page-audit-matrix.md) | CRM 十个列表路由与旧 PageId/按钮映射 | 模板和查询链矩阵进行中，非页面验收完成 |
| [audit-session-20260912.md](./audit-session-20260912.md) | 本轮主动对齐审计及各模块页面映射 | 进行中 |
| [task-create-entry-parity.md](./task-create-entry-parity.md) | 事务中心任务列表操作区与独立创建模板 | 初步判断证据不足，本轮加按钮改动已撤回 |
| [investigation-admin-personal-scope.md](./investigation-admin-personal-scope.md) | 调查大厅个人路由 -> 列表范围，`visibleRows` | 个人线索与任务语义混淆，本轮筛选改动已撤回 |
| [audit-client-router-slices.md](./audit-client-router-slices.md) | 全站 API 调用，例：任务新建 `POST /tasks` | 静态审计工具修复，8 项测试通过 |
| [case-delete-menu-capability.md](./case-delete-menu-capability.md) | 公司案件 -> 删除案件，`deleteCompanyCase` | 候选差异，待旧源码与删除保护核对 |
| [case-delete-selection-truncation.md](./case-delete-selection-truncation.md) | 公司案件 -> 多选 -> 删除案件，选择集与 `deleteCompanyCase` | 本地自动化 19/19 与构建通过，待页面验收，未部署 |
| [case-module-parity-audit.md](./case-module-parity-audit.md) | 案件模块全量对齐（删除/分配/合并/参与人/创建/归档） | 初步结构审计完成；逻辑删除vs物理删除用户视角一致（均不可恢复）；已归档删除差异待业务确认 |
| [contract-module-parity-audit.md](./contract-module-parity-audit.md) | 合同模块对齐（删除/审批/归档/级联更新） | 初步结构审计完成；新系统删除安全性优于旧系统；客户分配级联更新合同owner已核实；审批流程待深入 |
| [legacy-area-baseline.md](./legacy-area-baseline.md) | 旧系统各区域 -> 新页面族候选映射 | 已完成文件级盘点，服务层已完整反编译，逐入口业务证据进行中 |

## 记录要求

新增记录必须写明问题来源、页面位置、路由、按钮或字段、旧系统观察、新系统根因、具体组件/事件处理器、整改文件、定向测试、构建结果、后续状态和残余风险。截图必须注明对应行和实际查看结果，不能只记录模块名称或接口名称。

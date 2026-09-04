# 知产中心案件协助费整改定位

## 1. 清单原文
- 工作簿：不涉及（直接开发任务）。
- 工作表：不涉及。
- 行号：不涉及。
- 原始问题（逐字）：【任务】知产中心-案件协助费管理

  【背景】旧系统有CaseAssistedFee增删改查+确认+办理，是知产案件的一种费用类型。

  【修复要求】
  1. 在知产案件详情中增加"协助费"管理功能
  2. 功能包括：协助费列表；新增/编辑/删除协助费；确认协助费；办理协助费
  3. 后端：新增知产案件协助费数据结构；新增增删改查接口；状态变更接口（确认/办理）；权限校验 + 操作日志
  4. 保持与知产中心其他费用风格一致
  5. 完成后本地构建验证无编译错误
- 补充说明（逐字）：无。
- 返工意见（逐字）：无。
- 当前状态：定位完成，实施中。

## 2. 截图分析
- 未提供截图；以用户原文和只读旧系统源码为需求证据。

## 3. 旧系统实现
- 入口、角色和数据状态：案件详情的 `CaseAssistedFee` 标签；创建后记录案件 ID/案号、资助类别，办理时写办理日期、经办人和回执。
- 页面载体和布局：`Areas/IPR/Views/Case/PartialView/CaseAssistedFeeList.cshtml` 及 `Case.Create.CaseInfo.js` 的表格、创建和办理弹窗。
- 操作步骤与按钮行为：`CaseAssistedFeeList/Create/Delete/Confirm/Transact`。确认弹窗收集办理日期和文件；办理后不可重复办理。
- 字段默认值、展示和校验：类别必填；办理必须提交日期和回执文件。
- 状态流转及下游结果：旧代码未提供独立持久化确认状态；办理会保存回执并变更已办理状态。
- 数据表、字段及关联：`IPR_Case_AssistedFee` 以 `CaseId` 关联案件，含 `AssistedFeeTypeId`、申请/办理人员日期与文件字段。
- 采用证据：`GD.CRM.WEB.VIP/Areas/IPR/Controllers/CaseController.cs::CaseAssistedFeeList/Create/Delete/Confirm/Transact`；`Scripts/IPR/Case/Case.Create.CaseInfo.js::CaseAssistedFee`。

## 4. 新系统当前实现
### 前端
- 页面和入口：知产中心 > 案件详情 > 资助明细。
- 文件：`apps/admin-web/src/IprCenterPage.tsx`。
- 组件/函数：`loadAssistedFees`、`createAssistedFee`、`transactAssistedFee`、`deleteAssistedFee`。
- 状态、事件和 API 调用：已有列表、新建、直接办理、删除；无编辑及独立确认操作。
- 当前行为形成原因：新建记录默认“待办理”，前端因此直接显示办理按钮。

### 后端
- 文件：`apps/api-server/app/models.py`、`apps/api-server/app/main.py`。
- 路由：已有 `/ipr/cases/{case_id}/assisted-fees` 的列表/创建/删除及 `/transact`。
- 服务/权限/校验函数：`_ensure_record_module`、`_require_record_owner_or_manager`；直接办理仅接受“待办理”。
- 持久化及下游逻辑：专用 `ipr_case_assisted_fees` 表、`FileAttachment` 回执和 `WorkflowEvent` 案件操作日志。
- 当前行为形成原因：创建默认状态和接口集未表达用户要求的独立确认、编辑状态机。

### 数据库
- 表：`ipr_case_assisted_fees`。
- 主键/软关联字段：`id`；`case_record_id -> business_records.id`；`receipt_attachment_id -> file_attachments.id`。
- 状态/权限字段：`status`、`request_user`、`response_user`；案件负责人、同部门负责人或管理员。
- 查询或写入关系：按路径案件 ID 限定协助费查询，且附件归当前案件。
- 历史数据兼容：既有“待办理”记录保持可办理，不回写为“待确认”。

## 5. 新旧差异和根因
| 编号 | 具体页面/数据/功能/按钮 | 旧系统行为 | 新系统行为 | 证据 | 根因 |
|---|---|---|---|---|---|
| D1 | 案件详情协助费表格 | 创建、删除、确认、办理 | 有创建、删除、直接办理，无编辑/确认 | 旧 JS/Controller；新 `IprCenterPage.tsx` | 前后端接口和前端状态未完整实现。 |
| D2 | 协助费状态和审计 | 办理需要日期及回执，案件关联；旧 `Confirm` 仅打开办理弹窗 | 新建默认待办理，可跳过用户要求的独立确认 | 旧 Controller；新模型/路由；用户原文 | 用户明确要求的“确认/办理”拆分尚未实现；新确认状态是本次增强，不宣称为旧系统既有持久化状态。 |
| D3 | 案件权限和归档阻断 | 案件范围内维护 | 写接口重复实现校验，未统一为案件在办写保护 | 新 `main.py` 路由 | 缺少协助费专用写入帮助函数。 |

## 6. 精确修改清单
- [x] M1 前端 `apps/admin-web/src/IprCenterPage.tsx::assisted fee state/actions/modals`：增加编辑目标和表单，确认按钮/API，按状态显示编辑、删除、确认、办理；对用户显示“协助费”。对应 D1/D2。
- [x] M2 后端 `apps/api-server/app/main.py::IprCaseAssistedFee inputs/routes`：增加更新及确认请求模型和 PATCH/confirm 路由；以专用案件在办检查、路径案件归属和状态机阻断通用费用绕过。对应 D1/D2/D3。
- [x] M3 数据库 `apps/api-server/app/models.py::IprCaseAssistedFee.status`：默认新记录为“待确认”，保留既有“待办理”兼容。对应 D2。
- [x] M4 测试 `apps/api-server/ipr_case_assisted_fee_workflow_test.py`：覆盖成功链、跨案件、归档、越权、直接办理、重复确认/办理和非 IPR 路径模块门禁。对应 D1/D2/D3。
- 不涉及层及理由：无需新迁移，SQLAlchemy `create_all` 下模型默认即可支持新创建数据；生产迁移不在本地构建任务范围。
- 影响范围与回归风险：详情标签原“资助明细”改为“协助费”；历史“待办理”条目仍可办理，避免存量流程中断。

## 7. 验证清单
- [x] 自动化测试：`python -m unittest ipr_case_assisted_fee_workflow_test.py ipr_case_detail_lists_pagination_contract_test.py`（4 tests）。
- [x] 生产构建：`npm.cmd run build`。
- [x] API 成功路径：创建、编辑、确认、带回执办理、附件下载及列表刷新回读。
- [x] API 失败路径：跨案件、归档、直接办理、重复确认/办理、空类别、空文件和无效扩展名。
- [x] 数据持久化及刷新回读：内存 SQLite 中协助费、附件、WorkflowEvent；回执临时目录精确删除并断言不存在。
- [x] 权限、角色和历史数据：非可见用户阻断，同部门负责人能力返回；手工插入既有“待办理”记录仍可删除。
- [x] 测试数据及临时进程清理：内存 SQLite 与每个测试独立临时上传目录均清理。
- [ ] 用户验收项：当前工具集未提供可控浏览器，待可用环境补做。

## 8. 实施记录
- 实际改动提交：未提交（本任务明确禁止提交/部署）。
- 与修改清单不一致之处及原因：未新增金额字段；旧 `CaseAssistedFee` 是资助申请/回执流程，用户未要求金额。新持久化确认状态是用户新增要求，旧系统 `Confirm` 仅渲染办理弹窗。
- 测试结果与证据路径：`apps/api-server/ipr_case_assisted_fee_workflow_test.py`；前端生产构建成功。`scripts/audit-menu-coverage.py` 被既有 `CaseCenterPage.tsx:3011` 日期格式审计失败阻断，与本次改动无关。
- API 冒烟：`python scripts/smoke-api.py` 未执行到接口调用即因本地未配置 `SMOKE_PASSWORD` 退出；未伪造凭据或测试数据。
- 发布状态：未发布。

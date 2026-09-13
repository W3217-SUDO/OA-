# 财务中心 FC-01 整改定位

## 1. 清单原文

- 工作簿：不适用；来源为旧系统说明书与用户直接指令。
- 工作表：不适用。
- 行号：财务中心审计 FC-01。
- 原始问题（逐字）：`参考这个跟旧系统源码找到财务这块的逻辑问题`
- 补充说明（逐字）：`逻辑这块还有大量问题`；`财务中心`
- 实施指令（逐字）：`修复部署`；`1`；`全部问题都要改完啊`
- 当前状态：第 1 项并入财务中心 11 项统一整改和一次发布。
- VibeHub 术语核对：以脱敏短词“数据一致性”“结算规则”调用解析器，无可靠匹配，未采用不相关链接。

## 2. 截图分析

### 图 1：旧系统说明书第 71 页

- 所属页面/入口：财务中心 > 结算管理。
- 业务对象和可见数据：回款、代理费结算、归档扣留和实际结算金额。
- 涉及功能：到账分配后的结算金额形成。
- 涉及按钮/字段：本笔结算金额、扣归档费、实际结算金额。
- 截图显示的目标行为：回款金额、代理费结算额、归档扣留额和实际结算额是不同金额口径。

### 图 2：旧系统说明书第 80 页

- 所属页面/入口：财务中心 > 结算管理 > 混合费用结算。
- 业务对象和可见数据：官方费用、代理费及归档费分别汇总。
- 涉及功能：费用分类后计算结算净额。
- 截图显示的目标行为：代理费先形成结算额，再扣归档费；到账分配额不能直接视为净结算额。

## 3. 旧系统实现

- 入口、角色和数据状态：财务人员在回款完成分配后，将同一 PaymentId 提交结算审核。
- 页面载体和布局：结算列表展示回款、官费、代理费、其他费用、代理费结算、归档费和实际结算。
- 操作步骤与按钮行为：到账分配保存费用对象；结算申请和审批继续读取这些对象并重新汇总。
- 字段默认值、展示和校验：历史代理费分支按本次分配额 80% 形成结算额，未归档时再按结算额 10% 留存；特定已归档阶段留存为零。
- 状态流转及下游结果：归档留存进入后续归档费结算链，案件归档后支付。
- 数据表、字段及关联：PaymentObject 以 CaseFeeId 关联费用，保存 CashedAmount、SettlementAmount 和 ArchiveAmount。
- 采用证据：旧系统说明书第 71、80、83 页；`SH.CRM.Service.Decompiled/.../ReceivedPayment/PaymentService.cs` 的 `GetPaymentObjectList`、`Approved`；旧网页 `SettlementController`。

## 4. 新系统当前实现

### 前端

- 页面和入口：财务中心 > 到账管理 > 分配回款。
- 文件：`apps/admin-web/src/finance/services/accountingActions.tsx`。
- 组件/函数：`allocateIncoming`。
- 状态、事件和 API 调用：向 `POST /finance/incoming-payments/{id}/allocate` 提交每条费用分配。
- 当前行为形成原因：前端把 `settlement_amount` 固定为本次分配额，并把 `archive_fee` 固定为 0。

### 后端

- 文件：`apps/api-server/app/areas/finance/router.py`、`apps/api-server/app/core/finance.py`。
- 路由：`POST /finance/incoming-payments/{payment_id}/allocate`。
- 服务/权限/校验函数：`allocate_incoming_payment`、`_general_settlement_rows`。
- 持久化及下游逻辑：分配接口原样持久化前端的 `settlement_items`；一般结算优先信任其中的结算额和归档费。
- 当前行为形成原因：权威金额规则被放在客户端，后端只校验上下限，没有根据费用类型和案件归档状态计算。

### 数据库

- 表：`incoming_payments`、`business_records`。
- 主键/软关联字段：`incoming_payments.allocations[].fee_record_id` 关联 `business_records.id`。
- 状态/权限字段：到账状态、案件状态、费用 `data.fee_type` 与 `data.fee_archived`。
- 查询或写入关系：分配 JSON 保存结算明细；结算申请再复制为 `finance_settlement.data.allocation_details` 快照。
- 历史数据兼容：未形成结算申请的既有分配应按权威费用重算；已经审批或付款的结算快照不在本次静默改写。

## 5. 新旧差异和根因

| 编号 | 具体页面/数据/功能/按钮 | 旧系统行为 | 新系统行为 | 证据 | 根因 |
|---|---|---|---|---|---|
| D1 | 到账分配后的代理费结算金额 | 服务端按费用类型计算代理费结算额 | 前端把分配额直接写成结算额 | PPT 71、80；旧 PaymentService；隔离结果 F01 | 结算规则错误下放到客户端并被后端信任 |
| D2 | 未归档代理费的归档扣留 | 服务端按结算额及案件阶段形成留存 | 前端固定写 0 | PPT 71、80、83；旧 PaymentService；隔离结果 F02 | 后端没有生成权威留存快照 |
| D3 | 已有未申请结算的错误分配 | 结算时从费用对象重新汇总 | 新系统继续读取错误显式金额 | `_general_settlement_rows` | 读取链缺少权威重算 |

## 6. 精确修改清单

- [x] M1 前端 `accountingActions.tsx::allocateIncoming`：只提交费用 ID、费用类型和本次分配额，不再提交客户端计算的结算额和归档费；对应 D1、D2。
- [x] M2 请求模型 `models_shared.py::IncomingPaymentSettlementItem`：允许结算额和归档费省略，作为兼容输入但不作为权威值；对应 D1、D2。
- [x] M3 后端 `finance.py`：新增统一服务端结算计算函数，按权威费用记录、费用类型、费用级覆盖和案件归档状态计算；对应 D1、D2。
- [x] M4 后端 `router.py::allocate_incoming_payment`：持久化服务端生成的结算明细；对应 D1、D2。
- [x] M5 后端 `finance.py::_general_settlement_rows`：对能够解析到费用记录的已有分配重新计算待结算金额；对应 D3。
- [x] M6 自动化回归：覆盖客户端伪造金额被忽略、代理费计算、归档状态豁免和历史待结算重算。
- 不涉及层及理由：不新增数据库字段或迁移；现行“未归档扣留 5%”的金额基数仍未确认，本次不擅自改变现有 80%/10%公式，也不重算已审批/已付款历史快照。
- 影响范围与回归风险：到账分配、待结算列表、结算申请快照和归档费后续列表；主要风险是历史分配缺少有效费用 ID，此类记录保持原值以避免无依据归类。

## 7. 验证清单

- [x] 自动化测试：服务端忽略客户端传入的 `settlement_amount`/`archive_fee`。
- [x] 自动化测试：未归档代理费按 80% 和 10% 形成准确到分的结算快照。
- [x] 自动化测试：已归档案件不再留存归档费。
- [x] 自动化测试：已有错误显式明细在待结算读取时按费用记录重算。
- [x] 生产构建：前端 TypeScript/Vite 构建。
- [x] API 失败路径：原有费用关联、客户和案件校验回归通过。
- [x] 数据持久化及刷新回读：内存 SQLite 验证持久化明细与待结算汇总一致。
- [x] 权限、角色和历史数据：权限逻辑不变；已审批/已付款快照不改写。
- [x] 测试数据及临时进程清理：只使用内存数据库，不创建业务数据。
- [ ] 用户验收项：在 8089 用一笔代理费回款确认分配后显示结算额、归档费和实际结算额；归档案件确认归档费为零。

## 8. 实施记录

- 实际改动提交：见本文件所在功能提交及其后续正式发布提交。
- 与修改清单不一致之处及原因：计算中发现二进制浮点数配合向上取整会使 `70.40 - 7.04` 变为 `63.37`，已在同一金额服务中改为十进制定点比例和汇总，属于 D1/D2 的金额准确性范围。
- 测试结果与证据路径：`python -m unittest incoming_payment_case_fee_row15_test.py case_fee_receipt_projection_row30_test.py case_fee_legacy_links_row19_test.py incoming_allocation_cases_row15_test.py incoming_allocation_customer_match_row8_test.py finance_invoice_row29_contract_test.py`（18 项通过）；`python -m py_compile app/core/finance.py app/areas/finance/router.py app/models_shared.py` 通过；前端发票载荷断言通过；`npm.cmd run build` 通过。
- 发布状态：11 项本地实现与统一生产构建已完成，待正式发布；发布后由用户在 8089 验收。

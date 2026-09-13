# 会议 2026-09-13｜合同付款与开票申请定位

## 用户澄清后的有效口径

案件头部仅显示建案时的合同。新建每笔案件费用允许另选合同，费用归集到该笔费用选择的合同，不能回写案件头部。完整澄清原文见 `meeting-20260913-source.md`。因此本报告D2原“开票不认ContractObject即有问题”的推断撤回；以下源码观察保留，但必须按费用自己的合同重新判断是否存在缺陷。未执行任何业务修改。

## 1. 清单原文
- 工作簿：不适用（会议原文）。
- 工作表：不适用。
- 行号：不适用。
- 原始问题（分段摘录）：系统费用分为合同相关费用（官费、代理费，涉及对外结算）和内部费用（提成、扣款，涉及内部分配）；律师在案件中录入费用后，需通过“申请付款”动作提交至财务中心，否则财务端不可见。当前合同模块中的“申请付款”和“申请开票”界面存在缺陷，未正确绑定案件费用且弹窗简陋，导致流程卡滞；需参照老系统逻辑修复界面，确保数据能流转至财务中心的请款单审批及待付款列表。平台财务中心则处理司法汇城平台的合同收支。
- 完整原文已保存在 `meeting-20260913-source.md`；本文仅保留分段摘录，不能把摘录扩写为新的客户需求。
- 返工意见（逐字）：无。
- 当前状态：只读定位完成；发现合同入口未提交审批、费用关系口径偏差及若干真实数据待核实项。会议目标限定为现行诉讼流程；旧仓中的 `Areas/Lawsuit`、`Legal`、`FCM`、`FAM` 仅作为待甄别实现证据，冗余旧模板/入口不是默认目标。未修改业务代码/数据库，未测试、提交、部署或打开浏览器。
- 定位基线：本地 `dev` 当前为 `05a719d0`；用户提供的线上基线为 `dev 53754c35 / 1.1.109`。按主会话已完成的提交差异核对，两者差异仅涉及合同撤销等，未触及本文追踪的合同付款/开票候选、申请提交或财务查询代码；本轮没有读取线上运行文件，不能把本地结论表述为线上已复现。
- 技术说明（非客户原文）：主会话确认 `ContractObject(contract_record_id, case_record_id)` 已存在，且 `contract/router.py:756-826` 已维护合同标的；因此不能以 `case.data` 的单合同引用推断“不支持多合同”。本轮仅比较实际费用候选对 `ContractObject` 与直接费用/案件合同引用的口径。
- VibeHub 术语核对：已调用；“付款申请单”“费用明细”无可靠条目；“审批工作流”只返回语义不相符的 [人在回路](https://vibe-hub.org/human-in-the-loop)，未采用。

## 2. 截图分析
### 图 1：无新截图
- 所属页面/入口：无。
- 业务对象和可见数据：无。
- 涉及功能：不以旧聊天截图或历史报告充当本次证据。
- 涉及按钮/字段：无。
- 用户标注区域：无。
- 截图显示的实际异常：未核实。
- 与其他截图的关系：无；后续实施前需以当前版本、可清理测试数据和同一路径浏览器验收补证。

## 3. 旧系统实现
- 入口、角色和数据状态：在尚未证明旧 `FAM` 页面属于当前诉讼流程有效目标的前提下，旧 Web 的合同应付入口是 `FAM/AP/APController.cs:39-63` 的 `PaymentCreate(long contractId, string batchNos)`；它以合同 ID 创建付款模型，并可按 `batchNos` 缩小付款对象。开票入口是 `FAM/Invoice/InvoiceController.cs:38-73` 的 `InvoiceCreate(long contractId, string caseFeeIds)`，仅保留 `CaseFeeOpenInvoiceAmount > 0` 的逐笔案件费用，并可按 `caseFeeIds` 预选。
- 页面载体和布局：付款为完整 `FAM/Views/AP/Payment/Create.cshtml` 页面，开票为完整 `FAM/Views/Invoice/InvoiceCreate.cshtml` 页面，不是案件详情内的轻量确认框。开票页包含合同、客户、申请信息和逐笔费用行；费用行含费用类型、案件费用、已收款、已开票、此次开票金额与 `item_InvoiceApply` 勾选框（`InvoiceCreate.cshtml:480-532`）。
- 操作步骤与按钮行为：旧 `InvoiceCreateUpdate`（`InvoiceController.cs:116-189`）按每个 `CaseFeeId` 汇总服务明细和开票金额，阻止实际开票金额小于所选案件费用开票金额后写入 `InvoiceService`。付款审核页由 `APController.PaymentAudit:168-188` 读取付款与审批流；`APController.PaymentAuditList:265-273` 初始化待审状态；`PendingPaymentList:244-260` 初始化已审批付款，供后续待付款处理。
- 字段默认值、展示和校验：旧开票创建由合同与客户预填抬头、统一社会信用/证照、银行、地址、电话；它在服务端按费用行计算类别汇总和金额。旧付款清单 `FAM/Views/AP/Payment/PendingList.cshtml:126-181` 显示请款单号、状态、申请日期、申请付款金额、案件编号、合同编号/名称、付款日期、打包单号、申请人、交款人、客户名称。
- 状态流转及下游结果：旧 AP 审批调用 `PaymentAuditService.GetPendingPaymentList`（`PaymentAuditController.cs:47`）；审核完成后的已审批付款由 `PendingPaymentList` 承载。旧发票审核由 `InvoiceAuditController.cs:195-233` 读取 `InvoiceAuditService` 流程并调用 `InvoiceService.Audit`。
- 数据表、字段及关联：本轮旧 Web/controller 只读到业务服务调用及 `contractId`、`batchNos`、`caseFeeIds` 参数；旧 Service/实体反编译层的实际表名、写入事务及多合同同案件消歧尚未定位，不能据此断言旧库的唯一关系规则。
- 采用证据：上述旧 Web 文件与行号；未读取旧页面、未查询旧库。它们只证明旧代码曾有该数据形态，不能证明应保留所有旧 `FAM` 页面、字段或流程；后续必须从现行诉讼入口追到实际调用，识别并裁剪冗余实现。

## 4. 新系统当前实现
### 前端
- 页面和入口：
  - 案件详情的律所/平台费用页签在 `apps/admin-web/src/legal/CaseDetail/CaseFeesPanel.tsx:51-71` 的“其他操作”提供“申请付款/申请开票”；内部费用页签仅提供“申请付款”（:76-99）。
  - 案件费用“申请付款”由 `apps/admin-web/src/legal/services/financeActions.tsx:919-961` 打开逐笔费用付款表单并 `POST /finance/fees/{feeId}/submit`；案件费用“申请开票”在 :864-913 先检查 `/finance/case-fees/invoice-status`，再带选中费用记录跳转 `finance-invoice-mine`。
  - 合同付款是 `ContractCenterPage` 打开 `ContractPaymentModal`；`apps/admin-web/src/contract/services/financeActions.tsx:46-151` 读取 `/contracts/{id}/payment-candidates`，以每笔 `case_fee_id` 或 `contract_object_id` 和本次金额提交 `/contracts/{id}/payment-applications`。弹窗 `ContractModals.tsx:582-740` 已有付款单位、申请日期、备注、逐笔候选/余额/本次金额表格，不是空壳弹窗。
  - 合同开票由 `ContractCenterPage.tsx:853-872` 读取 `/contracts/{id}/invoice-candidates`；`contract/services/financeActions.tsx:154-210` 选择 `case_fee_ids` 后 `POST /finance/invoices`。弹窗 `ContractModals.tsx:741-872` 已有发票抬头、税号、专票地址/电话/银行/账号、交付信息和逐笔费用表。
- 当前行为形成原因：合同付款的前端申请一次即提交“待审批”；合同开票前端只创建发票草稿，未调用其独立提交接口，见 D1。

### 后端
- 合同标的维护：`apps/api-server/app/areas/contract/router.py:756-826` 的 `ContractObject` 以 `contract_record_id + case_record_id + fee_type` 建立多对多可表达的合同-案件费用标的关系；该事实已纳入本次判断。
- 合同付款候选和流转：
  - `_contract_payment_candidate_rows`（`app/core/finance.py:441-530`）先取当前合同的 `ContractObject`，再按案件和费用类型用 `_fee_matches_contract_object`（:425-439）匹配逐笔 `BusinessRecord(module='finance')`；候选包含 `contract_object_id`、可选 `case_fee_id`、案件、费用类型、余额。
  - `POST /contracts/{id}/payment-applications`（`contract/router.py:1155-1224`）重算候选、锁住待审批/待付款/已付款/已核销金额、写 `BusinessRecord(module='contract_payment', status='待审批')`、JSON 快照和 `ContractPaymentLine`；审核/付款/核销路由在 :1226-1290，状态为 `待审批 -> 待付款 -> 已付款 -> 已核销`。
  - 财务前端付款查询会合并普通 `finance` 与 `contract_payment`（`apps/admin-web/src/finance/services/paymentsActions.tsx:237-265`）。是否与线上菜单、权限和实际样本完全一致，本轮未验证。
- 合同开票候选和流转：
  - `GET /contracts/{id}/invoice-candidates`（`contract/router.py:956-994`）只按费用 JSON 中的 `contract_id`、`contract_record_id` 或 `contract_no` 选取，而不查询 `ContractObject`。
  - `POST /finance/invoices`（`finance/router.py:1200-1233`）调用 `_validate_invoice_source_links`（`app/core/finance.py:620-711`），将 `case_fee_ids` 和 `case_fee_allocations` 写入 `BusinessRecord(module='invoice', status='草稿')`；单独的 `POST /finance/invoices/{id}/submit`（:1286-1304）才转为“待审批”。审核再转“待开票”（:1322-1338）。
- 当前行为形成原因：付款候选以 `ContractObject` 为主关系；开票候选/校验以费用 JSON、并在缺失时回退案件 JSON 为主关系，两者没有共用合同标的解析器。

### 数据库
- 表：`contract_objects`（合同标的）、`contract_payment_lines`（付款逐笔明细）、`business_records`（`contract_payment`、`invoice`、`finance` 模块）、`workflow_events`、`finance_transactions`。
- 主键/软关联字段：`ContractObject.contract_record_id -> business_records.id`、`ContractObject.case_record_id -> business_records.id`；`ContractPaymentLine.payment_record_id -> business_records.id`、`contract_object_id -> contract_objects.id`、`case_record_id -> business_records.id`（`app/models.py:1594-1608`）。开票逐笔关联目前只在 `BusinessRecord.data.case_fee_ids` / `case_fee_allocations` JSON，未见专用 invoice-line 表。
- 状态/权限字段：合同付款使用上述四段状态；开票为草稿、待审批、待开票等。合同付款审批/支付/核销走 `contract.payment.*` 动作；开票审批目前用 `admin/manager/auditor` 角色判定。
- 查询或写入关系：合同付款写明细表和 JSON 快照；合同开票只写费用 ID/分摊 JSON。`accounting_center`/`finance_scope` 会按 `contract_body == '平台'` 写入两类申请，但本轮未追到财务列表筛选是否实际按该字段分流。
- 历史数据兼容：付款列表对 `legacy_kind='ap_payment'` 有 JSON 行回退（`contract/router.py:1115-1153`）；其与新 `ContractPaymentLine` 的并存和历史多合同数据未做真实数据核对。

## 5. 新旧差异和根因
| 编号 | 具体页面/数据/功能/按钮 | 旧系统行为 | 新系统行为 | 证据 | 根因 |
|---|---|---|---|---|---|
| D1（源码已确认，线上现象待核实） | 合同模块“申请开票”后至审批提交 | 旧 FAM 代码存在完整申请页及审批服务调用，但是否为现行诉讼有效目标待核实 | 合同弹窗只调用 `POST /finance/invoices`，后端固定写“草稿”；前端没有接着调 `/finance/invoices/{id}/submit` | 新 `contract/services/financeActions.tsx:182-190`、`finance/router.py:1219-1233,1286-1304` | 合同入口未提交审批是源码确认的状态缺口。草稿可能在“我的发票”等页面可见；未以真实角色/数据核验，不能称其为用户线上卡滞的唯一或最关键实测根因，也不能断言所有财务页面不可见。 |
| D2（用户澄清后待重新定位） | 案件费用选择合同；合同付款/开票费用候选 | 旧入口按合同和逐笔费用形成候选；本次按用户明确规则解释 | 已观察付款从ContractObject匹配，开票读取费用直接合同引用。查询差异本身不证明开票有错 | 新 `core/finance.py:425-530,620-711`；`contract/router.py:956-994` | 正确归属是新建费用时所选合同，而非案件头部合同或任意关联标的。重点重新核对费用保存、付款匹配是否串合同、开票校验是否误用案件合同阻断。不同候选可以来自不同余额/状态过滤，不应强求完全相同。 |
| D3（已实现，待真实数据核实） | 合同付款申请至请款审批、待付款 | 旧 AP 有待审和已审批待付款分层 | 新合同付款申请直接为“待审批”，审核通过为“待付款”，并有付款/核销事务；财务付款查询代码合并 `finance` 与 `contract_payment` | 新 `contract/router.py:1155-1290`、`finance/paymentsActions.tsx:237-265` | 源码链已存在，不能再把“未实现付款下游”当作根因；仍需真实角色和数据验证其实际在财务中心页面的可见性、权限和平台分流。 |
| D4（证据不足待核实） | 平台财务中心只处理司法汇城平台合同收支 | 未完成旧 Service/菜单/表条件追踪 | 新申请写 `accounting_center` 和 `finance_scope`，但本轮未确认财务中心每个审批/待付查询实际使用这两个字段 | `contract/router.py:1208-1216`、`finance/router.py:1219-1233` | 可能存在“字段已写但列表未按字段分流”的风险；没有读取线上实际查询或真实样本，不能定性。 |

## 6. 精确修改清单
- [ ] M1 前端 `apps/admin-web/src/contract/services/financeActions.tsx::createContractInvoice`：产品确认“申请开票”的预期动作后，令该动作创建成功即调用 `/finance/invoices/{id}/submit`，或明确拆成“保存草稿/提交申请”；对应 D1；预期结果：用户可区分草稿与待审批申请，申请动作才转入审批。
- [ ] M2 重新定位费用创建/保存、`_contract_payment_candidate_rows`、`contract_invoice_candidates`、`_validate_invoice_source_links`：逐笔以费用创建时选择并保存的合同确定归属。费用已有明确合同B，即使案件主合同为A也不能改归A或仅因此拒绝；不得由ContractObject覆盖。确认实际偏差后再形成代码修改清单，保留各入口独立的余额/状态约束。
- [ ] M3 数据：优先核对现有费用contract_id/contract_record_id/contract_no及申请逐笔费用ID是否持续一致。不得为“多对多”强制新增合同标的快照，不得从案件合同猜测覆盖历史费用；缺失或矛盾的历史引用只记录待处理，未经授权不回填。
- [ ] M4 前端 `apps/admin-web/src/contract/ContractModals.tsx::ContractPaymentModal/ContractInvoiceModal`：在保留现有字段的前提下对齐旧完整申请页的申请信息和逐笔明细展示，复用同一费用行标识、余额、分摊金额和申请状态；对应 D1/D2；预期结果：不以“弹窗简陋”替代真实链路修复。
- [ ] M5 财务查询：明确 `finance_scope/accounting_center` 在请款审批、待付款、开票审批/待开票的过滤条件与菜单名称；对应 D4；预期结果：平台合同只进平台财务中心，其余合同进财务中心。
- 不涉及层及理由：本轮未发现需要触及提成、人事或 5% 保留款，按任务边界不纳入。
- 影响范围与回归风险：合同详情、案件费用入口、财务“我的/待审批/待付款”、合同归档完结、历史 `ap_payment` 兼容，以及一案多合同且同费用类型的唯一性阻断。

## 7. 验证清单
- [ ] 自动化测试：案件建于合同A，费用1选择A、费用2选择B，分别归集且不串合同；案件头部仍为A，B费用的申请不因案件主合同A而拒绝。覆盖保存回读、余额/状态过滤、合同引用缺失/冲突、草稿后提交、驳回重提、重复开票与金额分摊。
- [ ] 生产构建：前端生产构建、Python 编译、菜单覆盖审计、API 冒烟。
- [ ] API 成功路径：以唯一 `CODEX-*` 合同、案件、两条合同标的和逐笔费用验证付款 `待审批 -> 待付款 -> 已付款 -> 已核销`，开票 `草稿/提交 -> 待审批 -> 待开票`；分别核对 `contract_payment_lines` / 开票逐笔关联。
- [ ] API 失败路径：跨合同费用、同费用多标的歧义、超余额、重复待审付款、重复有效开票、专票必填字段、非本人/无权限、归档合同均须明确失败且无残留。
- [ ] 数据持久化及刷新回读：合同详情、财务请款单审批、待付款、发票待审批/待开票及刷新回读均核对同一费用 ID、合同标的 ID、金额和财务中心。
- [ ] 权限、角色和历史数据：律师申请、付款审批人、财务付款人、开票审批人、平台财务角色及 `legacy_kind='ap_payment'` 分别验证；无权不可见且不可写。
- [ ] 测试数据及临时进程清理：记录所有 `CODEX-*` ID，清理业务记录、明细、事件、交易、附件和参数后回查零残留。
- [ ] 用户验收项：在当前线上版本而非历史截图上，走合同与案件两个入口，并对照财务审批/待付款实际页面。

## 8. 实施记录
- 实际改动提交：无。本轮仅新增本文档；业务代码、数据库、既有文档、提交、部署和浏览器均未操作。
- 与修改清单不一致之处及原因：无实施，故未执行 M1-M5。
- 测试结果与证据路径：未运行测试；源码证据见本文第 3-5 节。CodeGraph 在定位前显示索引最新（1,323 files / 18,458 nodes），并用于追踪合同付款、开票、财务列表及调用范围；旧源码用定向只读检索补足。无新截图。
- 发布状态：未发布 / 待用户确认定位。

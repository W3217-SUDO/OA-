# 合同付款与开票全链路对齐清单（待确认）

## 本轮边界

用户原文：
> 这不能光对齐这一个后续的页面都要对齐 逻辑也要对齐了

- 日期：2026-09-14。先定位、记录、汇总给用户确认，再统一修改；本轮未改业务代码、未部署、未操作业务数据、未执行浏览器测试。
- 审计基线：本地 dev 5544ceec，已包含 04889b92 和 5544ceec 的财务整改。结束时 origin/dev 增至 9a909f09，中间两个提交仅修改 package.json/package-lock.json 版本，不涉及本轮业务证据。不能将版本提交当作新的功能实现。
- 实际新源码：C:/Users/Administrator/.codex/worktrees/oa-auto-rules-dev-20260913；未在旧的 45fd 工作树实施整改。
- 旧源码：C:/Users/Administrator/Desktop/OA系统/OA系统_跨电脑继续开发_20260804_完整交接/旧系统归档源码/SH.CRM.WEB。
- 反编译服务：同级 SH.CRM.Service.Decompiled/Dchien.Legal.Service/Dchien/Legal/Service/FAM，实际读取 AP/Payment/PaymentService.cs 与 Invoice/InvoiceService.cs。不是只凭截图或 JavaScript 推断。
- CodeGraph：开始检查 status，更新源码后 sync；explore 付款事件与合同开票。开票符号查询返回泛化 Contract 符号，没有精确定位函数，使用 rg 和文件读取补足；图谱不作为业务验收证据。
- VibeHub：查询脱敏短语 state machine，返回 UI 状态概念，未把非精确术语当作业务规则。
- 强制保留用户指定差异：**合同是否审批通过，不作为申请付款/开票的前置条件**。这不代表财务申请本身无需审批，也不代表放开重复金额、数据范围、终止状态校验。

## 已定位的九项问题

| 编号 | 前端位置 | 明确差异 | 记录 |
|---|---|---|---|
| CPI-01 | 合同列表 → 合同开票 → 选择费用 | 只带第一份合同，前端拒绝多案件；未跟上最新后端合票能力 | [详情](cpi-01-20260914.md) |
| CPI-02 | 合同开票 → 金额 → 提交 | 前端仍拒绝高开，与旧逻辑及 FC-10 不一致 | [详情](cpi-02-20260914.md) |
| CPI-03 | 合同开票 → 客户开票资料 | 只带抬头，未带客户税号、地址、电话、银行及账号 | [详情](cpi-03-20260914.md) |
| CPI-04 | 合同开票 → 表单、服务项、费用明细 | 缺逐费本次金额、查询、合同内外编号、到账/已开金额、服务金额/税额等表达 | [详情](cpi-04-20260914.md) |
| CPI-05 | 财务请款 → 撤销、回滚 | 合同请款调用普通费用接口，记录类型不匹配 | [详情](cpi-05-20260914.md) |
| CPI-06 | 发票详情、处理开票、作废页 | 固定一条服务项和合同费用摘要，未展示真实多条来源明细 | [详情](cpi-06-20260914.md) |
| CPI-07 | 我的请款 → 驳回后编辑、重提 | 合同请款无原单编辑重提闭环，已驳回与已退回状态不一致 | [详情](cpi-07-20260914.md) |
| CPI-08 | 我的开票 → 编辑发票申请 | 下游仍是另一套简化抽屉，不能完整编辑多服务项 | [详情](cpi-08-20260914.md) |
| CPI-09 | 请款查询 → 分页 | 独立分页后合并截断，两类记录同时较多时漏行 | [详情](cpi-09-20260914.md) |

## 页面与逻辑覆盖图

下表“已存在”仅指源码发现对应实现，不是页面验收通过，也不是逐字段无差异。

| 业务节点 | 旧页面/控制器/服务 | 新前端及接口 | 结论及下一项证据 |
|---|---|---|---|
| 合同付款入口 | FCM.Contract.js PaymentApply | ContractCenterPage.startContractFinance → contract-payment-apply 路由 | 独立页面已存在；保留合同审批无关规则 |
| 收款单位查询/选择 | PaymentType/List.cshtml、FAM.AP.Payment.js PaymentType | ContractPaymentUnitPicker → payment-candidates | 列表、单选、分页、查询已有；既有114返工待用户验收 |
| 新增收款单位 | SystemCenter PaymentTypeCreateUpdate | PaymentTypeCreateModal → payment-types | 已有；银行信息必填与旧特殊单位规则仍待业务证据核实，不能直接删除安全校验 |
| 付款申请信息/费用 | AP/Payment/Create.cshtml、APController.PaymentCreate、AP PaymentService.CreatePayment | ContractPaymentModal、createContractPayment → payment-applications | 已有紧凑页面；字段显示与真实费用分类仍需逐场景验收 |
| 原请款修改重提 | APController.PaymentEdit、PaymentCreateUpdate | 当前合同专用接口无对应编辑重提 | CPI-07 |
| 付款审批及历史 | APController.PaymentAudit/MultiPaymentAudit，PaymentService 初始化审核节点/轮次 | submitFeeReview → contract-payment-applications/review | 简单通过/驳回已存在；旧配置节点/轮次与新 WorkflowEvent 并非同一模型，见待核实项 |
| 待付款/办理付款 | APController.PendingPaymentList | FinanceCenterPage 付款入口；contract-payment-applications/pay | 专用付款保存交易、改变状态；混合列表及入口可达性未浏览器验证 |
| 撤销/回滚 | PaymentCanceled、PaymentRollback | submitPaymentCancel/submitPaymentRollback | CPI-05 |
| 核销 | APController.PaymentPackingVerify | writeoffFee → contract-payment-applications/writeoff | 检查已付款和流水合计，已存在；更新后只刷新普通费用列表，合同列表即时刷新待核实 |
| 付款包/打印/Word | APController.PaymentPackingList/Print/PrintToWord | payment-packages、printPayment、downloadPaymentPrintWord | 新接口主要为 internal payment package，不能用此证明合同官费付款包已等价；待专项补证 |
| 请款查询/详情 | PaymentController.PaymentList、APController.PaymentView | loadPaymentQueryPage、openPaymentDetail | CPI-09；详情字段、审核轮次补证，不宣称全对齐 |
| 合同开票入口 | FCM.Contract.js InvoiceApply 多 contractNos | ContractCenterPage 单合同路由 | CPI-01 |
| 开票客户资料 | InvoiceController.InvoiceDetailCreate | invoiceForm 初始化 | CPI-03 |
| 开票服务项/费用分配 | InvoiceDetailCreate.cshtml、InvoiceService.InvoiceCreateUpdate | ContractInvoiceModal、createContractInvoice | CPI-01/02/04 |
| 提交申请 | InvoiceCreateUpdate 设置 Pending 并写节点 | createContractInvoice 先创建再 submit | 提交链已有；失败保留原草稿，不应重复创建 |
| 我的/公司/待处理开票 | InvoiceList、PendingList、InvoicedList | loadInvoiceMine/Company/Pending → finance/invoices | 查询接口已有；逐列、筛选总数、角色范围未验收 |
| 编辑/驳回重提 | InvoiceEdit、InvoiceCreateUpdate | createInvoice PATCH；submit 接受草稿/已驳回 | CPI-08；多服务项编辑和保留须补齐 |
| 审批/开票/驳回 | 旧 InvoiceService 节点与发票处理链 | review、issue、reject-issue | 专用状态校验和交易记录已有；配置审核人/轮次、菜单授权关系待核实 |
| 查看/处理/作废详情 | InvoiceView、InvoiceCancel | 共用 invoiceDetailPage | CPI-06 |
| 撤回申请 | ApplicationCancel/ApplicationCanceled | withdraw，状态已撤回，WorkflowEvent | 已有对应动作；费用释放与旧累计字段一致性需定向检查 |
| 作废发票 | InvoiceCancel/InvoiceCanceled | void，生成负向开票流水 | 已有冲销逻辑；多费额度恢复及历史映射未实际验收 |
| 改票号/日期 | InvoiceNoChange/Update、InvoiceDateChange/Update | change-number/change-date，同步关联交易 | 已有字段/流水同步代码；历史票无交易ID场景需补证 |

## 不能武断判为已对齐的边界

1. **审批节点和轮次**：反编译服务按默认 AuditFlowNode 初始化审核人，编辑重新记录审核轮次；新合同付款/发票审核路由是状态切换加 WorkflowEvent。需核对当前实际有效的审批配置以及用户“菜单开放即操作开放”规则，再决定恢复哪些节点行为；不自动照搬旧角色限制。
2. **付款费用分类及特殊收款单位**：旧 CreatePayment 依据旧费用分类排除 NonOffice；新候选按业务类型与余额计算。须补费用分类映射，不能依据中文名称猜等价。旧库有空银行/账号单位，新列表可选但提交仍要求完整，需确定特殊单位业务规则。
3. **付款包与打印**：已有内部费用打包不等于合同付款打包；必须以合同官费来源逐项核对打包、拆包、核销、Word 内容，尚不能标记通过。
4. **开票参考数据范围**：财务编辑 loadInvoiceReferenceData 只取第一页100条客户、合同和费用；是否通过其他加载路径补全尚未完成所有入口核对。列为待核实风险，不编造现网必现结论。
5. **部署与真实数据**：本轮只对本地最新功能提交和后续纯版本差异做了核对；未查询服务器运行版本、未做真实角色/数据/页面验收。不能把其他任务 FC-01 至 FC-11 的“本地通过”当成本轮全链路通过。

## 统一整改建议

- 第一组：CPI-01/02/03/04/08 统一合同与财务开票表单、来源选择、逐费分配、客户资料及重提行为，避免两套实现再次分叉。
- 第二组：CPI-06 让详情、处理、作废均展示同一份真实明细；不只修申请页。
- 第三组：CPI-05/07 补合同请款的编辑、重提、撤回、回滚与余额恢复，保留不可逆状态保护。
- 第四组：CPI-09 统一请款查询分页和总数，再核对付款/核销后的列表刷新。
- 上述待核实边界继续取证，不擅自变更未知规则。确认后按用户要求整批改好、在本地构建，统一发布；线上业务验收由用户执行。

## 本轮交付状态

- 九条问题各有独立 MD：前端位置、旧新源码、差异、拟改动文件、聚焦检查及后续状态。
- 业务代码：零修改；数据库：零操作；浏览器：零新增标签；构建/接口测试：未运行（审计阶段）。
- 文档暂存本地供确认，未 Git 提交/推送；既有 auto-task-fix-evidence-20260913.md 未改动。
- 本文是源码定位清单，不是“全系统审计完成”或“全部页面已经对齐”的证明。

## 用户确认后的统一实施（2026-09-14）

- 用户先要求“部署”，澄清尚未实现后明确答复“可以”，授权九项统一修复、本地构建后一次部署。
- 开始前 fetch 两个远端，dev 快进至 9a909f09；线上 production-current 同为 9a909f09 / 1.1.116，两服务 active，目录正确。
- 受控分工：A 合同开票前端；B 财务后续前端；C 合同请款与统一查询后端；D 发票明细后端。共享文件按唯一所有者划分，主任务串行提交发布。
- 子任务不再派生、不单独提交部署、不开浏览器；只用隔离验证，不操作业务数据库。
- [x] 用户确认范围；本地和线上基线一致。
- [x] 九项实现与接口契约核对。
- [x] 隔离验证、生产构建、后端加载与路由覆盖。
- [ ] 精确提交与远端同步，唯一版本统一发布。
- [ ] 服务健康、静态资源、GitHub main 同步及回执。
- [ ] 用户线上业务验收。

### 集成过程记录

- 首轮整合发现财务新增模块缺 TypeScript 声明及列类型错误，已退回 B 修复；随后 `tsc -b` 与本地 `vite build` 通过。后续候选加载调整完成后仍须再构建最终产物。
- 菜单审计旧付款文案断言失配，改为真实候选、金额、提交绑定断言；完整 `audit-menu-coverage.py` 通过。`audit-client-api-coverage.py` 828处调用通过，实际导入 FastAPI 为780条路由，新增8条均已挂载。
- 合同前端14/14定向隔离测试通过。后端最终联合执行 `cpi_d_invoice_contract_test`、`contract_payment_lifecycle_cpi_test`、`finance_invoice_row29_contract_test` 共29/29通过（86.005秒），全部使用隔离数据库，不连接业务库。
- 集成补证：部分开票费用保留余额；已授权费用的他人占用也计入余额，但隐藏他人发票编号、ID和日期。双用户100-10-30=60场景已覆盖。
- 当前仍收尾财务开票候选分页及原单已选费用加载；由B唯一修改，完成后主任务统一复核发布。已完成的A/C/D任务已回收，不保留空闲代理或浏览器标签。
- 本轮术语查询仅发送脱敏短语“状态流转”，解析器没有可靠匹配，未追加无关术语；原客户要求和旧系统证据不作替换。

### 统一发布就绪清单

| 问题 | 前端位置 | 本次整改 |
| --- | --- | --- |
| CPI-01 | 合同列表 / 合同开票 | 同客户多合同、多案件选择；刷新保留来源，逐费归属不混用 |
| CPI-02 | 合同开票 / 本次开票、高开 | 保留高开及逐费分配，数量、金额、服务项总额统一校验 |
| CPI-03 | 合同开票 / 客户开票资料 | 从准确客户档案预填税号、地址、电话、开户行和账号，歧义不猜 |
| CPI-04 | 合同开票 / 服务项、费用表格及查询 | 完整整页和服务明细，部分及跨申请人占用余额正确，缺失金额不伪造零 |
| CPI-05 | 财务请款 / 撤销、回滚 | 按合同请款/普通请款调用专用接口，保留状态保护与刷新 |
| CPI-06 | 发票查看、处理、作废 / 服务项与对象明细 | 展示所有真实行，不用总金额代替逐费金额，不伪造历史服务项 |
| CPI-07 | 我的请款 / 被驳回单据编辑、重新提交 | 修改原单保留编号，重新校验余额，已支付/核销不能回滚修改 |
| CPI-08 | 我的开票 / 新建、编辑、保存并提交 | 独立完整表单、共用服务编辑器；按客户/原票分页，保留跨页已选费用及原票号，防晚到请求串数据 |
| CPI-09 | 请款查询 / 筛选、总条数、翻页 | 后端统一筛选排序分页，不再两源独立取页后截断 |

- 最终联合前端 `node --test src/finance/cpiChain.test.mjs src/contract/contractInvoiceApplication.test.mjs`：26/26通过；后端29/29通过。
- 最终 `tsc -b`、本地 `vite build` 通过；Vite仅保留已有大包提示，不是构建错误。未运行连接业务库的verify-local整套脚本；改用上列隔离检查及静态覆盖审计。
- CodeGraph用于调用面定位并同步，不作为业务正确性证据；浏览器标签数为0，业务数据与附件零创建。
- READY TO RELEASE：55项隔离检查通过，生产构建完成；无数据库迁移/补丁，无需数据库备份。主任务精确提交、双远端dev同步后申请唯一版本，上传本地dist后一次重启；版本、提交、文件哈希与实际健康结果写入正式发布回执和服务器队列。
- 本文提交时尚未激活新版本；不得把发布就绪视为发布成功。真实页面/角色、PostgreSQL实际并发及用户业务验收未证明，不能宣称全OA全部对齐。

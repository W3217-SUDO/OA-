# 2026-09-13 会议｜代理费提成与归档留存定位

## 最新截图补充（优先于下文早期定位状态）

- 用户追加图片 `C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-32a9204f-08ac-4fb9-aa55-07368b5ee587.png`，已逐图查看。可见案件详情、律所费用列表、右侧新建提成预览、人员未配置提成提示及空明细，红字标注“人员提成绑定”。未提供新文字规则。
- 精确入口为案件详情 > 律所费用 > 选择代理费 > 新建提成；不是新增费用编辑器，也不是归档留存页面。前端 `legal/services/financeActions.tsx::openCaseCommission` 调用 GET `/cases/{id}/commission-preview?source_fee_id=...`，`CaseCenterPage.tsx` 渲染返回的缺配提示。
- 源码链为 `_case_commission_preview` -> `_case_commission_preview_for_amount` -> 员工索引/账号 -> `_commission_scheme_record_for_case` -> 角色比例或固定金额。方案按案件日期和员工ID、kind=commission筛选。
- 当前“未设某角色提成”不只代表没有方案，也可能是案件人员未匹配员工档案、没有覆盖案件日期的方案，或对应角色比例和固定金额均为零。截图只证明提示及空明细，不能单独认定数据库没配，也不能证明绑定一定正确。
- 本批已将新增代理费自动提成与此既有预览接入同一计算服务；但截图中具体人员的线上档案、方案有效期和角色字段尚未只读核实，仍为待核实，不声称截图问题已解决。不得为消除提示随意写比例、篡改方案日期或把经办律师映射为其他角色。
- VibeHub已查询脱敏词“数据绑定”，无可靠词条。未运行浏览器、数据库测试或业务数据写入。当前代码/构建/未部署状态以 [整改执行记录](meeting-20260913-remediation.md) 为准；下文为实施前的分析快照。

## 1. 清单原文
- 工作簿：不适用（会议原文）。
- 工作表：不适用。
- 行号：不适用。
- 原始问题（逐字）：新增代理费后无法自动计算并显示人员提成，原因是人员与提成比例未正确绑定；需检查经办律师等角色配置，确保修改人员信息后能触发正确的提成计算逻辑。财务中心支持银行流水导入以匹配回款，律师需协助确认款项归属；结算管理涉及律师与律所的对账，包含归档费结算逻辑（未归档扣留5%）
- 补充说明（逐字）：无。
- 返工意见（逐字）：无。
- 当前状态：只读定位完成；未修改业务代码、数据库、配置或线上环境，未执行浏览器或业务测试、提交、部署。
- 定位基线：用户指定线上为 `dev` 提交 `53754c35`、版本 `1.1.109`；本次只读工作树 `C:/Users/Administrator/.codex/worktrees/oa-auto-rules-dev-20260913` 的当前 HEAD 为 `05a719d0`、`apps/admin-web/package.json` 为 `1.1.109`。因此下列“新系统当前实现”是该工作树源码证据，未以运行中 8089 页面或数据库回读证明其与指定线上提交逐字一致。
- VibeHub 术语核对：已以脱敏候选 `commission calculation`、`bank reconciliation`、`retention percentage` 调用 resolver；均无可靠返回，不添加术语链接。

## 2. 截图分析
- 无新截图、旧系统截图或返工截图提供；未创建或虚构截图证据。
- 本文只以会议原文、旧 Web/反编译服务源码和新工作树源码建立候选差异；凡需运行态数据、人员配置或实际金额结果的结论均标为证据不足。

## 3. 旧系统实现
- 入口、角色和数据状态：旧 Web `Areas/FAM/Views/CaseFee/CaseFeeList.cshtml:361-383` 提供批量新增费用、修改经办律师和“生成结算提成表”入口（`:409`）。案件参与人编辑页 `Areas/Legal/Views/Case/CivilDispute/PartialView/ParticipantEdit.cshtml:61,128-141` 明确含开庭律师、经办律师、律师助理，并以 `Permission.EditCaseLawer` 控制经办律师编辑。
- 人员提成来源：本次可复核旧服务未找到“费用新增后按员工提成比例自动生成内部提成”的实现或人员提成比例表/字段的完整调用链。旧 `InternalFeeService.cs`、`CaseFeeService.cs` 和 `CaseService.cs` 中命中的提成/人员相关结果不足以证明该自动机制存在，不能把会议归因写为已证实的旧系统行为。
- 回款与结算（历史实现参考）：反编译 `Dchien.Legal.Service/Dchien/Legal/Service/FAM/AR/ReceivedPayment/PaymentService.cs:178-182,560-564` 对该 FAM/AR 查询分支的非官费写入 `CaseNonOfficeFeeSettlementAmount = 已分配额 * 80 / 100`，归档额为 `非官费结算基数 * 80 / 100 * 10 / 100`，总结算额再扣归档额；`:439-455` 对未归档阶段写 `ArchiveAmountSettlementStatus=10` 和归档额，特定案件阶段置零并标记 `30`。该服务按 PageId 分为 GroupId 10/20（`PaymentService.cs:159-165`；对应费用查询 `CaseFeeService.cs:100-106`）。这是历史实现参考，不能否定会议提出的现行规则变更；会议仅明确“未归档扣留5%”，未给出留存金额的计算基数。
- 状态流转及下游结果：`PaymentService.cs:530-545` 将回款送结算审核（状态 10）；`:548-596` 审核同意时更新结算额/状态并逐条调用 `PaymentObjectService.ToAudit`；`:635-664` 回滚清空结算额、归档额和归档结算状态。旧 Web `Areas/FAM/Controllers/ArchiveSettlementController.cs:138-267` 分别调用 `PaymentObjectService.ToAudit/Approved/Rejected/Rollback`。
- 数据表、字段及关联：从旧反编译业务模型可确认支付对象使用 `CaseCommissionFeeId`、`CaseCommissionFeeAmount`、`CaseCommissionFeeCashedAmount`、`CaseCommissionFeePaidTotalAmount`（`Dchien.Legal.BizModel/.../FAM/AP/Payment/BizPaymentObject.cs:143-225`）。本轮未读旧库，无法确认会议所称“人员与比例绑定”对应的权威旧表名与外键。
- 采用证据：上述旧源码路径与行号；没有旧页面运行态或数据库证据。

## 4. 新系统当前实现
### 前端
- 页面和入口：财务中心费用编辑窗的代理费分支位于 `apps/admin-web/src/finance/FinanceCenterView.tsx:3964-4032`。仅当费用类型为“代理费”时显示“员工提成” `Form.List`；用户手动点击“新建员工提成”，选择 `employee_username`，输入提成类型和金额。
- 案件中心同类入口：`apps/admin-web/src/legal/CaseCenterPage.tsx:3511-3521` 的新增费用弹窗在代理费分支同样使用 `Form.List(name="commission_details")`；`:3520` 要求用户手动点击“新建员工提成”、选择员工、手工填写提成金额。批量案件费用入口 `apps/admin-web/src/legal/services/financeActions.tsx:344-354` 初始化 `items[].commission_details: []`（`:351`），未按案件人员、角色或人员方案预填。
- 组件/事件/API：财务中心保存操作由 `apps/admin-web/src/finance/services/paymentsActions.tsx:282-283` 向 `POST/PUT /finance/fees` 提交完整表单，其中包含 `commission_details`；案件中心上述表单沿用同一费用提交契约。两个入口均没有从案件 `handling_lawyer/handling_lawyers`、人员提成方案或比例字段推导默认人员、比例或金额，也没有在人员字段变更时的重算事件。
- 银行流水必要链路：`apps/admin-web/src/finance/services/workflowActions.tsx:47-64` 上传文件到 `POST /finance/incoming-payments/import`；`accountingActions.tsx:79-88` 认领客户，`:91-170` 读取候选并将用户选定的费用分配提交到 `/allocate`。`IncomingAllocationModal.tsx:66-249` 只展示和筛选候选案件费用、输入本次回款，不替代律师确认归属。

### 后端
- 费用输入与校验：`apps/api-server/app/models_shared.py:1640-1666` 的 `FinanceFeeCommissionDetailInput` 只有 `employee_username`、`commission_type`、`amount`、`remark`；`FinanceFeeInput` 通过 `commission_details` 接收这些显式明细。`app/core/finance.py:228-271::_finance_fee_commission_details` 只校验代理费类型、员工账号唯一/在职、金额和总额不超过代理费，随后原样规范化为 `actual_commission`；未读取 `HrSubrecord(kind="commission")`，未读取案件律师角色，也未计算比例。
- 人员/角色关联：案件结算行仅读取案件 JSON 中 `handling_lawyers`、`handling_lawyer`、`assistant/lawyer_assistant` 作为展示/筛选快照（`app/core/finance.py:1826-1827,1874-1875,2074-2075`）。这条链没有调用 `_commission_scheme_for_case` 或人员提成方案来生成费用的 `commission_details`；故“新建或修改代理费会自动算人员提成”和“修改经办律师会重算已存在提成”均为当前源码未实现，而不是已验证的运行时故障根因。
- 银行流水 API：`apps/api-server/app/areas/finance/router.py:2156-2208` 导入、`:2315-2333` 认领、`:2336-2502` 查询可分配候选、`:2503-2645` 分配。该链路已经实现导入至分配；律师协助确认款项归属的角色权限和实际操作责任未在本次只读范围内以运行态验证。
- 结算与归档：`app/core/finance.py:1845-1858` 对无显式覆盖的代理费计算 `settlement_amount = current_amount * 0.8`，再计算 `archive_fee = settlement_amount * 0.1`（退费例外为零）。`1929-1935` 从明细汇总实际结算额。`1994-2136::_pending_archive_settlement_rows` 仅从已付款的 `finance_settlement` 读取留存明细，案件未归档显示“待归档”，归档后才进入“待支付”；已支付/已拒绝的 `finance_archive_settlement` 以 `source_row_id` 防重复决定。

### 数据库
- `business_records`：统一费用、案件、人员附属记录和结算申请的载体，关键字段为 `id/module/serial_no/status/owner/department/data`（`apps/api-server/app/models.py:335-355`）。代理费和生成的员工提成目前依赖 `data.fee_type`、`data.commission_details`、`data.actual_commission`、`data.payee` 等 JSON 字段，而非已验证的专用比例外键。
- `hr_subrecords`：员工提成方案的结构化附属记录类型为 `kind="commission"`（`models.py:49-50`；查询入口 `app/core/system.py:1333-1430`）。本次未发现其被 `_finance_fee_commission_details` 调用。
- `incoming_payments`：银行到账表，字段为 `receipt_no/received_date/amount/payer_name/bank_reference/status/claimed_customer/contract_record_id/contract_no/case_no/bank_source/claimant/allocated_amount/allocations/operator/remark`（`models.py:1364-1387`）。
- 结算/归档结算：使用 `business_records.module="finance_settlement"` 和 `module="finance_archive_settlement"`；`data.allocation_details[]` 存 `fee_id/case_id/case_no/current_amount/settlement_amount/archive_fee`，并以 `source_row_id` 幂等关联（`app/core/finance.py:1810-1829,2001-2035`）。

## 5. 新旧差异和根因
| 编号 | 具体页面/数据/功能/按钮 | 旧系统行为 | 新系统行为 | 证据 | 根因 |
|---|---|---|---|---|---|
| D1 | 财务中心、案件中心 > 新增/编辑代理费 > 员工提成 | 旧系统有案件人员入口和结算提成表入口；自动按比例生成的旧服务链本次未证实。 | 两个入口都手工新增明细、选择员工、输入金额；案件中心批量创建明确初始化空 `commission_details`。后端仅校验显式员工与金额。 | 旧 Web 路径 `CaseFeeList.cshtml:361-409`；新 `FinanceCenterView.tsx:3964-4032`、`CaseCenterPage.tsx:3511-3521`、`legal/services/financeActions.tsx:344-354`、`finance.py:228-271`。 | 已确认：新实现没有“案件角色/人员方案 -> 提成明细”的自动派生。会议所称“比例未绑定”仍需旧表和运行态证据确认。 |
| D2 | 修改经办律师等人员后重新计算 | 旧页面支持批量修改经办律师，但尚未找到其触发已存在费用/提成重算的源码。 | 角色字段仅被结算读取作快照；没有重算 API、事件或前端触发。 | 旧 `ParticipantEdit.cshtml:61,128-141`；新 `finance.py:1826-1827,1874-1875`。 | 已确认缺口：新源码没有重算路径；证据不足：不能断言旧系统一定实时重算。 |
| D3 | 银行流水导入、律师确认、回款匹配 | 本次只确认旧系统存在回款/结算服务，未定位其银行导入入口。 | 已有导入 -> 客户认领 -> 费用候选分配 API 和 UI。 | 新 `workflowActions.tsx:47-64`、`accountingActions.tsx:79-170`、`router.py:2156-2645`。 | 现系统已实现必要技术链路；律师协助确认的业务职责、权限和异常路径未测试，不能宣称已验收。 |
| D4 | 结算基数、未归档留存与归档释放 | 历史 FAM/AR 服务分支使用非官费 80% 结算、再从该口径取 10% 归档额；归档状态控制后续审核/回滚。 | 当前新系统同样使用代理费 80% 结算、再留结算额 10%；案件归档前待归档、归档后待支付。 | 会议原文；旧 `PaymentService.cs:159-182,439-455,560-664`、`CaseFeeService.cs:100-106`；新 `finance.py:1845-1858,1994-2136`。 | 已确认待对齐差异：会议要求“未归档扣留5%”，当前规则为“80%结算额再留10%”。待业务确认：5%的金额基数、生效时间、归档释放条件，以及是否和如何影响历史已结算记录；基数不明，不能直接按 `0.95` 计算。 |

## 6. 精确修改清单
- [ ] M1 前端 `apps/admin-web/src/finance/FinanceCenterView.tsx::代理费 Form.List`、`apps/admin-web/src/legal/CaseCenterPage.tsx::代理费 Form.List` 与 `apps/admin-web/src/legal/services/financeActions.tsx::openCaseFeeCreator`：仅在业务确认“自动计算”规则、人员方案字段和适用角色后，统一将空初始化替换为可审计的默认提成明细/预览，并明确人工覆写策略；对应 D1、D2。
- [ ] M2 后端 `apps/api-server/app/areas/finance/router.py::POST/PUT /finance/fees` 与 `app/core/finance.py::_finance_fee_commission_details`：增加单一的提成派生服务，按费用关联案件、角色快照、员工有效期内的 `HrSubrecord(kind=commission)` 和经确认的比例公式生成/校验明细；禁止仅靠前端计算；对应 D1。
- [ ] M3 后端 `apps/api-server/app/core/cases.py` 的案件人员变更入口及费用服务：定义“修改人员后”影响草稿、已审批、已付款、已结算记录各自的阻断或重算策略，并增加显式重算事件/审计；对应 D2。当前不得假设已付款历史可被静默改写。
- [ ] M4 数据库 `business_records.data` / `hr_subrecords`：先完成只读数据审计，确认人员方案的比例字段、起止日期和案件角色绑定键；若缺少稳定 `user_id + role + effective_from/to` 关系，再设计迁移。对应 D1、D2。
- [ ] M5 业务规则确认：明确“未归档扣留5%”的金额基数、适用费用类型、开始生效时间、归档释放条件，以及历史已结算/已付款记录是否重算；对应 D4。
- [ ] M6 后端 `app/core/finance.py` 结算明细生成函数：按 M5 的确认口径调整当前“80%结算额再留10%”规则，保留历史明细快照、版本/生效日期及回滚规则；不得在基数不明时直接乘 `0.95`；对应 D4。
- 不涉及层及理由：银行流水的导入、认领、候选、分配已经有真实前后端/API/表链，当前不扩展到全量对账、会计凭证或其他财务模块。
- 影响范围与回归风险：自动提成将影响费用新增、费用编辑、案件人员编辑、内部提成付款、ROI 分摊和结算；比例或留存变更会影响历史结算、归档审核、付款包与财务报表，必须以生效边界隔离历史记录。

## 7. 验证清单
- [ ] 自动化测试：覆盖代理费新增、编辑、案件人员变更、员工方案生效期切换、重复员工、离职员工、比例总额超限和人工覆写。
- [ ] 生产构建：前端 TypeScript/Vite 与后端相关测试/编译。
- [ ] API 成功路径：创建代理费后生成可追溯的人员/比例/金额快照；变更人员后仅允许规定状态重算。
- [ ] API 失败路径：无关联案件、角色缺失、无有效方案、多人比例冲突、已付款/已结算记录重算请求必须明确阻断。
- [ ] 数据持久化及刷新回读：验证费用 JSON 明细、`HrSubrecord` 引用快照、付款包、ROI 和结算列表一致；不以 UI 短暂显示代替回读。
- [ ] 权限、角色和历史数据：分别验证经办律师、开庭律师、律师助理、财务人员和管理员；历史结算按生效规则不被重算。
- [ ] 结算口径：在业务确认金额基数与历史范围后，以一个可清理的 `CODEX-*` 回款验证确认后的公式、未归档状态、归档释放、审核、拒绝和回滚。
- [ ] 银行流水：导入 -> 认领客户 -> 候选案件费用 -> 分配 -> 合同应收回读；验证律师确认角色的权限边界。
- [ ] 测试数据及临时进程清理：所有验证数据、附件、流水、结算、审批/事件精确清理。
- [ ] 用户验收项：业务方先确认“自动提成”的角色、比例、取整、覆盖和历史重算规则，以及“未归档扣留5%”的金额基数、生效时间与历史处理范围。

## 8. 实施记录
- 实际改动提交：无；本次仅新增本文档。
- 与修改清单不一致之处及原因：按用户要求只读定位，不实施 M1-M5，不读写数据库，不启动浏览器或测试。
- 测试结果与证据路径：未运行业务测试、构建或 API；CodeGraph `status` 已确认索引最新，并对费用提成、归档结算、银行回款执行 `codegraph explore`，结果指向 `FinanceFeeCommissionDetailInput`、`IncomingAllocationModal`、`FinanceCenterView` 和 `app/core/finance.py`。补充检索仅限相关路径，未读取 `sfhc/`。
- 发布状态：未发布 / 待业务规则确认。

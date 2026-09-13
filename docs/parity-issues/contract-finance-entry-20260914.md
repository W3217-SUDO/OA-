# 合同付款与开票入口返工

## 1. 清单原文
本次为直接问题，不属于 Excel 批次。
- “合同付款 合同 付款 这里是可以点击的 ，没有跟旧的系统对齐”
- “合同开票也是的”
- “点击应该回到这个节目”及纠正“界面”
- “审批不审批都可以”
- 状态：已定位，实施中，待用户验收。

## 2. 截图分析
- 209cdd57-f2e6-4b9d-8c03-4c791935ef56：合同中心 > 我的合同，选中审批中合同；底部合同付款灰色，合同开票可点击。
- 8a22cb48-a46b-4527-bee9-58902f3da6ae：目标为完整申请付款页面；包含付款信息填写/提交申请/财务审批/财务付款四阶段、合同/客户信息、交款人、收款单位、开户行、账号、备注及付款费用明细。
- 图片为本轮附件，逐张阅读；不是相邻表格图片。VibeHub 已查询脱敏术语 disabled state，匹配 State；术语不替换用户要求。

## 3. 旧系统实现
源码根为旧系统归档源码/SH.CRM.WEB。
- Scripts/FCM/Contract/FCM.Contract.js：btnContractPaymentApply、btnContractInvoiceApply 检查选中合同和归档状态，不检查审批通过。PaymentApply 调用 addtabs 进入 FAM/AP/PaymentCreate；InvoiceApply 进入 FAM/Invoice/InvoiceDetailCreate。多合同开票要求同客户。
- Areas/FAM/Controllers/APController.cs::PaymentCreate：根据合同读取客户、付款对象，交款人默认为客户名，返回 Payment/Create。
- Areas/FAM/Views/AP/Payment/Create.cshtml：完整页面、四阶段、收款单位选择及账户回填、逐行付款明细、提交。
- Areas/FAM/Controllers/InvoiceController.cs::InvoiceDetailCreate：客户抬头和税务信息预填，按合同查未开票费用，返回完整开票页。
- 未执行旧系统浏览器操作或写入。源码与用户截图是本次证据。

## 4. 新系统当前实现
- 前端 contractWorkflowPolicy.mjs::contractListActionPolicy 将付款限制为审批通过；列表、打开与提交共用该策略。
- ContractCenterPage.tsx 打开 ContractPaymentModal/ContractInvoiceModal；不是独立申请页面。
- 后端 areas/contract/router.py::create_contract_payment_application 额外拒绝审批中及所有非审批通过/已完成合同。
- 开票候选与创建接口使用 core/contracts.py::_contract_allows_downstream_creation，该通用规则拒绝草稿，造成未提交审批合同仍不可开票。
- 数据库 BusinessRecord 保存合同与付款/发票；付款使用 data.lines 及 ContractPaymentLine，发票关联费用。审批不通过不应影响进入财务申请，但财务单自身审批仍保留。

## 5. 差异与返工根因
上次整改关注费用归属与提成链路，遗漏合同列表入口的审批门禁和完整页面载体；不能只在弹窗内部修复。
合同审批状态与付款/开票申请的审批流程被混淆。前后端限制不同，还存在按钮可点而候选加载被拒绝的情况。

## 6. 精确修改清单
- [x] contractWorkflowPolicy.mjs：付款/开票统一允许未审批、审批中及审批通过合同；保留归档和终止阻断。
- [x] core/contracts.py：新增财务专用有效合同判定，允许草稿，不改变新建案件/调查的门禁。
- [x] areas/contract/router.py、areas/finance/router.py：付款提交、开票候选和创建使用同一财务判定，删除付款审批通过白名单。
- [x] App.tsx、ContractCenterPage.tsx：付款/开票独立路由、刷新恢复合同上下文、返回入口、错误显示；按合同菜单权限开放。
- [x] ContractModals.tsx：付款和开票改为无遮罩完整页面，付款四阶段、合同信息、收款账户、明细；不伪造申请编号。
- [x] models_shared.py、付款提交：交款人和费用行备注使用现有 JSON 数据字段保存，无数据库迁移。
- [x] core/finance.py、contract/types.ts：付款候选补充案件类型及实际 inform_date，旧标的没有通知日期时留空，不以创建时间冒充。
- 本轮不扩大为多合同合并发票改造；不移除金额、费用归属、重复申请、归档或数据范围校验。

## 7. 验证清单
直接问题依用户规则不执行浏览器及业务测试，完成本地生产构建、Python 编译/应用加载、差异检查及部署健康检查。
用户验收：未审批/审批中合同分别进入付款与开票完整页面；正确合同与客户上下文；付款账户回填；费用勾选与金额录入；提交后财务单据可见；归档或终止合同及超额申请仍阻断。
本轮不创建测试数据，不操作既有业务记录。

## 8. 实施记录
CodeGraph status 最新；explore 确认 ContractCenterPage 与共享 contractWorkflowActionPolicy 调用关系，未覆盖的旧源码和路由片段通过定向读取补齐。
发布状态：尚未发布。完成后以本次发布队列和回执记录准确版本、提交、健康结果；未收到用户确认前不标记已验收。

2026-09-14：首轮本地生产构建通过；最终代码 Python 编译及 app.main 加载通过（772 个应用路由），CodeGraph 已同步。正式版本构建和部署继续执行，不将编译结果当作业务验收。

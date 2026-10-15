# 10.15 第8至14行集中定位汇总

## 范围与规则

本批按问题处理 skill 完成：逐行读取原文，逐张读取同一行的全部截图；每行拆分多个子问题，保留截图、旧系统证据、当前代码入口和原子验收项。当前阶段只完成定位文档，未写入完成状态、未创建 CODEX 测试数据、未部署。

## 行级结论

| 行 | 子问题 | 主要新系统入口 | 旧系统证据 | 下一步 |
|---|---|---|---|---|
| 8 | 所有财务/平台财务导出模板统一“上海沪知律师事务所”；页面、打印、DOCX/Excel 回读一致 | `PaymentDocument.tsx`、`FinanceCenterPage.tsx`、`paymentsActions.tsx`、`printWindow.ts` | image65、旧模板说明 | 建立导出入口矩阵，真实文件回读 |
| 9 | 案号/法院案号/收款账户/备注可复制并保持真实关联 | `CopyValue.tsx`、`PaymentDocument.tsx`、列表/详情/打印入口 | image67 | 逐字段剪贴板回读和关联点击 |
| 10 | 打印预览隔离且完整；所有导出生成真实可读文件 | `PaymentDocument.tsx`、`printWindow.ts`、`paymentsActions.tsx` | image70/71 | CODEX 单据导出、DOCX/Excel 读取、浏览器打印 |
| 11 | 回滚后我的请款单可编辑、保存、再次提交；到账分配时先撤销 | `ContractPaymentEditPage.tsx`、合同 router、`FinanceFeeModals.tsx` | image73 | 状态、阻断、落库、审批链闭环 |
| 12 | 回滚状态显示“创建待提交”，编辑页有修改后再提交动作 | `ContractPaymentEditPage.tsx`、`paymentLifecycle.mjs` | 无旧图，按新问题处理 | 普通/合同两类费用分别回读状态和事件 |
| 13 | 所有回滚操作的列表/接口状态统一为创建待提交 | `fee_workflows.py`、`paymentLifecycle.mjs`、`FinanceCenterPage.tsx` | image76 | 回滚接口、列表筛选、权限与事件日志 |
| 14 | 公共搜索/首行筛选/首行数据固定；超时可重试；删除权限与终态门禁 | `FinanceCenterPage.tsx`、`FinanceCenterView.tsx`、回款/结算/内部提成页面及后端权限 | image79 | CodeGraph 追踪公共壳层、真实查询和删除 API |

## 集中实施前的共享风险

1. 第8、10行共享打印和下载数据源，必须先统一模板上下文，再分别验证抬头和文件完整性。
2. 第11至13行共享回滚状态和编辑提交链，但验收证据要按行分开，不能用一条接口响应替代三行。
3. 第14行同时包含公共布局、查询失败和删除权限，不能只改前端 CSS 或隐藏按钮；后端必须有状态和角色门禁。
4. 所有写入验收使用本轮唯一 `CODEX-*` 前缀，完成后精确删除业务记录、事件/审批、附件和临时导出文件并回查零残留。

## 当前状态

- 定位文档：第8至14行各一份，另有本汇总。
- I8至I14：保持空白，等待集中修复和完整验收。
- G8至G14：待写入“定位完成”及文档路径；不写完成结论。

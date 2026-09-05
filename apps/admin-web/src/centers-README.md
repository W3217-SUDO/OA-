# 前端中心页目录（对照旧系统 GD.CRM 架构）

新系统前端按旧系统 GD.CRM 的 Area 结构拆分。

## 页面对应关系

| 新系统页面 | 旧系统模块 | 当前行数 | 拆分状态 | 目录 |
|-----------|-----------|---------|---------|------|
| FinanceCenterPage | FAM/FAS/FSC (财务) | 14304 | 待拆分 | finance-center/ |
| CaseCenterPage | Legal (案件) | 7997 | 待拆分 | case-center/ |
| InvestigationCenterPage | CIT (调查) | 5327 | 拆分中 | investigation-center/ |
| IprCenterPage | IPR (知产) | 3964 | 拆分中 | ipr-center/ |
| ContractCenterPage | CMS (合同) | 3552 | 待拆分 | contract-center/ |
| SealCenterPage | Legal/Seal (用印) | 3427 | 待拆分 | seal-center/ |
| CustomerCenterPage | CRM (客户) | 2801 | 待拆分 | customer-center/ |
| SystemCenterPage | System (系统) | 2527 | 待拆分 | system-center/ |
| DocumentCenterPage | AWS (文书) | 2491 | 待拆分 | document-center/ |
| TaskCenterPage | TP (任务) | 2253 | 待拆分 | task-center/ |

## 拆分原则

1. **父组件保留状态，子组件接收 props** - 不引入新的状态管理
2. **按 Tab 拆分** - 每个 Tab 一个子组件文件
3. **详情弹窗/Drawer 独立** - Modal/Drawer 内容独立为组件
4. **hooks 提取** - 每个 Tab 的数据加载逻辑提取为自定义 hook
5. **零功能变更** - 纯架构重构，不改变业务逻辑

## 拆分批次

| 批次 | 页面 | 预估难度 | 状态 |
|------|------|---------|------|
| 第1批 | IprCenterPage | 低 | 进行中 |
| 第2批 | InvestigationCenterPage | 中 | 进行中 |
| 第3批 | Customer + Document + Task + System | 低-中 | 待开始 |
| 第4批 | SealCenterPage + ContractCenterPage | 中 | 待开始 |
| 第5批 | FinanceCenterPage - 简单Tab | 中 | 待开始 |
| 第6批 | FinanceCenterPage - 核心Tab | 高 | 待开始 |
| 第7批 | CaseCenterPage - 详情Tab | 高 | 待开始 |
| 第8批 | CaseCenterPage - 列表+新建 | 高 | 待开始 |

# 财务中心旧数据可见性审计

- 日期：2026-10-09
- 问题原文：财务跟我说，除了回款所的旧系统的数据在新系统都没有显示出来，在平台财务中心跟财务中心
- 任务类型：既有功能缺陷/新旧数据可见性对齐
- 审计范围：平台财务中心、财务中心的前端数据入口、API 路由与线上只读数据库统计；未修改代码、数据库或部署。

## 新系统入口与请求链路

1. `apps/admin-web/src/finance/services/queriesActions.tsx:520-834` 的 `load()`：
   - 费用/请款默认请求 `GET /records?module=finance&page_size=100`；
   - 发票请求 `GET /records?module=invoice&page_size=100`；
   - 退款、结算、交易、对账分别请求现代 `refund`、`finance_settlement`、`/finance/transactions`、`/finance/reconciliations` 等实体；
   - 这些请求都没有并入 `legacy_finance_records`、`legacy_finance_allocations`、`legacy_finance_files` 或 `legacy_finance_audits`。
2. `apps/admin-web/src/PlatformFinancePage.tsx:740-750` 的 `loadRows()`：
   - 回款类请求 `GET /finance/incoming-payments`；
   - 其他平台财务页面按类别请求 `GET /records?module=finance` 或 `GET /records?module=invoice`；
   - 没有旧财务账本并入逻辑。
3. `apps/admin-web/src/finance/FinanceStandardTabsView.tsx:168-233`：
   - 旧财务数据只在用户主动切换“历史财务账本”标签后，通过 `GET /finance/legacy-history` 加载；
   - `LegacyHistoryPanel.tsx:213-214` 明确提示历史请款、回款、开票及付款打包“与实时财务口径完全分离”，因此它不会出现在费用管理、发票申请、退款、结算等常规列表。
4. 后端 `apps/api-server/app/areas/finance/router.py:893-1148`：
   - `/finance/legacy-history` 只读 `legacy_finance_records` 及其分配、文件、审批子表；
   - 该接口没有被常规 `/records` 查询或各财务业务查询调用。

## 线上只读数据库证据

生产数据库使用只读事务统计，未输出业务明细：

- `business_records`：`finance=384`、`invoice=107`、`refund=16`、`contract_payment=1`。
- `business_records.module='finance'` 中：
  - `legacy_kind='ap_payment'`：100 条；
  - `legacy_source='PRD_CRM_SH_20190320'`：200 条；
  - 其余 184 条没有 `legacy_source`，属于现代或早期转换记录；
  - 状态含 `历史数据=8`、`已登记=201`、`已付款=74` 等。
- `business_records.module='invoice'` 中：`legacy_kind='invoice'` 100 条，另有 7 条无 `legacy_kind`。
- `business_records.module='refund'`：16 条均无 `legacy_kind`；`contract_payment` 1 条无 `legacy_kind`。
- 旧账本实体表 `legacy_finance_records`、`legacy_finance_allocations`、`legacy_finance_files`、`legacy_finance_audits` 均存在，但当前线上记录数为 0；因此 `/finance/legacy-history` 本身也没有可显示的旧账本。
- `incoming_payments` 有 `bank_import=45`、`manual=8`、`unknown=100`，回款入口有独立现代数据，所以用户会感觉“回款旧数据还能看到”。

## 根因

旧 FAM 财务数据没有形成一套完整、可查询的历史财务投影：回款被导入 `incoming_payments` 或部分费用记录，部分请款/发票被降级写入现代 `business_records`，而内部费用、付款打包、付款/发票对象及审批、发票文件、退款/结算等旧表数据既没有完整导入到现代模块，也没有填入 `legacy_finance_*` 历史账本。前端常规财务列表只查询现代模块，因此这些数据天然不会显示；只增加前端筛选不能修复数据缺失。

## 最小修复范围

1. 以旧 FAM 源表为权威，补齐并可重复运行导入：请款、内部费用、付款打包、发票及发票对象/文件/审批、退款和结算/分配；为每条记录保留源表与旧 ID，使用稳定的案件/合同/客户映射，记录未映射/孤儿原因。
2. 先确定产品口径：
   - 若要求旧记录在现有“费用管理/发票/退款/结算”中直接出现，需要后端建立统一历史+实时只读 read model，统一分页、筛选、状态和权限，再让两个前端入口调用该 read model；
   - 若要求先可查可追溯，可先让“历史财务账本”正确填充全部 FAM 数据，但这仍不能满足“常规平台财务中心/财务中心列表显示”的要求。
3. 导入完成后再补 UI 映射与详情只读标记，避免把历史记录误当成可继续审批、付款或退款的实时记录。

## 审计状态

- 代码：未修改。
- 数据库：仅只读统计，未写入。
- 部署：未执行。
- 页面业务验收：待主任务修复后由用户在 8089 验收。

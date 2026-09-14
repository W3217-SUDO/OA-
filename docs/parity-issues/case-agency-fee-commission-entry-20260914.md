# 案件代理费与新增提成入口返工

## 1. 用户原文

- “这个跟旧的系统不一样啊”
- “这是新增提成哪一步”
- “这个前端好像也没有同步吧”
- 当前状态：返工实施中。

## 2. 截图分析

### 新系统截图 `codex-clipboard-67380691-8b8c-4876-a852-50335c75f2a5.png`

- 所属页面：案件中心 > 案件详情 > 律所费用 > 新增案件费用 > 新增代理费。
- 可见对象：一条律师代理费草稿输入行。
- 可见步骤与按钮：顶部“新增费用 / 申请付款”，底部“下一步 / 取消”。
- 用户标注：费用类型“律师代理费”以及其下方“员工提成：自动计算 / 手动录入”。
- 实际异常：代理费新增页混入提成计算方式，却没有显示旧系统独立的“新增提成”工作区；代理费仍展示“申请付款”第二步。

### 旧系统 PPT 第57页三张截图

- 第一步“新增费用”只录入案号、费用类型、金额、备注并可增减行。
- 第二步“申请付款”明确提示“代理费不允许付款”。
- 本页没有在新增代理费行内录入员工提成。

## 3. 旧系统实现

- 律所费用入口：`SH.CRM.WEB/Areas/Legal/Views/CaseFee/PartialView/CaseFeeList.cshtml`。
- “新增代理费”调用案件费用 `MultiCreate`；“新建提成(选择代理费)”是同一“新增案件费用”菜单中的独立项目，调用 `InternalFee.MultiOpenByCaseFee`。
- `Scripts/Legal/Case/Legal.Case.js::MultiOpenByCaseFee` 要求先选择代理费，再加载 `/FAM/InternalFee/MultiCreateByCaseFee`。
- `Areas/FAM/Views/InternalFee/InternalFee/MultiCreateByCaseFee.cshtml` 的独立右侧工作区标题为“新增提成”，列为案号、费用类型、支付对象、基数、参考提成、实际金额、备注、操作，提交按钮为“申请付款”。
- PPT 第86页说明正常归档前先确认到账、核算实际代理费、人工计算内部提成并经办律师审核，再在系统中新建内部提成。

## 4. 新系统当前实现

### 前端

- `apps/admin-web/src/legal/CaseCenterPage.tsx` 在单条编辑和批量新增代理费行内渲染 `FeeCommissionEditor`，因此出现截图中的自动/手动单选。
- `apps/admin-web/src/legal/services/financeActions.tsx::openCaseFee/createCaseFee` 默认给代理费写入 `commission_mode=automatic`，创建后无条件进入付款第二步。
- `apps/admin-web/src/legal/CaseDetail/CaseFeesPanel.tsx` 已有独立的“新建提成(选择代理费)”菜单项，并调用 `openCaseCommission`。
- `apps/admin-web/src/finance/FinanceCenterView.tsx` 和 `paymentsActions.tsx::createFee` 也把提成编辑器及提成载荷混入普通代理费创建/编辑。

### 后端

- `apps/api-server/app/core/finance.py::_finance_fee_commission_payload` 在代理费未显式传提成方式和明细时仍默认 `automatic`，会在创建代理费时派生提成明细。
- 独立提成的权威入口为 `GET /cases/{case_id}/commission-preview` 和 `POST /cases/{case_id}/commissions`，按所选代理费生成内部费用及付款申请。

### 数据库

- 代理费和内部提成都存入 `business_records`；通过 `data.case_id`、`data.source_fee_id`、`data.source_fee_no` 等软关联保持来源链。
- 本次不新增字段、不迁移或修改既有数据。历史已保存的 `commission_mode/commission_details` 保留读取兼容。

## 5. 新旧差异和根因

| 编号 | 位置 | 旧系统 | 新系统 | 根因 |
|---|---|---|---|---|
| D1 | 新增代理费第一步 | 只录代理费字段 | 混入自动/手动员工提成 | 复用通用 `FeeCommissionEditor` 时没有保持代理费与内部提成的流程边界 |
| D2 | 新增代理费提交后 | 代理费不允许付款；提成另行新建 | 所有费用无条件进入“申请付款”第二步 | `createCaseFee` 未按费用类型筛选可付款记录 |
| D3 | 财务费用创建/编辑 | 普通代理费与新增提成分开 | 代理费表单也携带提成载荷 | 两个入口采用了同一错误的内嵌设计 |
| D4 | 后端默认值 | 提成从独立入口新建 | 空提成载荷仍默认为自动生成 | `_finance_fee_commission_payload` 的缺省分支把“未提供”解释成“自动” |

## 6. 精确修改清单

- [x] M1 `CaseCenterPage.tsx`：删除新增/编辑代理费表单内嵌的 `FeeCommissionEditor`；保留独立“新建提成(选择代理费)”入口。
- [x] M2 `financeActions.tsx::openCaseFee/createCaseFee`：普通代理费不发送提成模式或明细；代理费单独保存后关闭，混合费用只把可付款记录带到第二步。
- [x] M3 `CaseCenterPage.tsx`：代理费单独新增时只显示“新增费用”步骤，主按钮显示“保存”。
- [x] M4 `FinanceCenterView.tsx`、`paymentsActions.tsx::createFee`：删除普通代理费表单的提成编辑器和提成载荷。
- [x] M5 `finance.py::_finance_fee_commission_payload`：未显式提供提成模式时缺省为空的人工模式，不再随代理费创建自动派生；显式自动模式及历史数据兼容不变。
- [x] M6 更新聚焦自动化测试，覆盖入口可见、代理费表单无内嵌提成、代理费不进入付款步骤、后端缺省不自动派生。
- 不涉及数据库迁移和线上数据写入。

## 7. 验证清单

- [x] 前端聚焦测试：3 个文件，8/8 通过。
- [x] 后端聚焦测试：`finance_agency_fee_employee_commission_row24_test.py`，7/7 通过。
- [x] TypeScript/生产构建：`npm.cmd run build`，5836 modules 通过。
- [x] Python 编译检查。
- [x] `git diff --check`。
- [ ] 部署后只检查版本、静态资源、服务、API/Web 健康与严重错误日志。
- [ ] 用户验收：新增代理费页不出现员工提成；代理费保存后不进入付款；选中代理费后“新建提成(选择代理费)”打开独立新增提成工作区。

## 8. VibeHub 术语核对

- 已用脱敏候选词调用 resolver；返回结果与本问题不可靠相关，因此未强行补充术语。

## 9. 实施记录

- 相邻历史测试中存在多项与本次无关的旧路径静态断言失败：测试仍读取已改为 re-export 的 `src/CaseCenterPage.tsx` 或已拆分的 `app/main.py`；本次聚焦测试已改为读取真实实现文件，生产 TypeScript 构建通过。
- 实际改动提交：待填写。
- 发布状态：未发布。

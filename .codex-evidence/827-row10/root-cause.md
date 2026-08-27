# 8.27 第10行根因追踪

## 旧系统只读链路

- 五类案件的新建模板均提供必填 `Case.Basic.ContractNo` 下拉：民事、刑事、行政及国家赔偿、法律顾问、仲裁。
- `Scripts/Legal/Case/Legal.Case.Basic.Invoke.js` 的客户选择器回调固定调用 `contract.Contracts.List`。
- `Scripts/Legal/Case/Legal.Case.js` 的 `contract.Contracts.List` 读取 `Case_Basic_CustomerNo`，调用 `POST /FCM/Contract/GetContractListByCustomerNo`，并将该客户合同填充到 `Case_Basic_ContractNo`；无合同则显示“该客户下未存在合同,请新建合同”。
- 同一脚本的统一提交逻辑先校验客户，再强制校验合同，随后同时提交 `Case.Basic.CustomerNo` 与 `Case.Basic.ContractNo`。
- `Areas/FCM/Controllers/ContractController.cs` 调用 `ContractService.GetBasicContractListByCustomerNo(customerNo)`；`Areas/Legal/Controllers/CaseController.cs` 将模型交给 `CaseService.CreateUpdate`。归档源中服务/仓储实现以编译程序集提供，未发现对应 C# 源文件，因此只读证据边界止于控制器调用与页面提交模型；数据库关联字段由案件 `CustomerNo`、`ContractNo` 共同保存。

## 新系统链路与根因

- 所有普通案件类型共用 `apps/admin-web/src/CaseCenterPage.tsx`；类型路由分别映射为 `case-new-criminal`、`case-new-administrative`、`case-new-counsel`、`case-new-arbitration`。
- 根因：合同 `<Select>` 使用 `disabled={initialView !== "case-new" || Boolean(contractPrefill?.id)}`。因此除通用 `case-new`（截图中的正常民事入口）外，所有点名的类型专属路由均被永久禁用。
- 次生缺陷：`buildCaseContractOptions` 返回全部可见合同，没有按当前客户过滤，不符合旧系统“先选客户，再加载该客户合同”的联动语义。
- API `GET /cases/eligible-contracts` 只返回当前角色数据范围内且状态属于 `CASE_SOURCE_CONTRACT_STATUSES` 的合同。
- `POST /cases` 重新校验案件类型新建权限、合同可见性/模块/状态、合同唯一有效客户绑定、请求客户与合同客户一致、有效部门，并把 `contract_id`、`contract_no`、`customer_id`、`customer_no` 持久化到案件 `BusinessRecord.data`；数据库模型无需新增字段。

## 整改范围

1. 所有类型专属新建路由在已选客户时允许打开合同下拉；合同预填入口仍锁定客户与合同。
2. 合同候选仅显示当前客户的可见、状态合格合同；切换客户时清除不再匹配的合同及其自动派生值。
3. 添加前端联动回归与后端权限/一致性聚焦测试；逐一浏览器验收刑事、行政及国家赔偿、法律顾问、仲裁入口。

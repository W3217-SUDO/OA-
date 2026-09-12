# [待确认] CRM 客户分配功能新旧一致性审计

## 前端位置
- 发现日期：2026-09-12；来源：主动审计，基于反编译服务层源码的字段级核对。
- 菜单：客户管理 -> 我的客户/部门客户/公司客户/公海客户 -> 更多操作/右键 -> 分配客户。
- 路由：customer-mine、customer-dept、customer-company、customer-public（公海需先领取）。
- React：`crm/CustomerCenterPage.tsx` 第 1285 行 action 菜单 `key==="assign"`；第 1310 行触发 `startAssign(target)`；第 545-571 行 `startAssign` / `assignCustomer` 弹框选择管理人后调用 `PUT /customers/{id}/managers`。
- 后端：`PUT /customers/{customer_id}/managers`，`update_customer_managers`（`router.py` 第 989-1023 行）。

## 新旧对比与依据

### 旧系统真实行为（反编译核实）

反编译源文件：
- 服务层：`Dchien.Legal.Service/CRM/Customer/CustomerService.cs` —— `CustomerOwnerChange` 方法
- 数据层：`Dchien.Legal.DataAccess/CRM/Customer/CustomerDao.cs` —— `CustomerOwnerChange` 方法
- 合同级联：`Dchien.Legal.DataAccess/FCM/Contract/ContractDao.cs` —— `ContractOwnerChange` 方法（已核实 SQL）

**CustomerService.CustomerOwnerChange(customerIds, currentOwner)** 执行流程：
1. 事务内依次执行：案件 owner 变更 → 合同 owner 变更 → 客户 owner 变更 → 调查 owner 变更 → 写客户事件日志。
2. 级联变更：客户分配时，该客户关联的案件、合同、调查的 owner 同步变更。
3. 事件日志：Content = "客户重新分配给{currentOwner}."。
4. 支持批量：`customerIds` 为 `List<long>`，可单客户或多客户批量分配。
5. 无备注/原因字段。

**CustomerDao.CustomerOwnerChange 实际 SQL：**
```sql
UPDATE CRM_Customer
SET CustomerOwner = @CurrentOwner,
    Holder = @CurrentOwner,
    BusinessOwner = @CurrentOwner
WHERE CustomerId = @CustomerId
```

关键观察：SQL 只更新 `CRM_Customer` 表的 `CustomerOwner`、`Holder`、`BusinessOwner` 三个字段。

### 新系统行为

`update_customer_managers` 端点（`router.py` 第 989-1023 行）：
- 权限：`_require_record_owner_or_manager`（owner 或管理人可操作）。
- 状态校验：公海客户禁止直接分配，需先领取（第 1002 行 409 拒绝）。
- 字段更新：
  - `customer.owner` = 新管理人列表首位（第 1017 行）。
  - `customer.data.customer_managers` = `_prioritize_new_customer_managers(existing, requested)` —— 新指定的管理人排首位，原管理人保留在列表中（第 1005-1007 行，`crm.py`）。
  - `customer.data.assignment_history` 追加记录（from_owner / to_owner / managers / operator / comment / created_at）。
- 事件日志：`_customer_event(customer, "更新客户管理人", identity, ...)`。
- 单客户操作，无批量分配入口。
- 不更新 `department` 字段。
- 不级联更新关联案件、合同、调查的负责人。

### 逐项对比

| 对比项 | 旧系统 | 新系统 | 一致性 |
|--------|--------|--------|--------|
| 入口名称 | 分配客户 | 分配客户 | 一致 |
| 操作对象 | 单客户 / 批量 | 单客户 | 有差异（新系统缺批量） |
| 更新 CustomerOwner / Holder / BusinessOwner | 是（3 字段） | owner 字段对应 | 基本一致（字段映射不同） |
| 修改 customer_managers / CRM_Customer_Coordinator | 否（不碰协调人表） | 是（新人加首位，原管理人保留） | 有差异（新系统多做） |
| 更新部门 / 公司 | 否（SQL 无 DepartmentId / CompanyId） | 否 | 一致 |
| 级联更新案件 owner | 是 | 否 | **有差异（中等风险）** |
| 级联更新合同 owner | 是 | 否 | **有差异（中等风险）** |
| 级联更新调查 owner | 是 | 否 | **有差异（中等风险）** |
| 客户事件日志 | 有（"客户重新分配给xxx."） | 有（"更新客户管理人"） | 基本一致（文案不同） |
| 备注 / 原因字段 | 无 | 有（comment，前端默认空） | 有差异（新系统多做） |
| 分配历史记录 | 无（仅事件日志） | 有（assignment_history 数组） | 有差异（新系统多做） |

### 关键问题答案（D1 / D2）

**D1：customer_managers 的处理方式**
- 旧系统：不修改 `CRM_Customer_Coordinator`（客户管理人/协调人）表，分配仅改 `CRM_Customer` 的 3 个 owner 字段。
- 新系统：把分配对象插入 `customer_managers` 列表首位，原管理人保留。
- 差异判定：新系统比旧系统多做了「把分配对象加入管理人列表」。按"菜单开放即动作开放"的原则，应作为新系统扩展功能保留，不视为回归缺陷。

**D2：department 是否随分配更新**
- 旧系统：`CustomerDao` 的 SQL 中无 `DepartmentId` 或 `CompanyId` 字段。`CustomerService` 虽接收 `departmentId` 和 `companyId` 参数，但仅传给 `CaseDao` 和 `ContractDao`，未传给 `CustomerDao`。客户分配不改变客户的部门和公司归属。
- 新系统：也不更新 department 字段。
- 结论：一致，无差异。

## 差异分析

### 中等风险差异：级联更新案件 / 合同 / 调查 owner

- **现象**：旧系统分配客户时，同一事务内同步更新该客户关联的所有案件、合同、调查的负责人为新 owner。新系统仅更新客户本身的 owner 和管理人。
- **SQL 证据（合同级联已核实）**：
  ```sql
  -- ContractDao.ContractOwnerChange
  UPDATE [dbo].[FCM_Contract]
  SET BusinessOwner = @CurrentOwner
  WHERE BusinessOwner = @OriginalOwner AND CustomerId = @CustomerId
  ```
  条件：按原 owner + 客户 ID 精准匹配，只更新 BusinessOwner 字段。
- **影响**：客户分配后，其关联案件/合同/调查的负责人仍为原 owner，出现"客户负责人与案件负责人不一致"的情况。业务员可能在客户列表看到新分配的客户，但进入案件列表发现不归自己管。
- **风险等级**：中等。涉及跨模块数据一致性，影响日常工作流转，但不涉及数据丢失或权限越权。
- **是否需修复**：需业务确认。若旧系统行为是业务规则（客户分配=全链路归属转移），则新系统需补充级联更新；若仅是历史实现巧合，则可保留现状。

### 低风险差异：无批量分配入口

- 旧系统工具栏支持勾选多客户后批量分配（`customerIds` 为 `List<long>`）。
- 新系统 action 菜单仅单客户分配。
- 按项目推进节奏，批量分配属可后补功能，不影响主流程对齐。

### 新系统扩展功能（非缺陷）

- 分配备注（comment）：新系统有，旧系统无。
- 分配历史（assignment_history）：新系统结构化记录，旧系统仅事件日志。
- customer_managers 管理人列表：新系统分配时追加而非替换，提供更丰富的协作信息。
- 以上均为新系统功能增强，按"菜单开放即动作开放"原则保留。

## 整改与验证计划

- 当前不做代码改动。
- 优先确认业务侧对"客户分配是否级联更新案件/合同/调查负责人"的预期：
  - 如需级联：在 `update_customer_managers` 中补充对 `legal_case`、`contract`、`investigation` 的 owner 更新，保持事务一致性，补充事件日志。
  - 如不需级联：关闭此差异项，标注为新系统行为更优（精细化权限控制）。
- 批量分配入口列入后续迭代，不纳入本轮对齐整改。
- 验证方案：
  - 创建客户 + 关联案件 + 关联合同 + 关联调查。
  - 分配客户给新用户 B。
  - 断言客户 owner / 管理人正确更新。
  - 根据业务确认结果，断言案件/合同/调查 owner 是否同步变更。
  - 断言事件日志与分配历史正确记录。
  - 断言公海客户分配被 409 拒绝。

## 当前状态

- 已完成反编译源码级审计，旧系统分配行为已核实（CustomerService 第 734-773 行 + CustomerDao 第 766-774 行）。
- 确认一致项：部门/公司不随分配更新、客户 owner 变更、有事件日志。
- 确认差异项（共 3 类）：
  1. **中等风险**：级联更新案件/合同/调查 owner —— 需业务确认是否修复。
  2. 低风险：无批量分配入口 —— 后续迭代补充。
  3. 新系统扩展：customer_managers 追加、分配备注、分配历史 —— 保留。
- 未浏览器验收、未提交、未部署。

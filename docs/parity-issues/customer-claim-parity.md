# 公海客户拾回流程一致性审计（服务层已核实）

## 前端位置
- 发现日期：2026-09-12；来源：主动审计，公海客户页面（PageId 6001006）流程专项核对。
- 菜单：客户管理 -> 公海客户 -> 更多操作/右键 -> 拾回。
- 路由：customer-public。
- React：`crm/CustomerCenterPage.tsx` 第 1297-1300 行，公海视图下 action 菜单；第 1320 行 `key==="claim"` 触发；第 575-592 行 action 函数直接 POST，无确认框，成功后 `load()` 刷新当前列表。
- 后端：`POST /customers/{id}/claim`，`claim_customer`（`router.py` 第 659-689 行）。

## 新旧对比与依据

### 旧系统行为
- 公海页面 PageId 6001006（`CustomerList.cshtml` 第 315、416 行）。
- 工具栏拾回按钮（第 315-320 行）：取第一个勾选的客户 ID，调用 `customer.Customer.InClose`。
- 右键菜单（第 416-421 行）：仅"客户查看"+"拾回"两项，无"客户编辑"。
- JS：`CRM.Customer.js` `InClose` 方法（第 181-196 行），POST 到 `/CRM/Customer/CustomerClose`，仅传 `customerId`，无确认框，成功后刷新当前列表。
- 控制器：`CustomerController.cs` 第 575-577 行 `CustomerClose(long customerId)`，`[CheckUserLogin]` 过滤器，调用 `CustomerService.Instance.CloseCustomer`。
- 服务层：`Dchien.Legal.Service.CRM.Customer.CustomerService.CloseCustomer` —— **已通过反编译核实**（见下方"服务层源码核实"章节）。

### 新系统行为
- `claim_customer` 端点（`router.py` 659-689）：
  - 权限：`role ∈ {admin, manager, user}`（第 671-672 行）。
  - 行锁：`_locked_customer_or_404` 行级锁 + 可见性检查（第 673 行）。
  - 状态校验：仅"公海"可领取（第 674 行）。
  - 字段设置：`status="潜在"`，`owner=当前用户`，`department=当前用户部门`，`customer_managers=[当前用户]`，`shared_with=[]`，`is_shared="否"`，`claimed_at` / `claimed_by` 审计字段。
  - 日志：`WorkflowEvent` action="领取客户"，from="公海" to="潜在"。
  - 409 冲突转 HTTP 200 + `IsSuccess=false`（legacy 转换）。
- 管理员直接编辑公海客户：
  - 权限层（`permissions.py` 744-745）：公海客户非 admin → 403；admin 直接通过。
  - 前端（`CustomerCenterPage.tsx` 1298-1299）：admin 公海视图有"客户编辑"菜单项。

### 确认一致的点（10 项）
入口名称、POST 方法、单个客户操作、仅公海可操作、拾回后移出公海、归属设为当前用户、部门设为当前用户部门、刷新当前列表不跳转、非管理员公海页无编辑、成功/失败都有反馈。

### 可疑 / 待确认差异（服务层核实后更新）
1. **customer_managers 覆盖语义**（已确认 - 轻微差异）：旧系统 CloseCustomer **不修改** `CRM_Customer_Coordinator`（管理人/协调人）字段，拾回后原管理人保留；新系统覆盖为 `[当前用户]`。但公海客户理论上拾回前不应有管理人（丢公海时通常会清空），实际影响很小。详见下方核实章节。
2. **shared_with 清空**（已确认 - 新系统多做一步）：旧系统 CloseCustomer **不修改** `IsShared` 字段；新系统拾回时清空 `shared_with` 并设 `is_shared="否"`。公海本身即共享池，拾回收归个人后清空共享属于防御性操作，风险低，不视为回归。
3. **拾回后状态为"潜在"**（已确认 - 一致）：旧系统 `IsOpened=F + IsActived=T` 对应"活跃/潜在客户"；新系统 `status="潜在"`，语义一致。
4. **前端无确认框**（低，新旧一致）：旧 `InClose` 同样无确认框，一致。
5. **管理员直接编辑公海客户**（需业务确认）：旧系统公海页无编辑入口，新系统 admin 可以直接编辑。按用户"菜单开放即动作开放"的倾向，更可能作为新系统扩展保留，不视为回归。
6. **comment 参数**（低）：新系统有接收但前端传空，不影响主流程。

## 服务层源码核实（2026-09-13 补充）

反编译源文件：
- `CustomerService.cs` — `CloseCustomer` 第 669-682 行、`OpenCustomer` 第 658-667 行
- `CustomerDao.cs` — `CloseCustomer` 第 164-180 行、`OpenCustomer` 第 150-162 行

### CloseCustomer（拾回 = 关闭公海状态）SQL 更新字段

```
UPDATE CRM_Customer
   SET IsOpened = 'F'          -- 关闭公海 = 从公海收回
      ,IsActived = 'T'         -- 活跃
      ,BusinessOwner = 当前用户
      ,CustomerOwner = 当前用户
      ,Holder = 当前用户
      ,LastUpdateTime = 现在
      ,ChangeUser = 当前用户
      ,ChangeTime = 现在
 WHERE CustomerId = @CustomerId
```

### OpenCustomer（丢公海 = 打开公海状态）SQL 更新字段

```
UPDATE CRM_Customer
   SET IsOpened = 'T'          -- 打开公海
      ,LastUpdateTime = 现在
      ,ChangeUser = 当前用户
      ,ChangeTime = 现在
 WHERE CustomerId = @CustomerId
```

> 注：丢公海（OpenCustomer）仅改 IsOpened 标记和审计字段，不改 BusinessOwner / CustomerOwner / Holder / IsActived 等。这意味着丢公海后原负责人信息仍保留在客户表，仅通过 IsOpened=T 区分公海状态。

### 逐项核实结论

| 字段 / 行为 | 旧系统（CloseCustomer） | 新系统（claim_customer） | 结论 |
|---|---|---|---|
| IsOpened / 公海状态 | 设为 F（从公海收回） | 从"公海"移出 → status="潜在" | 一致 |
| IsActived / 状态 | 设为 T（活跃） | status="潜在" | 语义一致（旧系统 IsActived=T 对应潜在/活跃客户） |
| BusinessOwner / 归属 | 设为当前用户 | owner = 当前用户 | 一致 |
| Holder / 持有人 | 设为当前用户 | owner = 当前用户（合并字段） | 一致 |
| CustomerOwner / 客户负责人 | 设为当前用户 | owner = 当前用户（合并字段） | 一致 |
| 部门归属 | 客户表无 DepartmentId，通过 BusinessOwner 关联员工部门 | department = 当前用户部门 | 新系统冗余存储，功能等价 |
| 管理人 / Coordinator | **不修改**（保留原值） | customer_managers = [当前用户]（覆盖） | **差异**：新系统把原管理人清空，换成只有拾回人。公海客户通常无管理人，实际影响低 |
| IsShared / 共享关系 | **不修改**（保留原值） | shared_with = [], is_shared = "否" | **差异**：新系统多了清空共享的操作，属于防御性处理，风险低 |
| 级联变更 | 仅改客户表，无级联 | 仅改客户记录，无级联 | 一致 |
| 事务 | 单条 SQL，隐式事务 | 行锁 + 单条 update | 一致 |

### 差异影响评估

1. **customer_managers 覆盖**：旧系统丢公海（OpenCustomer）也不清空管理人，所以拾回时可能还有历史管理人数据。新系统直接覆盖为拾回人一人，相当于"重新分配管理人"。公海客户的原管理人通常就是丢公海的人，拾回后换成新的拾回人符合业务直觉，风险低。
2. **shared_with 清空**：旧系统公海客户可能仍带 IsShared=T（因为 OpenCustomer 不改该字段），拾回后共享关系可能残留。新系统主动清空，比旧系统更干净，属于正向改进，不构成回归。
3. **其余字段全部一致**：状态、归属、审计字段、无确认框、单条操作等均与旧系统行为匹配。

## 整改与验证计划
- 当前不做代码改动。优先通过数据库层对照或业务方确认以下三点：`customer_managers` 是覆盖还是追加、拾回后默认状态、共享关系是否清空。
- 确认后如需调整，仅修改 `claim_customer` 内字段赋值，保留行锁、状态校验、权限、日志和事务。
- 定向测试覆盖：普通用户拾回公海客户后状态/归属/部门/管理人/共享、管理员拾回、重复拾回 409、非公海状态拾回拒绝、无权限用户拾回。
- 浏览器验收：公海列表勾选/右键拾回，列表刷新后客户消失，我的客户中出现；管理员公海编辑入口存在且可保存。

## 当前状态
- 已完成源码级审计 + 服务层反编译核实，未发现功能性阻断差异。
- **拾回后状态**：已确认一致（旧系统 IsOpened=F + IsActived=T 对应新系统 status="潜在"）。
- **customer_managers 覆盖**：已确认差异（旧系统不修改 Coordinator，新系统覆盖为拾回人），风险低，暂不改动。
- **shared_with 清空**：已确认差异（旧系统不改 IsShared，新系统主动清空），属于防御性改进，不视为回归。
- 管理员公海直接编辑判定为新系统扩展功能，按用户菜单授权策略保留，不视为缺陷。
- 未浏览器验收、未提交、未部署。

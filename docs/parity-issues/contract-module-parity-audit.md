# 合同模块对齐审计（初步）

- 审计日期：2026-09-13
- 证据来源：
  - 旧系统服务层：`SH.CRM.Service.Decompiled/Dchien.Legal.Service/FCM/Contract/ContractService.cs` + `ContractDao.cs`（反编译）
  - 旧系统实体：`Dchien.Legal.Entity/FCM/Contract/ContractStatus.cs`
  - 旧系统 WEB 层：`Areas/FCM/`（待深入）
  - 新系统后端：`apps/api-server/app/areas/contract/router.py` + `app/core/contracts.py`
- 状态：初步审计，未覆盖全部功能，未写测试，未验收

## 一、合同状态对比

### 旧系统（ContractStatus 枚举）

| 值 | 枚举 | 描述 |
|----|------|------|
| 1 | D | 待提交（草稿） |
| 2 | P | 审批中 |
| 3 | A | 审批通过 |
| 4 | R | 已驳回 |
| 5 | Archived | 已归档 |

### 新系统

从代码中可见的状态：草稿、已拒绝、审批中、已通过、已回收、已归档 等。

**待深入对比**：完整状态列表和流转路径。

## 二、合同删除对比

### 旧系统（ContractService.ContractDelete + ContractDao.ContractDelete）

```csharp
// ContractDao.ContractDelete — 逻辑删除
UPDATE [dbo].[FCM_Contract]
SET IsActived = 'F', ChangeTime = @ChangeTime, ChangeUser = @ChangeUser
WHERE ContractId = @ContractId
```

关键特征：
- **逻辑删除**：只更新 `IsActived = 'F'`
- **事务保护**：有 TransactionScope（整批原子）
- **无级联删除**：不删除关联的合同对象、费用、事件、审批记录等
- **无关联检查**：不检查是否有关联数据（应收、到账、案件等）
- **无权限校验**：服务层没有权限检查
- **无状态校验**：任何状态的合同都能删

### 新系统（_delete_contract_records）

关键特征：
- **物理删除**：直接从 `business_records` 表删除
- **事务保护**：有事务，失败回滚
- **级联删除**：合同对象、合同对象日志、合同事件、审批步骤、工作流事件、附件
- **严格关联检查**（删除前校验）：
  - 已有审批记录 → 不能删
  - 已有应收计划 → 不能删
  - 已关联到账记录 → 不能删
  - 已有付款申请明细 → 不能删
  - 已被其他业务关联 → 不能删
- **权限校验**：admin 或 owner 本人
- **状态校验**：
  - 回收站删除：只接受"已回收"状态
  - 公司合同删除：allow_company_contract 模式
  - 空合同删除：allow_empty_contract 模式

### ⚠️ 差异分析

| 维度 | 旧系统 | 新系统 | 评估 |
|------|-------|-------|------|
| 删除方式 | 逻辑删除（IsActived='F'） | 物理删除 | 新系统更彻底，但旧系统保留数据 |
| 关联检查 | 无 | 严格（5项检查） | 新系统更安全，防止误删有业务数据的合同 |
| 级联删除 | 无 | 有（对象/事件/审批/附件） | 新系统数据一致性更好 |
| 事务 | 有 | 有 | 一致 |
| 权限校验 | 服务层无 | 有（owner/admin） | 新系统更严格 |
| 状态校验 | 无 | 有（按接口区分） | 新系统更严谨 |

**结论**：新系统的删除功能在数据安全上明显优于旧系统。但需要确认：
- 旧系统是否有"合同回收站"恢复已删除合同？（根据 IsActived 逻辑，可能有）
- 法律行业合规性是否要求保留删除痕迹？

## 三、合同审批流程对比

### 旧系统（ContractService.ToAudit + ContractService.Audit）

审批流程关键特征：
- **固定审批流**：`AuditFlowNodeEntity.DEFAULT_FLOWID`，默认审批流
- **审批节点**：从 AuditFlowNodeDao 获取流节点列表
- **提交审批（ToAudit）**：
  - 状态从 1(待提交) → 2(审批中)
  - 初始化所有审批节点（Insert 多条 Audit 记录，状态=2/待审批）
  - 设置当前节点为第一个节点
- **审批（Audit）**：
  - 通过（A）：移到下一个节点；如果是最后节点，状态→3(审批通过)，并自动审批关联的公函
  - 驳回（R）：状态→4(已驳回)
  - 写审批日志（ContractAudit 表）
- **多轮审批**：AuditRoundId 支持多轮审批

### 新系统

新系统有独立的 `ContractApprovalStep` 表和审批流。从接口可见：
- 提交审批（submit）
- 审批（approve）
- 审批设置（approver-settings）
- 印章申请（seal-application）

**待深入对比**：审批流配置、节点数量、驳回逻辑、审批人设置方式。

## 四、客户 owner 级联更新（已核实）

旧系统 ContractDao 有 `ContractOwnerChange` 方法：

```csharp
UPDATE [dbo].[FCM_Contract]
SET BusinessOwner=@CurrentOwner
WHERE BusinessOwner=@OriginalOwner and CustomerId=@CustomerId
```

这证实了**客户分配（owner 变更）会级联更新该客户下所有合同的业务负责人**。

这是客户模块审计中提到的"级联更新差异"的直接证据：
- 旧系统：客户分配 → 案件 owner 变更 → 合同 owner 变更 → 调查 owner 变更
- 新系统：**待确认是否有同样的级联更新**

## 五、合同归档对比

### 旧系统（ContractService.ContractArchive）

- 直接把合同状态改为 5(已归档)
- 事务保护
- 无级联操作

### 新系统

有归档接口 `POST /contracts/{contract_id}/archive` 和归档列表接口。

**待深入对比**：归档条件、归档后的操作限制、归档审批流程。

## 六、下一步计划

| 优先级 | 审计点 | 说明 |
|--------|-------|------|
| 高 | 客户分配级联更新合同 owner | 直接影响客户模块审计结论 |
| 中 | 审批流程完整对比 | 审批节点、驳回、多轮审批 |
| 中 | 合同对象与费用 | 合同对象（ContractObject）及关联费用的创建/变更逻辑 |
| 中 | 合同回收站 | 旧系统是否有合同回收站（基于 IsActived） |
| 低 | 合同创建向导 | 字段与初始化逻辑对比 |
| 低 | 公函关联 | 审批通过后自动审批公函的联动逻辑 |

当前仅完成结构层面的初步审计，每个点都需要深入到代码细节。

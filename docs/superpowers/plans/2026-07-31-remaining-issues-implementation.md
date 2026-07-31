# 剩余问题清单 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 完成问题清单中未发布的 20 项业务修复，并一次性发布测试服务器。

**Architecture:** 以 FastAPI 服务端约束业务权限、关系和状态，React 页面只消费受控 API。归档系统只作为只读规则证据；每一组改动在工作树中经过 CodeGraph、定向审计、构建和 API/浏览器验收。

**Tech Stack:** FastAPI、SQLAlchemy、React、TypeScript、Ant Design、Docker Compose。

## Global Constraints

- 每次改代码前后运行 CodeGraph `status/sync/explore`。
- 不写补丁文件；使用 Git 提交恢复。
- 所有剩余条目完成后统一测试站发布；不直接修改 `current`。

### Task 1: 人事字段与权限边界

**Files:** `apps/api-server/app/main.py`、`apps/admin-web/src/HrCenterPage.tsx`、`apps/admin-web/src/OrganizationCenterPage.tsx`、`scripts/audit-menu-coverage.py`。

- [ ] 增加逾期扣款布尔字段及默认值、可审计更新和列表展示。
- [ ] 把部门权限配置迁移为角色权限，服务端以部门/人员关系执行数据范围。
- [ ] 以旧系统已有提成记录为默认来源，新增员工仍可编辑五类提成值。
- [ ] 验证账号可用状态即时限制登录；编译、审计、API 冒烟并提交。

### Task 2: 沟通记录附件与只读体验

**Files:** `apps/api-server/app/main.py`、`apps/admin-web/src/CommunicationLogPage.tsx`、`scripts/smoke-api.py`、`scripts/audit-menu-coverage.py`。

- [ ] 创建沟通记录专用附件关系、上传/下载/删除与客户范围校验。
- [ ] 限制文件夹式上传，要求 ZIP；其他普通文件类型允许上传。
- [ ] 验证客户名/编号列和“查看”只读弹窗不泄露编辑能力并提交。

### Task 3: 客户主数据与列表动作

**Files:** `apps/api-server/app/main.py`、`apps/admin-web/src/CustomerCenterPage.tsx`、相关 CSS 与审计/冒烟脚本。

- [ ] 人员字段改为目录搜索候选，保存稳定用户名；按旧系统规则生成客户编号。
- [ ] 增加合同/案件统计及受控筛选跳转；校正查询栏布局。
- [ ] 我的客户隐藏删除；公司客户可配置编辑/删除，关联合同或案件时服务端拒绝删除。
- [ ] 编辑表单与创建字段一致并允许合规变更管理人；提交构建与定向冒烟。

### Task 4: 客户范围、回收、共享与冲突

**Files:** `apps/api-server/app/main.py`、`apps/admin-web/src/CustomerCenterPage.tsx`、审计/冒烟脚本。

- [ ] 统一本人、部门、公司、来源人和多管理人范围谓词；公司列表排除回收/删除状态。
- [ ] 共享列表增加接收人列，且只暴露授权范围内的姓名。
- [ ] 按旧系统的精确名称冲突流程修复查询、空结果与只读详情。
- [ ] 验证角色绕过、分页、回收和关联阻断并提交。

### Task 5: 合同审批与客户门户激活

**Files:** `apps/api-server/app/main.py`、`apps/admin-web/src/ContractCenterPage.tsx`、`apps/admin-web/src/CustomerPortalPage.tsx`、审计/冒烟脚本。

- [ ] 合同最后一步合并为提交审批；无同步用印时进入合同只读详情而非审核页。
- [ ] 建立客户账号激活、设置密码、重置、失效与频率限制生命周期。
- [ ] 验证审批权限、状态流转及门户安全边界并提交。

### Task 6: 全量回归与一次发布

- [ ] 运行前端生产构建、Python 编译、菜单/客户端 API 审计、完整 API 冒烟及浏览器关键路径。
- [ ] 更新交接文档和工作簿完成状态，提交所有文档。
- [ ] 从测试服务器 `dev` 创建新 release，构建受影响镜像，切换 `current`，检查 `/health`、Compose 服务和浏览器验收。

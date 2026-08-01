# 员工列表批量删除对齐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不降低现有人事删除门禁的前提下，对齐旧员工列表的勾选和“删除选中”流程。

**Architecture:** FastAPI 提供专用预检与原子批量删除接口，二者复用单条删除的阻断规则。React 仅向接口提交当前选中的正式员工 ID，并在服务端预检后显示确认窗口。

**Tech Stack:** FastAPI、SQLAlchemy async、React、TypeScript、Ant Design、Node test runner。

## Global Constraints

- 仅修改本地 `dev` 工作副本；旧系统只读，禁止服务器部署或数据修改。
- 不删除、改名或降低既有扩展字段、单条删除、状态办理或账号管理功能。
- 删除必须整批预检；任一目标不合格即零删除。
- 每个小改动前后均在旧系统和本地页面对照记录。

---

### Task 1: 批量删除接口

**Files:** `apps/api-server/app/main.py`, `apps/admin-web/src/employeeBulkDelete.mjs`, `apps/admin-web/employeeBulkDelete.test.mjs`

- [ ] 写入失败测试：去重排序；空数组报“请至少选择一名员工”。
- [ ] 实现输入归一化、批量预检和同事务删除；任一阻断返回 409 且零写入。
- [ ] 运行 Node 单测、API 冒烟和提交。

### Task 2: 列表选择与确认

**Files:** `apps/admin-web/src/HrCenterPage.tsx`, `apps/admin-web/hrCenterVisibleBehavior.test.mjs`

- [ ] 写入失败测试：列表包含 `rowSelection` 与 `batch-deletion-impact`。
- [ ] 增加不可选账号占位行、删除选中按钮、预检反馈和确认提交。
- [ ] 运行前端测试、生产构建和提交。

### Task 3: 页面对照与完整验证

**Files:** `docs/hr-local-parity-verification.md`

- [ ] 在旧系统只读验证筛选、勾选、分页、删除选中与取消；本地用临时记录验证空选、阻断、成功删除和精确清理。
- [ ] 运行 `powershell -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1`，记录双方页面证据、差异、修改文件和测试结果并提交。

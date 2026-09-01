# 9.1 第 16 行处理结果

- 状态：代码与聚焦测试完成；未浏览器验收、未构建、未部署。
- 根因：删除接口使用 `identity.role == "admin"` 单字段判断；多角色账号的主 role 可能为 user、admin 位于 `role_ids` 次位，导致页面显示管理员能力但接口仍返回“仅管理员”。同一函数的 manager/task 管理员判断也存在同类问题。
- 修改：统一使用 `_identity_role_ids(identity)` 判断 admin/manager；调查父任务仍严格仅 admin 可删，普通用户即使是 owner 也拒绝；既有状态与子任务依赖门禁保持。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/investigation_admin_delete_role_ids_row16_test.py`、`.codex-evidence/9.1-row16/*`。
- 测试：第14/15/16行后端回归 4/4 通过；Python 编译与 `git diff --check` 通过。
- 数据库补丁建议：无需迁移。删除原截图无效任务前应只读核对确无子任务、线索和附件；由管理员在页面执行并保留审计/证据，不建议直接 SQL 删除。
- 主会话 Chrome 验收：使用截图同一多角色管理员 Fwl/范文林，选中对应草稿合同已删除且状态待分配的调查任务，点击删除，确认成功且刷新后消失；使用普通调查主管自建待分配记录确认提示仅管理员；再对有子任务记录确认依赖门禁阻断且父子均保留。

# 9.1 第16行验收记录

- reading-confirmation：仅处理工作表“9.1”第16行；已读取本行完整单元格文字和锚定截图 `C_image435.png`，本行无旧系统目标图、无补充返工文字，未读取未分配行。
- 状态：本地新系统 Chrome 真实业务验收通过；未提交、未构建、未部署、未改版本、未写线上数据库。
- 根因一：后端删除接口曾只检查单值 `identity.role`，多角色账号的管理员角色位于 `role_ids` 时被误判为普通账号。
- 根因二：后端角色集合判断修复后，前端仍对普通账号无条件渲染“删除”按钮，导致前后端权限表现不一致。
- 整改：后端统一通过 `_identity_role_ids(identity)` 检查账号全部角色；前端 Profile 补充 `role_ids`，将单值角色和全部角色合并判断，仅管理员账号在“待我分配的调查任务”页面看到删除按钮。后端仍作为最终权限边界。
- Chrome 验收（隔离 Web 15316 / API 18316 / SQLite）：`r16.multi` 的主角色为 user、角色集合包含 admin，页面显示删除按钮，选择 `DC-R16-ADMIN` 后实际删除成功并刷新消失；`r16.user` 可看到 `DC-R16-USER`，但页面不显示删除按钮。使用普通账号令牌直接 POST 删除接口，HTTP 200 业务结果为 deleted=0、failed=1、错误“仅管理员可以删除调查任务”，随后重新查询确认 `DC-R16-USER` 仍存在。
- 页面证据：`local-new-system-multi-admin-visible.png`、`local-new-system-multi-admin-deleted.png`、`local-new-system-ordinary-hidden.png`；进程证据为 `row16-api.out.log`、`row16-api.err.log`，原问题锚定截图为 `C_image435.png`。补验截图使用独立 Web 15490、API 18490、SQLite 和 `RQA-` 前缀夹具，由本行责任会话亲自操作 Google Chrome 生成并落盘。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/investigation_admin_delete_role_ids_row16_test.py`、`apps/admin-web/src/InvestigationCenterPage.tsx`、`apps/admin-web/investigationAdminDeleteRoleIdsRow16.test.mjs`、`.codex-evidence/9.1-row16/*`。
- 聚焦测试：前端 `node investigationAdminDeleteRoleIdsRow16.test.mjs` 通过；后端 `python -m unittest investigation_admin_delete_role_ids_row16_test.py contract_downstream_draft_gate_row15_test.py`，3/3 通过。
- 数据库补丁建议：无需迁移。对原问题中的失效调查任务，应先只读核对不存在子任务、线索、附件或其他真实下游依赖，再由管理员通过页面删除并保留审计证据；不建议直接 SQL 删除。
- 清理：Chrome 本行标签已关闭；隔离 API、SQLite、测试记录及临时凭据已在验收后清理；Web 15316 由主会话停止。

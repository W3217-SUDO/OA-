# 9.1 第17行验收记录

- reading-confirmation：仅处理工作表“9.1”第17行；已读取本行完整单元格文字及全部锚定截图 `C_image23.png`，已区分新系统问题图与旧系统目标图，未读取未分配行。
- 状态：本地新系统 Chrome 真实业务验收通过；未提交、未构建、未部署、未改版本、未写线上数据库。
- 根因：前端“新增子任务”原先未在打开表单前校验父调查任务授权结束日；后端创建接口也缺少同一门禁，可被直接请求绕过。
- 整改：前端读取 `authorized_to`（兼容历史 `end_date`），结束日早于当天时提示“该任务已过期，不允许新建子任务”并停止打开表单；后端解析根调查事项后、任何子任务写入前执行同一校验并返回 HTTP 409。当日到期仍允许，只有早于当天才判定过期。
- Chrome 验收（隔离 Web 15317 / API 18317 / SQLite）：选择 `DC-R17-EXPIRED` 点击“新增子任务”，显示准确提示且未打开表单；使用同账号令牌直接 POST 返回 409 和相同提示，调用前后子任务数均为0。`DC-R17-TODAY` 与 `DC-R17-FUTURE` 均正常打开新增表单，选择“第十七行管理员”后各成功保存1条隔离子任务。最终数量为过期0、当天1、未来1。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/investigation_expired_subtask_row17_test.py`、`apps/admin-web/src/InvestigationCenterPage.tsx`、`apps/admin-web/investigationExpiredSubtaskRow17.test.mjs`、`.codex-evidence/9.1-row17/*`。
- 聚焦测试：前端第17/16行测试均通过；后端 `python -m unittest investigation_expired_subtask_row17_test.py contract_downstream_draft_gate_row15_test.py investigation_admin_delete_role_ids_row16_test.py`，7/7通过。
- 数据库补丁建议：本行无需结构或数据迁移。可另行只读审计 `authorized_to` 缺失或非 ISO 日期的历史调查数据，输出清单交业务治理，不应在本批次自动改写。
- 清理：Chrome 本行标签已关闭；隔离 API、SQLite、三条父任务、两条子任务及临时凭据已在验收后清理；Web 15317 由主会话停止。

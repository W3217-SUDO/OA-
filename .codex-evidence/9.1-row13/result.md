# 9.1 第 13 行处理结果

- 状态：代码与静态聚焦测试完成；未浏览器验收、未构建、未部署。
- 根因：前端把 `investigation-task-mine` 映射为 `module=task + investigation_view=assigned`，将父调查委托页错误当成调查员子任务执行页；按钮配置因此混入“新增线索/关闭任务并生成报告”。
- 旧系统链路：`Areas/CIT/Views/Investigation/List.cshtml` 的父调查列表底部为刷新、修改、上传调查资料；`InvestigationTask/List.cshtml` 的新增线索属于调查子任务页，不能移植到品管发布的父任务页。
- 修改：我的调查任务改读 `module=investigation + investigation_view=published`；我的/过期父调查任务按钮限定为查询、刷新、修改、上传调查资料；子任务新增线索入口保持不变。
- owned files：`apps/admin-web/src/InvestigationCenterPage.tsx`、`apps/admin-web/investigationPublishedParentTaskRow13.test.mjs`、`apps/admin-web/investigationCenterFrontendParity.test.mjs`、`.codex-evidence/9.1-row13/*`。
- 测试：新增聚焦测试通过；`investigationPublishedFilter`、`investigationAdminPublishedVisibility`、`investigationTaskMenuParity` 通过；既有 `investigationCenterFrontendParity` 的本行旧断言已更新，另有与本行无关的“经办律师 Select”历史断言失败，记录为非本行阻断；`git diff --check` 通过。
- 数据库补丁建议：无需数据迁移；修复查询模块和视图语义即可。若历史父调查缺少 publisher，后端已按 owner 兼容。
- 主会话 Chrome 验收：用品管账号进入调查大厅→我发布的调查任务→我的调查任务，确认展示父调查编号且底部仅刷新/修改/上传调查资料；不得出现新增线索或关闭报告。打开过期调查任务重复核对，并确认仅当前品管发布且授权结束日已过的父调查；再以调查员账号确认其执行子任务页仍保留新增线索。

# 9.1 第13行处理结果

- reading-confirmation：仅处理工作表 9.1 第13行；已读取该行全部单元格与全部锚定截图，区分新系统问题图和旧系统目标图。问题要求“我发布的调查任务”展示发布者的父调查事项，不允许办理调查员子任务动作。
- 状态：代码整改、聚焦测试和隔离本地新系统 Chrome 验收均完成；未构建、未部署、未改版本、未写线上数据库、未提交。
- 根因：前端曾把发布者的“我的调查任务”映射为 `module=task + investigation_view=assigned`，错误复用了调查员子任务执行页，因此混入“新增线索”“关闭任务并生成报告”等调查员动作。
- 旧系统/证据语义：父调查列表 `Areas/CIT/Views/Investigation/List.cshtml` 的操作为刷新、修改、上传调查资料；新增线索属于调查员子任务页面，不能移植到发布者父任务页。
- 修改：发布者的我的/过期调查任务统一使用 `module=investigation + investigation_view=published`；保留父调查事项字段和刷新、修改、上传调查资料，移除调查员动作。
- owned files：`apps/admin-web/src/InvestigationCenterPage.tsx`、`apps/admin-web/investigationPublishedParentTaskRow13.test.mjs`、`apps/admin-web/investigationCenterFrontendParity.test.mjs`、`.codex-evidence/9.1-row13/*`。
- Chrome 验收：隔离 Web `127.0.0.1:15313`、API `127.0.0.1:18313`、SQLite `row13-browser.sqlite3`。使用 Admin 管理者从“调查大厅 → 我发布的调查任务 → 我的调查任务/过期调查任务”进入；两页均显示父调查字段（调查编号、权利人、权利类型、授权起止、调查区域、案源人、任务分配人）。允许按钮计数均为：刷新 1、修改 1、上传调查资料 1；禁止按钮计数均为：新增线索 0、关闭任务并生成报告 0。
- 动态数据限制：隔离 SQLite 中没有发布者父调查样本，页面显示“没有查询到符合条件的记录”；因此未对原记录内容做动态复现，但已对原入口、父调查列语义和操作权限做真实浏览器验收，不能将空列表记为原记录浏览器通过。
- 请求命中：API 日志多次记录 `GET /api/v1/records?module=investigation&page_size=100&scope=mine&investigation_view=published...`，均返回 200，确认请求命中本工作树隔离 API。
- 截图：`.codex-evidence/9.1-row13/local-new-system-publisher.png`。
- 测试：`investigationPublishedParentTaskRow13.test.mjs` 通过；`investigationPublishedFilter.test.mjs` 1/1 通过；`investigationAdminPublishedVisibility.test.mjs` 通过；`investigationTaskMenuParity.test.mjs` 2/2 通过。
- 数据库补丁建议：无需数据库迁移；本行是查询模块、视图语义和按钮权限修复。若历史父调查缺少 publisher，后端继续按 owner 兼容即可。
- 主会话 Chrome 验收：在包含原问题记录的数据环境，以发布者账号进入“调查大厅 → 我发布的调查任务 → 我的调查任务”，确认原父调查记录可见且仅有刷新/修改/上传调查资料；不得出现新增线索或关闭任务并生成报告。再进入“过期调查任务”重复核对；最后以调查员账号确认其子任务执行页仍保留调查员动作。
- 补证（2026-09-01）：在隔离 SQLite 创建 `CODEX-901-R13-ACTIVE` 与 `CODEX-901-R13-OVERDUE` 发布者父调查样本，以发布者账号 `rqa2.publisher` 分别进入“我的调查任务”和“过期调查任务”。两页均为非空父调查列表，直接展示调查编号、权利人、权利类型、授权起止、调查区域、案源人、任务分配人；底部仅有“修改/上传调查资料”，无“新增线索/关闭任务并生成报告”。整页刷新后记录仍存在。证据：`local-new-system-publisher-active-refreshed.png`、`local-new-system-publisher-overdue-refreshed.png`。

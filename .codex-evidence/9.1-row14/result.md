# 9.1 第14行处理结果

- reading-confirmation：仅处理工作表 9.1 第14行；已读取本行全部单元格和全部锚定截图，原问题记录为 `DC20260810140152FCE1`，问题是调查子任务负责人搜索遗漏人员，要求用户名、系统显示名、人事中文姓名均可检索且选择、保存、回显一致。
- 状态：代码整改、聚焦测试、隔离 API/Web/SQLite 和 Google Chrome 真实业务验收均完成；未构建、未部署、未改版本、未写线上数据库、未提交。
- 根因一：共享 `/people/options` 原先只用 HR 中文姓名和用户名生成 `search_text`，漏掉 `User.display_name`，因此按系统显示名检索失败。
- 根因二：任务保存后 `_task_display_dicts` 仍只从 `User.display_name` 生成 `owner_display_name`，导致表单选择显示 HR 中文姓名、任务列表回显系统显示名，二者不一致。
- 修改：人员搜索文本统一包含“在职 HR 中文姓名 + 系统显示名 + 用户名”；任务负责人回显优先采用同账号的在职 HR 中文姓名，缺失时再沿用系统显示名。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/people_options_chinese_match_row14_test.py`、`apps/admin-web/src/InvestigationCenterPage.tsx`、`.codex-evidence/9.1-row14/*`。
- 浏览器夹具：原调查 `DC20260810140152FCE1`；测试人员用户名 `r14.fan`、系统显示名 `FAN-WL`、HR 中文姓名 `范文玲`；保存任务 `RW20260901184548208756`。
- Chrome 搜索验收：在“调查大厅 → 待我分配的调查任务 → 原调查 → 新增子任务”的调查员下拉中，分别输入 `r14.fan`、`FAN-WL`、`范文玲`，三次均唯一命中候选 `范文玲`，候选账号均为 `r14.fan`。
- Chrome 保存/回显验收：选择 `范文玲` 后保存任务成功；修复并重启 API 后，原任务列表负责人显示 `范文玲`。整页刷新后重新进入原调查，任务 `RW20260901184548208756` 仍显示负责人 `范文玲`，持久化一致。
- 请求命中：API 日志记录 `GET /api/v1/people/options`、`POST /api/v1/investigations/29/tasks`、多次 `GET /api/v1/investigations/29/tasks`；搜索、保存和刷新回查均命中本工作树隔离 API。
- 截图：`.codex-evidence/9.1-row14/local-new-system-reverify.png`。
- 测试：`python -m unittest people_options_chinese_match_row14_test.py task_case_acceptance_status_row12_test.py task_serial_number_row11_test.py` 3/3 通过；新增聚焦断言同时覆盖系统显示名搜索文本和任务负责人 HR 中文姓名回显；`git diff --check` 通过。
- 数据库补丁建议：无需数据库结构迁移。上线前建议只读核对在职 HR 档案中的 `data.username/owner` 是否能唯一关联系统账号；无法唯一关联的档案应人工维护，不能猜测映射。
- 主会话 Chrome 验收：在包含原问题数据的环境进入 `DC20260810140152FCE1` 新增子任务，分别以截图涉及人员的用户名、系统显示名和 HR 中文姓名搜索，确认候选集合一致；选择后保存，再刷新并回到原任务，负责人必须持续显示同一 HR 中文姓名。
- 补证（2026-09-01）：在隔离父调查 `CODEX-901-R14-PARENT` 的新增子任务表单中，以用户名 `rqa2.fan` 搜索时下拉唯一显示 HR 中文姓名“范文玲”；选择后保存，整页刷新并重新打开父调查，顶部子任务列表负责人仍为“范文玲”。证据：`local-new-system-search-fanwenling.png`、`local-new-system-saved-refreshed-fanwenling.png`。

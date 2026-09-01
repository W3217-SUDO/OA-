# 9.1 第 11 行处理结果

- 状态：代码与聚焦测试完成；按派工约束未浏览器验收、未构建、未部署，不能标记线上闭环。
- 返工优先审计：本行发起时间为 2026-09-01，F/G/H/I 均空；未发现 8.28/8.31 同问题的 reading-confirmation 或历史提交，因此属于新增问题，不是已闭环返工。
- 旧系统审计：旧页面 `Areas/TP/Views/Task/TaskDetail.cshtml`、`Scripts/TP/Task/Legal.Task.js` 以 `TaskNo` 作为详情与列表业务标识；Web 源码未包含服务层的生成实现。仓库既有旧制示例为 `RW20260714001`（日期 + 日序号），支持采用短日序号而不改变字符串关联语义。
- 根因：`POST /api/v1/tasks` 在 `apps/api-server/app/main.py` 使用 `RW%Y%m%d%H%M%S%f`，把日期、时分秒和微秒全部暴露为任务业务号，产生截图中的 22 位 `RW...` 长编号。
- 修改：新增人工任务短号生成器，格式为 `RW + YYMMDD + 3 位当日序号`；只改变新建人工任务，历史长编号不迁移、不重写并继续可查询。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/task_serial_number_row11_test.py`、`.codex-evidence/9.1-row11/*`。
- 测试：`python -m unittest task_serial_number_row11_test.py case_task_creation_approval_independence_row7_test.py`，4/4 通过；`python -m py_compile app/main.py task_serial_number_row11_test.py` 通过；`git diff --check` 通过。
- 数据库补丁建议：无需迁移。历史任务号是对外关联标识，保留原值风险最低；新任务自然使用短号。
- 主会话 Chrome 验收：以有案件任务创建权限的账号进入案件中心某可写案件，发起两条任务；打开“事务中心 → 我的任务 → 我发起的任务”，确认编号均匹配 `RW\d{9}`、长度 11、两条末三位连续且可分别点击打开详情；再搜索截图中的历史长编号，确认仍可查可打开。

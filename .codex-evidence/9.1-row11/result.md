# 9.1 第11行处理结果

- 状态：代码、聚焦测试与隔离本地新系统 Chrome 真实业务验收完成；未构建、未部署、未改版本、未写线上数据库。
- 返工判定：本行 F/G/H/I 均为空，未发现 8.28/8.31 同问题历史整改或返工意见，属于新增问题。
- 根因：`POST /api/v1/tasks` 原以 `RW%Y%m%d%H%M%S%f` 生成编号，把时分秒与微秒暴露在业务编号中，形成 22 位长编号。
- 修改：人工任务编号改为 `RW + YYMMDD + 3 位当日序号`；历史编号不迁移、不重写，仍可查询。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/task_serial_number_row11_test.py`、`.codex-evidence/9.1-row11/*`。
- 聚焦测试：`python -m unittest task_serial_number_row11_test.py case_task_creation_approval_independence_row7_test.py`，4/4 通过；`python -m py_compile app/main.py task_serial_number_row11_test.py` 通过；`git diff --check` 通过。
- Chrome 实跑：隔离 Web `127.0.0.1:15311` 代理到本工作树隔离 API `127.0.0.1:18311`，隔离 SQLite；管理员从“公司案件 → 民事争议 → SHMS2500149 → 案件任务 → 发布任务”依次创建 `CODEX-901-R11-A`、`CODEX-901-R11-B`。
- 浏览器结果：列表持久化展示 `RW260901001`、`RW260901002`，均为人工任务、状态“进行中”；两个编号均匹配 `RW\d{9}`、长度 11，且当日序号连续唯一。
- 进程命中证据：本次 API 日志记录两次 `POST /api/v1/tasks HTTP/1.1`，均返回 `201 Created`，并由随后 `GET /api/v1/cases/26/tasks?...scope=case` 返回列表，确认请求到达本工作树 18311 进程。
- 截图：`local-new-system-acceptance.png`。
- 数据清理：验收结束后关闭本行 Chrome 标签、停止隔离 Web/API，并删除整套隔离 SQLite（含两条验收任务及临时账号变更）；线上及共享数据库无写入。
- 数据库补丁建议：无需迁移。历史任务号是外部关联标识，保留原值风险最低；新建人工任务自然使用短号。

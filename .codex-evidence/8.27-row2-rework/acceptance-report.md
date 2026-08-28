# 8.27 第 2 行返工本地验收

## 结论

控制台待办数量已与点击后的本账号真实队列一致。本行费用类待办按原台账备注暂不处理。

## 浏览器验收

- 待处理任务：控制台 1，进入 `task-my-accepted` 的“待处理”后 1 条。
- 已拒绝任务：控制台 1，进入 `task-my-created` 的“进行中-拒绝”后 1 条。
- 待审批线索：控制台 2，进入 `clue-audit-pending` 后 2 条，未混入待取证线索。
- 已拒绝线索：控制台 1，进入 `clue-audit-refused` 后 1 条，未进入全部线索。
- 待审批/已驳回合同：均为 0，目标窗口分别为 `contract-audit-pending` / `contract-audit-refused`，列表均为 0。
- 待审批/已拒绝用印：均为 0，目标窗口分别为 `seal-audit-pending` / `seal-my-refused`，列表均为 0。
- 待审核/已拒绝归档：均为 0，目标窗口分别为 `case-archive-pending` / `case-archive-refused`，列表均为 0。
- 一条超过交接自动完成日期的任务在打开控制台时自动转为已完成，未计入待处理数。
- 浏览器控制台错误/警告：0。

## 自动化验证

- 后端：`python -m unittest dashboard_personal_todo_scope_row2_test.py`，1/1 通过。
- 前端：`node --test src/dashboardTodoNavigationRow2.test.mjs`，3/3 通过。
- 正式构建：`npm.cmd run build` 通过，5636 modules transformed，版本保持 1.1.12。

## 清理

- 隔离 SQLite 测试库和本地 8042/5242 服务已清理。
- 未连接或写入线上数据库。

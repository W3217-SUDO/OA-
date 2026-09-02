# 9.1 第14行本地整改验收（2026-09-02）

## 结论与文件

- 需求：所有复用人员选择器的入口，都应能按启用人员的 HR 中文姓名、系统显示名和用户名检索到同一账号；保存与刷新后继续显示同一 HR 中文姓名。
- 既有修复文件：`apps/api-server/app/main.py`、`apps/api-server/people_options_chinese_match_row14_test.py`。本轮严格审计既有实现和证据，不重复改写已形成的代码。
- 根因、旧/新系统源码与数据链路见 `reading-confirmation-20260902.md`。

## 独立 Chrome 验收

- 环境：本工作树独立 API 8014、Web 15324、SQLite `row14b.db`；账号 `row14supervisor`，目标账号 `row14fan`，系统显示名 `FAN-WL`，在职 HR 中文名“范文玲”。
- 同一“待我分配的调查任务 → CODEX-901-R14-PARENT → 新增子任务 → 调查员”入口分别输入“范文玲”、`row14fan`、`FAN-WL`，三次均只命中同一候选“范文玲（row14fan）”：`local-search-hr-chinese-20260902.png`、`local-search-username-20260902.png`、`local-search-system-display-20260902.png`。
- 选择“范文玲”，补齐上海市/市辖区/黄浦区并创建子任务；成功提示证据 `local-saved-hr-name-20260902.png`。
- 整页刷新后重新打开父调查，任务 `RW20260902133920232888` 仍存在，负责人“范文玲”、账号持久值 `row14fan`、区域与日期均保持：`local-refreshed-persisted-20260902.png`。
- 失败路径一：未选择父调查时点击“新增子任务”，前端提示“请只勾选一条记录”，无写请求：`local-no-selection-blocked-20260902.png`。
- 失败路径二：首次使用超过 30 天的截止日期，API 返回“任务截止日期不能超过 30 天”；修正为合法截止日期后只创建 1 条任务，未产生重复测试记录。

## 测试与数据核对

- `python -m unittest people_options_chinese_match_row14_test.py task_case_acceptance_status_row12_test.py task_serial_number_row11_test.py`：4/4 通过。
- `python -m py_compile app/main.py people_options_chinese_match_row14_test.py`：通过。
- `npm.cmd run build`：通过，5643 modules transformed；仅有既存 chunk size 警告。
- SQLite 回查：唯一任务 owner=`row14fan`、status=`待接收`；唯一 HR 档案 title=`范文玲`、status=`在职`、data.username=`row14fan`。

## 清理与风险

- 验收后关闭本行 Chrome 标签并停止 8014/15324；删除本行 SQLite、种子/检查脚本、日志、PID 文件、临时 `.env.staging.local` 和 `node_modules` junction；测试账号、HR、合同、父调查与子任务随隔离数据库删除。
- 未部署，未改版本/tag/dev/线上数据库/8089/Excel 状态。
- 冲突风险：`apps/api-server/app/main.py` 是跨行共享热点；集成时必须同时保留 `/people/options` 的三字段 `search_text` 与 `_task_display_dicts` 的 HR 中文名覆盖，避免只保留搜索修复或只保留回显修复。

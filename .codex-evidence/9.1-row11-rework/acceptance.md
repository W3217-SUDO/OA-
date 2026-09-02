# 9.1 第11行返工验收记录

- 工作簿：`C:\Users\Administrator\Desktop\OA系统\问题\OA系统对接9.1.xlsx`
- 工作表/行：`9.1` / 第11行
- 原始需求：案件中心发起任务时，任务编号过长，需要按旧系统表现缩短。
- VibeHub：已对脱敏词“任务编号”“编号生成规则”执行核对，无可靠补充术语；未改变原需求。

## 根因与旧系统依据

- 前一轮把旧规则误判成 `RW + YYMMDD + 当日三位序号`；旧系统真实页面不支持该结论。
- 管理员在旧系统 `localhost:8091` 同模块复现，公司任务列表显示任务类型与任务编号为独立字段。
- 旧编号均为 11 位纯数字，例如 `14065225191`、`13334869344`、`09553505662`；前六位与列表更新时间的 `HHmmss` 一致，后五位为碰撞区分值。
- 旧入口由 `CaseTaskController` / `TaskController` 调用服务程序集生成编号；归档源码不含该服务实现，因此不臆测后五位的具体旧算法，只对齐可观察契约。
- 新系统 `POST /api/v1/tasks` 曾生成 `RW%Y%m%d%H%M%S%f`，后又被误改为带 `RW` 的日期序号；根因是没有先完成同入口动态复现便推断规则。

## 修改

- `apps/api-server/app/main.py`：新建人工任务生成 `HHmmss + 五位随机碰撞区分值` 的 11 位纯数字编号；全局检查 `BusinessRecord.serial_no`，最多重试 100 次，失败返回 503；历史编号不迁移。
- `apps/api-server/task_serial_number_row11_test.py`：覆盖旧形态、历史编号兼容、碰撞重试、重试耗尽与零额外写入。

## 自动化与构建

- `python -m unittest task_serial_number_row11_test.py case_task_creation_approval_independence_row7_test.py`：5 项通过。
- `python -m py_compile app/main.py task_serial_number_row11_test.py`：通过。
- 前端 `npm.cmd run build`：通过（5643 modules；仅既有 chunk 大小警告）。
- `git diff --check`：通过。
- 修改后 `codegraph sync`：通过。

## 独立 Chrome 验收

- 隔离环境：本工作树源码；API `8012`；Vite `15311`；独立 SQLite；管理员角色。
- 路径：案件详情 `CODEX-901-R11-CASE` → 案件任务 → 发布任务。
- 成功路径：创建 `CODEX-901-R11-LEGACY-NUMBER`，页面显示编号 `12461616174`、类型“人工”、状态“进行中”。
- 刷新持久化：浏览器刷新后重新进入案件任务，仍显示同一编号和标题。
- 失败路径：任务主标题留空时显示“请输入任务主标题”，输入框 `aria-invalid=true`；后端 `POST /api/v1/tasks` 总数保持 1，没有产生失败写入。

## 证据

- `legacy-company-task-numbers.png`：205605 bytes；SHA256 `670043446594A61DE9917BFAFD69B91C44B98F58079C6C9FE6120EF7EC04B78D`
- `local-task-number-created.png`：115581 bytes；SHA256 `617C9559D7BB8D57E30C0842845A4341A45CA650B2DF57922B6675A7782BC398`
- `local-task-number-refreshed.png`：115615 bytes；SHA256 `F1A09EBBDCAC7B4010718747088BB12B131429F90C08FB7228194292D83C25FA`
- `local-empty-title-blocked.png`：97717 bytes；SHA256 `638F9BE4FC0F3EE0038234463C82E3841CF6A620379598B60E0DCBEE2B1F6B7D`

## 清理与发布边界

- 已停止端口 `8012` / `15311` 的临时进程；已删除隔离 SQLite、日志、种子脚本和临时 `node_modules` 目录联接。
- 未触碰共享或线上数据库，未修改 Excel 完成状态，未修改正式版本、tag、`dev`、8089 部署。

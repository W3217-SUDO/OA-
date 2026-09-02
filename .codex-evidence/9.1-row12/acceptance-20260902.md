# 9.1 第12行本地整改验收（2026-09-02）

## 需求与结构化读取

- 工作簿：`C:\Users\Administrator\Desktop\OA系统\问题\OA系统对接9.1.xlsx`，工作表 `9.1`，第12行，范围 A:I。
- A=`事务中心`；B 原文已逐字保存在 `reading-confirmation-20260902.md`；C、D 单元格各锚定一张图片；E=`2026.9.1`；F、G、I 为空；H 原值为 `1`，但本次委托明确返工，因此不作为完成依据。
- 无批注、超链接和合并单元格；行高 135.75；图片、格式及文字均已结构化读取。
- VibeHub 使用脱敏候选词“关系视图状态 / 任务接收 / 状态机”核对，revision `d2034b1998eaaa2f`，未返回需要补充的可靠术语。

## 旧系统事实与根因

- 同入口/同角色：`http://localhost:8091/9001001020/TP/Task/TaskList`，负责人“我接受的任务”。当前只读样本库中四个状态均为 0，截图 `legacy-current-empty.png`；因此没有伪造动态流程，也没有写旧库。
- 权威旧源码：`GD.CRM.WEB/Areas/TP/Controllers/TaskController.cs` 按 Pending/Processing 与当前负责人查询；`GD.CRM.WEB.VIP/Areas/TP/Views/Task/TaskList.cshtml` 分开展示待处理和进行中；`TaskDetail.cshtml` 仅在当前负责人且 Pending 时显示“接受任务”。主数据/节点关系为 `Legal_Case_Task`、`Legal_Case_Task_Node`、`TaskGuid`。
- 旧库只读核验：当前 23 条案件任务中没有可关联的待处理节点，也找不到截图原记录，故旧系统动态证据以原始 D12 截图和权威源码/数据结构为准，并明确记录样本缺口。
- 新系统追踪：`apps/api-server/app/main.py` 创建案件任务时持久化为 `待处理`；发起人列表和案件详情仅把关系视图显示映射为 `进行中`，同时保留 `workflow_status=待处理`；负责人接收接口校验负责人/管理员后才将状态转为 `处理中` 并写入流转事件。
- 具体根因：此前把“发起人看到任务已经开始计时/进行中”的关系视图语义误当成全局持久化状态，导致负责人无需接受就跳过待处理状态。修复将显示状态与工作流状态拆分。

## 修改与测试

- 既有修复文件：`apps/api-server/app/main.py`（案件任务初始状态、发起人/案件详情显示映射、负责人接受流转）。
- 本次返工补强：`apps/api-server/task_case_acceptance_status_row12_test.py` 新增“发起人不得代替负责人接受且状态保持待处理”的失败路径断言。
- `python -m unittest task_case_acceptance_status_row12_test.py task_serial_number_row11_test.py case_task_creation_approval_independence_row7_test.py case_task_detail_row21_test.py`：7 tests，OK，32.421s。
- `python -m py_compile apps/api-server/app/main.py apps/api-server/task_case_acceptance_status_row12_test.py`：通过。
- `npm.cmd run build`：通过，5643 modules transformed；仅保留既有 chunk size 警告。

## 独立 Chrome 验收

- 发起人创建 `CODEX-901-R12-STATE-FLOW` 后，案件任务视角显示“进行中”：`local-initiator-processing.png`。
- 负责人“我接受的任务”先显示待处理(1)、进行中(0)：`local-owner-pending.png`。
- 未勾选任务点击“接受任务”时 DOM 出现“请先选择”阻断；API 日志中 `/accept` 仍为 0：`local-owner-no-selection-blocked.png`。
- 勾选后接收成功，待处理(0)、进行中(1)：`local-owner-accepted.png`。
- 整页刷新后仍为进行中(1)且任务存在：`local-owner-accepted-refreshed.png`。
- 详情沟通记录出现“接收任务 / 待处理 → 处理中 / 任务已接收”：`local-owner-history.png`。
- API 日志只出现一次创建 `201` 和一次接收 `200`，没有重复提交。

## 数据持久化与失败路径

- 隔离 SQLite：任务 id=2、编号 `13025832867`、status=`处理中`、owner=`row12owner`，`data.accepted_at` 已持久化。
- `workflow_events` 恰有两条：发起任务 `'' → 待处理`；负责人接收 `待处理 → 处理中`。
- API 单元测试进一步证明发起人请求接收返回 403，且 `workflow_status` 保持 `待处理`。

## 截图 SHA256

- `local-initiator-processing.png`: `7B053C3741535029CA747ED521D7E4B4C48CCBCE9EFACAE80ED4D9712EF1B44F`
- `local-owner-pending.png`: `8024AB11BA9B5CEB5ED30475A8459EACD6927A8F30623E82B4D63872D83737EC`
- `local-owner-no-selection-blocked.png`: `8024AB11BA9B5CEB5ED30475A8459EACD6927A8F30623E82B4D63872D83737EC`
- `local-owner-accepted.png`: `FFF83D408E238915A796E7C009CDC56228F23C2335D2CA9CCE63BF301B33FEE5`
- `local-owner-accepted-refreshed.png`: `5BD73E4C589B4AF9A0EE4604FAE8BF6DB2D15DB9658C6B57B29206D781F13F24`
- `local-owner-history.png`: `68C78FB079155E0F68C186E38B05A5140DA4F08B8A91B97FB59BBBBBA1B02511`
- `legacy-current-empty.png`: `C2E155815BD3573FC766F6435691275AC309BD92A46DFAC8844A0C732736A140`

## 清理与边界

- 本行验收后关闭本行新/旧系统标签页，停止隔离 8012/15312 服务，删除隔离数据库、日志、种子脚本和临时 `node_modules` junction；不影响其他任务。
- 未部署、未改版本/tag/dev/线上数据库/8089，也未修改工作簿完成状态。
- 冲突风险：`apps/api-server/app/main.py` 为批次共享热点文件；本次新提交只增加第12行专项测试和证据，集成时仍应保留祖先提交 `933df92` 中的案件任务状态拆分。

# 9.1 第17行整改结果

## 根因

- “待我分配的调查任务”的“新增子任务”动作直接进入 `openTasks(row, true)`，没有在打开表单前校验所选调查的授权结束日。
- 后端 `POST /investigations/{record_id}/tasks` 也没有校验根调查事项是否已经超过授权结束日，因此仅做页面禁用仍可被接口绕过。

## 修改

- 前端读取所选调查的 `authorized_to`（兼容历史 `end_date`）；结束日早于当天时，立即提示“该任务已过期，不允许新建子任务”并停止加载/打开表单。
- 后端增加统一的调查授权过期判定，并在解析到根调查事项后、创建任何子任务前返回 HTTP 409 和同一提示。
- 当天到期仍允许创建；只有结束日早于当天才视为过期。缺失或非法日期不臆断为过期，交由既有数据校验/治理处理。

## 文件

- `apps/admin-web/src/InvestigationCenterPage.tsx`
- `apps/api-server/app/main.py`
- `apps/admin-web/investigationExpiredSubtaskRow17.test.mjs`
- `apps/api-server/investigation_expired_subtask_row17_test.py`
- `.codex-evidence/9.1-row17/reading-confirmation.md`
- `.codex-evidence/9.1-row17/C_image23.png`

## 聚焦测试

- `python -m unittest investigation_expired_subtask_row17_test.py contract_downstream_draft_gate_row15_test.py investigation_admin_delete_role_ids_row16_test.py`：7 项通过。
- `node investigationExpiredSubtaskRow17.test.mjs`：通过。
- `node investigationSubtaskContractGateRow15.test.mjs`：通过。
- `node investigationPublishedParentTaskRow13.test.mjs`：通过。
- `python -m py_compile app/main.py`：通过。
- 首次从 `apps/api-server` 目录调用三个前端 Node 测试时因路径错误均报 `MODULE_NOT_FOUND`；改到 `apps/admin-web` 后逐项通过，属于测试命令工作目录错误，不是产品失败。

## 数据库补丁建议

- 本行不需要结构或数据迁移。
- 可另行排查 `authorized_to` 缺失或非 ISO 日期的历史调查数据并做数据治理，但不应在本批次无授权写库。

## 主会话 Chrome 验收步骤

1. 使用有调查分配权限的角色进入“调查大厅 → 待我分配的调查任务”。
2. 选择授权结束日早于当天的调查（截图样例 `RW2411260046472`，授权结束日 `2024-11-23`），点击“新增子任务”。
3. 确认页面提示“该任务已过期，不允许新建子任务”，且不打开新增表单、不产生子任务。
4. 选择授权结束日为当天或未来的调查，确认仍可正常打开新增子任务表单。
5. 通过开发者工具复核过期记录的直接 POST 调用返回 409 与相同提示，且数据库没有新增任务记录。

## 状态

- 代码与非浏览器聚焦测试完成。
- 按本会话限制未启动浏览器、未构建、未部署、未改版本、未写数据库。

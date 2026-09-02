# 9.1 第15行本地整改验收（2026-09-02）

## 修改

- 既有合同门禁：`apps/api-server/app/main.py`、`apps/api-server/contract_downstream_draft_gate_row15_test.py`，仅草稿合同禁止下游创建，其他持久存在的合同状态允许；合同不存在明确阻断。
- 本轮补齐：`apps/admin-web/src/InvestigationCenterPage.tsx` 将新增子任务抽屉内任务列表列名和必填反馈从“负责人”统一改成“调查员”。
- 测试扩展：`apps/admin-web/investigationSubtaskContractGateRow15.test.mjs` 同时约束合同过滤、表单标签、校验提示和任务表列名。

## 独立 Chrome 验收

- 环境：独立 API 8015、Web 15325、SQLite `row15b.db`，账号 `row15supervisor`，调查员 `row15investigator`。
- 草稿合同：`CODEX-901-R15-DRAFT` 选择调查员后提交，API 409“草稿合同不能创建调查子任务”，数据库无任务；`local-draft-blocked-labels-20260902.png`。既有截图 `local-new-system-contract-draft-blocked.png` 继续保留作错误提示视觉补证。
- 非草稿合同：状态“已拒绝”的 `CODEX-901-R15-REJECTED` 未被白名单误拒绝；未选调查员时提示“请填写调查员后再创建任务”，`local-investigator-required-label-20260902.png`；选择后 API 201，只创建任务 `RW20260902135007123674`。
- 整页刷新后重新打开父调查，任务表列名为“调查员”，任务负责人持续显示“第15行调查员”，合同/区域/日期保持，`local-nondraft-refreshed-persisted-20260902.png`。
- 已删除合同：`CODEX-901-R15-DELETED` 指向不存在的合同 ID，选择调查员提交后 API 422“创建调查任务前必须绑定同客户合同”，数据库无任务；`local-deleted-contract-blocked-20260902.png`。
- API 写路径只有三次：草稿 409、非草稿 201、已删除合同 422；唯一成功任务证明失败路径没有产生脏数据或重复数据。

## 测试

- `node investigationSubtaskContractGateRow15.test.mjs`：通过。
- `node --test investigationPublishedFilter.test.mjs investigationAdminPublishedVisibility.test.mjs investigationTaskMenuParity.test.mjs investigationCenterFrontendParity.test.mjs`：25/25 通过。
- `python -m unittest contract_downstream_draft_gate_row15_test.py people_options_chinese_match_row14_test.py task_case_acceptance_status_row12_test.py`：3/3 通过。
- `python -m py_compile app/main.py contract_downstream_draft_gate_row15_test.py`：通过。
- `npm.cmd run build`：通过，5643 modules transformed；仅有既存 chunk size 警告。
- `git diff --check`：提交前通过。

## 清理与冲突风险

- 验收后 Chrome 已执行最终清理；停止 8015/15325，删除 SQLite、账号/合同/调查/任务测试数据、种子/检查脚本、日志、PID、临时 `.env.staging.local` 和 `node_modules` junction。
- 未部署，未改版本/tag/dev/线上数据库/8089/Excel 状态。
- 冲突风险：`apps/api-server/app/main.py` 和 `apps/admin-web/src/InvestigationCenterPage.tsx` 均是多行共享热点。集成时必须保留公共“非草稿”门禁、合同不存在阻断、调查员表单标签/必填提示/任务表列名，以及第13行 published 视图与第14行人员搜索映射。

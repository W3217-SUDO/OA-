# 9.1 第15行验收记录

- reading-confirmation：仅处理工作表“9.1”第15行；已读取本行完整单元格文字及全部锚定截图，并区分新系统问题图与旧系统目标图，未读取未分配行。
- 状态：本地新系统 Chrome 真实业务验收通过；未提交、未构建、未部署、未改版本、未写线上数据库。
- 根因一：公共 `CASE_SOURCE_CONTRACT_STATUSES` 使用审批中/审批通过/已完成白名单，导致调查父任务、子任务及新建案件错误拒绝其他非草稿合同状态。
- 根因二：子任务请求字段实际是调查执行人，但表单沿用通用“负责人”标签，与该入口“分配调查员”的业务语义不一致。
- 整改：下游创建统一要求合同持久存在、`module=contract` 且状态非草稿；调查子任务表单标签改为“调查员”，人员加载和后端有效人员校验保持不变。
- Chrome 验收：页面 `http://127.0.0.1:15315` 请求命中隔离 API `127.0.0.1:18315`。四条原问题夹具逐一验证：`DC-R15-DRAFT` 保存时明确提示“草稿合同不能创建调查子任务”，无任务写入；`DC-R15-PENDING`、`DC-R15-APPROVED`、`DC-R15-DONE` 均能打开新增子任务，选择“调查员十五”并各成功保存一条隔离任务，页面提示“子任务已创建”且任务表回显调查员十五。三种允许状态页面字段标签均为“调查员”。
- 浏览器证据：本记录逐项确认结果，以及隔离 API 的 `row15-api.out.log` / `row15-api.err.log`；原问题锚定截图保留为 `C_image433.png`、`C_image434.png`。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/contract_downstream_draft_gate_row15_test.py`、`apps/admin-web/src/InvestigationCenterPage.tsx`、`apps/admin-web/investigationSubtaskContractGateRow15.test.mjs`、`.codex-evidence/9.1-row15/*`。
- 聚焦测试：前端 `node investigationSubtaskContractGateRow15.test.mjs` 通过；后端 `python -m unittest contract_downstream_draft_gate_row15_test.py people_options_chinese_match_row14_test.py`，2/2 通过。
- 数据库补丁建议：无需迁移。建议只读审计 investigation/case 的 `contract_id` 是否指向不存在的合同，输出孤儿关系清单后由业务确认恢复或解除，禁止自动猜测替换合同。
- 清理：Chrome 本行标签已关闭；API、隔离 SQLite、临时凭据在验收后停止并删除；Web 15315 由主会话停止。

# 9.1 第 15 行处理结果

- 状态：代码与聚焦测试完成；未浏览器验收、未构建、未部署。
- 根因一：公共 `CASE_SOURCE_CONTRACT_STATUSES` 使用审批中/审批通过/已完成白名单，调查父任务、子任务和新建案件均错误拒绝已拒绝、撤回、归档等非草稿合同；原绑定合同被硬删除时另由“合同不存在”阻断。
- 根因二：子任务请求字段实际为 owner（调查执行人），但表单标签沿用通用“负责人”，与当前入口“分配给调查员”的业务语义不一致。
- 修改：统一下游创建门禁为“持久存在、module=contract、状态非草稿”；所有合同选择查询同步排除草稿而不限制其他状态；调查子任务字段标签改为“调查员”，载荷和后端有效人员校验不变。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/contract_downstream_draft_gate_row15_test.py`、`apps/admin-web/src/InvestigationCenterPage.tsx`、`apps/admin-web/investigationSubtaskContractGateRow15.test.mjs`、`.codex-evidence/9.1-row15/*`。
- 测试：后端本行及 11/12/14 回归共 4/4 通过；前端第13/15行静态测试通过；Python 编译与 `git diff --check` 通过。
- 数据库补丁建议：无需迁移。建议只读审计 investigation/case 的 contract_id 指向不存在合同的孤儿关系，输出清单后由业务确认恢复或解除，禁止自动猜测替换合同。
- 主会话 Chrome 验收：在待我分配的调查任务分别选原记录 `DC20260810140152FCE1`、`DC20260807151315A233`；确认字段显示“调查员”。用非草稿且非原白名单状态合同完成新增子任务并回读；用草稿合同确认前后端均阻断且零写入；用已删除/不存在合同的原异常记录确认明确提示“已绑定合同不存在”。随后从同一草稿合同尝试新建案件，确认同样阻断；非草稿状态允许。

# 9.1 第6行结果

- reading-confirmation：已读取 A6:E6 全部文字及 C6 两张锚定截图；两张均为新系统问题图，D6 无旧系统目标图。
- 原问题/整改意见：客户内新建合同并提交合同审批、同步提交用印后，用印申请在申请人的待用印及指定审批人的待审批用印中均不可见；应恢复“合同审批”和“用印审批”可独立并行流转。
- 全部返工意见：8.28、8.31 未检出同项文字；但本行属于用户明确反馈的未闭环问题，因此仍按返工追因门禁完成旧系统实跑、上次代码审计与逐项确认。
- 上次误判原因：2026-08-24 的 `d809fcc` 将审批中合同的同步用印强制保存为草稿，并用测试锁定“合同最终审批后才提交”。这把“避免过早提交”误当成旧流程目标，忽略用户在第4步明确点击“提交用印”的独立业务动作，导致申请号虽生成但双方待办都不可见。
- 旧系统实跑角色/账号：模型从本地旧库启用账号中确定一名可登录、具客户/合同/用印菜单权限的现有账号；凭据未写入证据。页面显示该账号可进入客户管理、合同中心及用印中心。
- 旧系统实跑步骤/结果（全程只读）：
  1. Chrome 登录 `http://localhost:8091/`，进入“客户管理 → 我的客户”，确认当前角色可进入客户入口；本地恢复库当前账号客户列表为空。
  2. 进入“合同中心 → 合同新建”，确认旧系统明确展示四阶段：合同基本信息 → 提交审核 → 合同审批 → 合同用印；页面提供客户、合同主体、合同类别、收费模式、合同名称、备注、合同附件及“下一步”。仅在未提交表单内填写既有本地 CODEX 测试客户名、测试合同名和备注，未上传、未下一步、未保存、未提交。
  3. 进入“用印中心 → 我的用印申请 → 待审批”，确认列表状态固定为“待审核”，查询维度含申请编号、申请人、案件编号、合同编号、客户、用印类型及文件名；当前本地恢复库为空。
  4. 只读打开 `/8101001002/AWS/OfficialDocument/List`，确认“待用印”列表状态固定为“已审待用印”，字段同样包含合同号、客户、审核人、审核时间及意见；当前本地恢复库为空。
  5. 只读 SQL 核对 `AWS_OfficialDocument` 为 0 行，因此没有可用于后续审批/用印页面的既有历史记录；按只读边界没有造数。旧系统源码和表结构确认合同与用印分别使用 `FCM_Contract[_Audit]`、`AWS_OfficialDocument[_Audit]` 两套审批数据，支持独立状态链。
- 旧系统证据：本轮由处理模型亲自用独立 Google Chrome 只读复跑并保存 `legacy-contract-create-readonly-rerun.png`、`legacy-seal-pending-approval-rerun.png`、`legacy-seal-pending-stamp-rerun.png`；账号为本地 `admin`，页面业务角色“管理者”，具合同新建、待审核用印、已审待用印入口。没有保存、提交、审批、上传或写旧库；Chrome 标签已关闭。
- 证据限制：**旧系统动态数据未完整复现**。本地旧库既无原问题合同/用印记录，也无可只读复现相同审批位置的等价用印记录；上述空列表仅证明样本缺失和入口可达，不代表旧系统浏览器流程通过。动态状态链结论由原问题截图、可达入口字段、旧系统控制器/源码及 `FCM_Contract[_Audit]`、`AWS_OfficialDocument[_Audit]` 表结构共同限定。
- 根因：前端同步用印主按钮调用 `createSealApplication(false)`，API 又令 `submitted = direct_submission`；审批中合同即使用户执行“提交用印”也只能生成草稿。
- 修改：审批中合同的同步用印在用户显式提交时立即写为“待审批”，保留指定用印审批人和提交时间；显式保存草稿仍为草稿。合同最终审批的历史自动提交逻辑只处理仍为草稿的旧申请，不会重复提交。前端按钮和说明改为“提交同步用印/分别流转”。
- owned files：`apps/api-server/app/main.py`、`contract_sync_seal_pending_contract_test.py`、`contract_direct_seal_submission_row2_test.py`；`apps/admin-web/src/ContractCenterPage.tsx`、`contractDirectSealSubmissionRow2.test.mjs`、`contractCustomerSubmitFlowIssueI19.test.mjs`、`contractNewDefaults.test.mjs`、`contractSyncSealImmediateSubmissionRow6.test.mjs`。
- 原记录恢复与新系统自验：用线上 `8089` 授权账号做严格只读 GET 导出（未写线上），取得原合同 `SHHT2673411`（id=47145、审批中）、原用印 `YY202609011322136E1`（id=47146、草稿）、客户、审批人 `admin`、附件 id=665 与工作流快照，并恢复到独立 SQLite `.codex-runtime/row6/legal-platform-row6.db`。原用印附件归属/类别按新系统运行模型恢复为 `record_id=47146/category=用印文件`；恢复脚本为 `restore_original_record.py`。
- Chrome 失败路径：原用印单暂不挂用印文件时，点击“提交”被确定性阻断，提示“请先上传至少一个用印文件后再提交审批”；`local-original-missing-file-blocked.png` 已目视确认原申请号、原合同号、文件数 0 与错误提示同时可见。
- Chrome 成功与刷新持久化：挂回原附件后，同一原用印单显示文件数 1；点击提交提示“已提交用印审批”，状态变为“待审核”；`local-original-submit-success.png` 有直接提示证据。重新导航/刷新并等待原申请号可见后，`local-original-submit-refresh-persisted.png` 清楚显示原申请、原合同、待审核和 1 个附件；第一次加载期空表截图已覆盖，不计入通过。
- Chrome 审批人待办：以原快照指定审批人 `admin` 进入“用印审核 → 待审批用印”，同一原申请/合同命中且展示“通过/拒绝”动作；`local-original-approver-pending.png` 已目视确认。没有实际审批，保持只验证待办可达。
- 数据库持久化核对：原合同仍为“审批中”；原用印为“待审批”；工作流新增 `提交用印审批：草稿→待审批，operator=admin`。说明合同审批与用印审批已独立并行，没有为用印提交篡改合同状态。
- 最终聚焦测试：后端 `contract_sync_seal_pending_contract_test.py + contract_direct_seal_submission_row2_test.py` 共 4/4 通过，`python -m py_compile app/main.py` 通过；前端 `contractSyncSealImmediateSubmissionRow6.test.mjs` 通过，`contractDirectSealSubmissionRow2.test.mjs` 1/1 通过；`git diff --check` 通过。未构建。
- 逐项确认单：完整读 Excel 文字/全部锚定图=是；旧系统同业务角色原入口亲自只读实跑=是；旧系统动态数据未完整复现限制=已标明；原问题记录严格恢复=是；显式提交立即待审批=是；缺附件失败阻断=是；刷新持久化=是；指定审批人待办命中并具办理动作=是；提交时间/工作流记录=是；合同审批与用印审批独立=是；合同最终审批不重复提交=测试覆盖；所有截图非空且逐张目视确认=是；未线上写库=是。
- 构建/部署/版本/线上数据库：均未执行。
- 数据库补丁建议：筛选历史 `contract.data.sync_seal=true` 且关联 `seal` 仍为“草稿”的记录；仅当时间线/审计能证明用户已执行提交用印时，幂等改为“待审批”并补 `sync_seal_submitted_at`，同时校验 `data.approver` 为启用且有用印审批权限的账号。截图样本 `SHHT2673411 / YY202609011322136E1` 优先人工核对，不盲改。
- 主会话 Chrome 验收：线上仍须先回原记录 `SHHT2673411 / YY202609011322136E1`；现网快照仍是用印草稿，发布代码不会自动改变既有数据。先按数据库补丁建议人工审计并修复该原记录，再以原申请人核对“我的用印申请”，以原指定审批人核对“待审批用印”，刷新确认持久化；缺附件时必须阻断，非审批人不得办理。不得用新流程数据冒充原记录闭环。

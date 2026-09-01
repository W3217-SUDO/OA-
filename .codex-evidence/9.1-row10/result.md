# 9.1 第10行整改与验收记录

- reading-confirmation：已逐字读取 A-I，并查看 C10 锚定的 3 张原分辨率问题截图；D10 无旧系统目标图。问题是发布案件任务时，负责人和协作者搜索“范文”均缺少在职人员“范文林”。
- 旧系统只读实跑：使用本地旧系统 `localhost:8091` 的 admin/管理者账号，从案件中心原入口搜索原记录 `SHMS2600436`，结果为空，证据见 `legacy-original-case-missing-readonly.png`。随后以同业务角色、同模块、同任务发布流程的既有案件 `SHMS2600383` 作为替代记录，打开“案件任务→发布任务”，分别到达负责人、协作人选择入口并输入关键字；全程未保存、提交或写库。旧环境动态候选数据未完整复现，证据见 `legacy-equivalent-task-picker-readonly.png`，不得记为旧浏览器候选结果通过。
- 旧系统等价依据：两字段均使用 `AssociateAvailableUserForTask`，调用 `/Account/UserCenter/AvailableUsers`；控制器按中文名过滤有效员工，值为 `StaffName`、显示为 `StaffChName`。因此负责人和协作者共用完整有效员工目录是目标语义。
- 根因：新系统 `/cases/reference-options` 虽先读取有效 `User` 账号，却允许同 username 的冲突 HR 扩展档案覆盖账号中文名；冲突档案覆盖 `fwl/范文林` 后，两个人员选择器同时缺项。
- 修改：案件任务可分配人员严格限定为有效登录账号，选项显示名取对应 `User.display_name`；无独立账号的 HR 档案不伪装为可分配人员。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/case_reference_people_contract_test.py`。
- 新系统隔离验收：使用独立 SQLite、API `19175`、Web `19176`，在隔离库恢复同案号 `SHMS2600436` 并建立三个独立有效账号 `fwl/范文林`、`fwling/范文玲`、`fwll/范文玲玲`。负责人搜索“范文”完整显示三人（`local-owner-search-all-three.png`）；协作者搜索同样完整显示三人（`local-collaborator-search-all-three.png`）。
- 失败路径：在同案号 `SHMS2600436` 的案件任务发布窗保持任务主标题为空并点击确定，标题框变红且直接显示“请输入任务主标题”；背景任务列表仍为“暂无数据”，证据见 `local-empty-title-validation-no-insert.png`。隔离 SQLite 在点击前、点击后分别查询该案 task 数量，均为 0，确认校验失败未产生部分写入。
- 成功与刷新持久化：填写标题 `CODEX-901-R10-人员目录验收` 后创建成功，任务号 `RW20260901213553129755`；刷新并重新进入同案号案件任务列表，任务仍显示负责人范文林、状态进行中（`local-task-refresh-persisted.png`）。隔离库只读核对 owner=`fwl`、collaborators=`["fwling","fwll"]`。
- 截图核验：上述 6 张 PNG 均已确认文件非空并由本人逐张目视检查；四张新系统图能直接证明搜索完整性、失败校验无新增和刷新持久化。
- 聚焦测试：`python -m unittest case_reference_people_contract_test.py`，3/3 通过；`python -m py_compile app/main.py` 通过；`git diff --check` 通过。
- 数据库补丁建议：只读审计目标库 username=`fwl` 的 `users` 与全部在职 HR 档案。保留真实账号 `users.display_name=范文林`；若“范文玲”也为在职员工，应为其分配独立唯一 username，并修正 HR `data.username/owner`，禁止不同人员共享 `fwl`。本会话未写线上数据库。
- 清理：验收结束后关闭本任务 Chrome 标签/窗口，停止本任务 19175/19176 服务，并删除 row10 隔离 SQLite、恢复记录、测试用户和启动文件；不影响其他会话。
- 主会话线上验收步骤：部署并完成必要数据修复后，以具有案件任务发布权限的账号进入原记录 `SHMS2600436`；负责人搜索“范文”确认范文林、范文玲、范文玲玲按各自有效账号完整出现；协作者重复搜索并确认一致；分别选范文林为负责人、另两人为协作者，先验证缺标题失败，再成功提交并刷新，核对负责人和协作者仍对应所选账号。

# 9.1 第 5 行结果

- reading-confirmation：已读完整文字、C5 新系统图 1 张；D5 原系统列无图。
- 8.28/8.31 返工审计：两张历史工作表未命中“律师助理/助理”同项返工文字。
- 旧系统证据：`Legal.Case.Basic.Invoke.js` 使用可重复添加/删除的助理标签；`Legal.Case.js` 将全部账号/姓名按顺序序列化到 `CaseAssistant/CaseAssistantName`，固定任务等下游取逗号序列第一个助理。
- 根因：新系统普通案件编辑 schema、API 和弹窗均只接受单个 `assistant`；团队 payload 将助理压成单值，既无法保留完整集合，也不能稳定表达“集合第一项是最新助理、其他页面只投影第一项”。
- 修改：普通案件编辑新增有序 `assistants` 多选；前端把新加入助理移到最前并保留既有相对顺序；后端持久化 `assistants/assistant_usernames` 全集，同时以第一项维护兼容字段 `assistant/assistant_username`；全部助理进入 `case_team_usernames` 且均获得助理角色，其他既有界面继续读取单值字段，只显示最新助理。
- owned files：`apps/api-server/app/main.py`；`apps/api-server/case_multiple_assistants_row5_test.py`；`apps/admin-web/src/CaseCenterPage.tsx`；`apps/admin-web/caseMultipleAssistantsRow5.test.mjs`。
- 测试：新增隔离测试、基本信息遗留阶段/创建步骤回归共 7 项通过；前端静态契约通过；`py_compile`、`git diff --check` 通过。
- 非本行基线失败：扩大运行 `case_basic_phase_approval_independence_row4_test` 时，既有 `can_update_progress` 期望 false、实际 true；改动未触及进展 capability，未纳入本行修复。
- 构建/浏览器/部署/版本/线上数据库：依用户约束均未执行。
- 数据库补丁建议：无需 schema 迁移（JSON 兼容）。如需恢复历史多人助理，按旧库 `CaseAssistant/CaseAssistantName` 顺序幂等写入 `assistant_usernames/assistants`，并将第一项同步到单值投影；禁止仅用当前单值反推丢失的历史成员。
- 主会话 Chrome 验收：在案件 `SHMS2600438` 或本任务案件打开基本信息，依次选择旧助理 A、B，再新增 C，保存并刷新；编辑弹窗应显示 C/A/B，案件摘要和至少一个案件列表仅显示 C；分别用 A/B/C 账号验证均具备助理应有可见性；移除成员后再刷新验证集合、单值投影和权限同步；精确清理本任务数据。
- Chrome 实跑补充（原案件 `47150/SHMS2600438`，Admin 陶威）：公司案件→民事争议→原案件详情→操作→修改基本信息；多人选择控件可加入范应根、陶国南，但实跑发现原 `onChange` 在 Ant Design 已更新表单值后读取“previous”，新增识别始终为空，界面错误显示旧顺序“范文林、范应根、陶国南”。已改为 `onSelect` 将本次选中值置首、`onDeselect` 精确移除，并补强前端契约测试。修正后刷新时主会话提供的 `19026` 服务已拒绝连接，因此保存、刷新持久化、列表单值投影和移除边界尚未完成复验，本行不得判定浏览器通过。
- Chrome 二次实跑：服务恢复后再次操作同一原案件，确认同步 `onSelect` 写值仍会被 Select 随后的内部更新覆盖，最终标签回退为仅“范文林”。现改为在控件内部更新完成后的下一任务读取最终集合，将本次新增值移到首位；移除继续由控件原生多选状态处理。前端聚焦契约测试通过。该二次修正后的最终保存/刷新/列表/移除浏览器闭环尚未完成，本行仍不得判定浏览器通过。
- Chrome 最终追因：实际键盘交互确认当前 Ant Design 的 `onChange` 先于 `onSelect`，不能由同次 `onChange` 消费 `onSelect` ref；最终以聚焦时保存既有有序集合、`onChange(values)` 比较集合确定新增值的方式实现，无 `setTimeout`。另补齐 `normalizeCaseEditPayload` 遗漏的 `assistants`，此前该遗漏会把视觉标签以空数组提交。隔离恢复还缺原客户关系，已只在隔离库补建 `47153/KH-ROW5-RESTORED-TEST555` 并关联原案件。原案件保存后数据库持久化顺序及详情刷新均为 `陶国南、范应根、范文林`；但详情错误拼接全集，现已将 `_case_assistant_display` 改为仅投影第一项并补后端断言。API 19025 由主会话持有且未重启，最后这项后端投影改动尚未载入运行实例，因此列表单值投影与移除后的最终浏览器闭环等待主会话重启 API 后继续，本行仍不得判定完全通过。
- Chrome 最终闭环（API 重启后）：原案件 `47150/SHMS2600438` 详情刷新仅显示首项助理“陶国南”；公司案件→民事争议列表同一行仅显示“助理:陶国南”，不显示较早成员。重新打开基本信息弹窗按 `陶国南、范应根、范文林` 显示完整有序集合。以 Backspace 移除末尾较早成员“范文林”，保存并刷新后详情仍仅投影“陶国南”；隔离库最终精确值为 `assistant=陶国南`、`assistants=[陶国南,范应根]`、`assistant_username=tgn`、`assistant_usernames=[tgn,fanyg]`。隔离恢复补建客户 `47153/KH-ROW5-RESTORED-TEST555` 并写入原案件 `customer_record_id=47153`；线上数据未写。Chrome 标签已全部关闭，主会话服务未停止。
- Chrome 直接截图补证（独立实例 API `19125` / Web `19126`，隔离库 `.codex-runtime/row5/legal-platform-row5.db`）：`chrome-list-latest-assistant-only.png` 展示公司民事案件列表原案件 `SHMS2600438` 仅投影 `助理:陶国南`；`chrome-detail-latest-assistant-only.png` 展示同一原案件详情“律师助理=陶国南”；`chrome-edit-assistants-after-remove-refresh.png` 是重新进入原案件后打开的编辑弹窗，展示移除并保存刷新后仍按顺序持久化 `陶国南、范应根`。截图完成后 Chrome 标签及本会话独立服务均关闭。
- 第5行投影边界补测：当第一/最新助理可解析、第二个旧助理不可解析时，返回第一人的中文名且 `missing=False`；首助理不可解析时仍 `missing=True`。`python -m unittest case_multiple_assistants_row5_test.py`：2/2 通过。

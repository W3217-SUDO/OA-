# 9.1 第 14 行处理结果

- 状态：共享人员源修复与聚焦测试完成；未浏览器验收、未构建、未部署。
- 根因：共享 `/people/options` 仅使用 `User.display_name`；在职 HR 档案已维护中文姓名但账号显示名仍是缩写/旧值时，中文关键字匹配会漏掉有效人员。当前调查子任务负责人下拉也只按 label 过滤，无法用账号补充定位。
- 修改：共享人员接口优先使用在职 HR 档案标题作为中文姓名，并返回姓名+账号搜索文本；当前调查负责人下拉按该搜索文本进行不区分大小写包含匹配。所有复用 `/people/options` 的入口同步获得完整 HR 中文名。
- owned files：`apps/api-server/app/main.py`、`apps/api-server/people_options_chinese_match_row14_test.py`、`apps/admin-web/src/InvestigationCenterPage.tsx`、`.codex-evidence/9.1-row14/*`。
- 测试：`python -m unittest people_options_chinese_match_row14_test.py task_case_acceptance_status_row12_test.py task_serial_number_row11_test.py`，3/3 通过；Python 编译、`git diff --check` 通过。
- 数据库补丁建议：无需迁移；若线上存在 HR 在职档案与 User 无账号关联，应另做只读清单并人工维护关联，不能猜测映射。
- 主会话 Chrome 验收：在待我分配的调查任务选原截图记录 `DC20260810140152FCE1`，新增子任务；负责人依次输入“范”、完整中文名中段和账号片段，核对候选与 `/people/options` 全部命中一致。再抽查任务中心、案件人员选择等复用共享人员接口的入口，确保相同中文关键字不漏人。

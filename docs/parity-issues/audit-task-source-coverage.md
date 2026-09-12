# 审计工具任务页面源码覆盖误报

- **发现日期**：2026-09-12
- **问题类型**：审计工具缺陷，导致任务提醒功能产生误报
- **前端位置**：任务中心菜单；路由 `task-reminders`；任务中心页面与任务列表子组件
- **旧系统对比**：旧系统的提醒任务入口需要进入专用提醒视图并仅展示提醒范围；新系统实际已在 `tp/TaskCenterPage.tsx` 中实现 `isReminder`、`reminder_only` 请求参数和空状态处理。
- **新系统根因**：`scripts/audit-menu-coverage.py` 只读取 `src/TaskCenterPage.tsx` 的导出壳，未纳入实际实现文件 `src/tp/TaskCenterPage.tsx` 与 `src/tp/TaskList.tsx`，造成静态检查无法看到真实实现。
- **整改**：审计脚本改为合并读取任务中心实际实现及列表子组件后再执行规范化断言。
- **状态**：已修复，待完整本地审计与构建验证。
- **验收映射**：任务中心 -> 提醒任务；`TaskCenterPage` 的 `initialView === "task-reminders"`；请求字段 `reminder_only`；空结果分页/操作区行为。
- **残余风险**：尚未替代真实浏览器业务验收；需在完整本地验证中确认提醒接口返回范围与旧系统一致。

# 2026-10-14 工作台 AI 空间入口删除

## 用户需求与截图定位（修改前）

用户完整原文：`这个地方不需要 ，删除这个入口吧`

单张截图：`/var/folders/lm/3mbkryqx3_d766wf4fpc708r0000gn/T/codex-clipboard-cc13dc33-d116-4065-8d7c-69b21579538c.png`。已逐张查看（本任务仅此 1 张）。画面身份：申浩工作台、管理员、上方提醒指标、左侧工作概况和右侧开庭排期/审批驳回提醒；红框明确标注工作概况右上方的“AI 空间”按钮。证据角色：用户提供的新系统现状；不是 Excel 问题批次。

任务分类：直接独立 UI 删除需求；旧系统对照不适用。当前源码 `Dashboard.tsx` 在桌面仅渲染该按钮，在窄屏渲染“工作概况 / 助手对话 / AI 空间”三按钮；按钮使用本地 `personalSpaceOpen` 状态打开 `PersonalAiSpace` 弹层。此次删除工作台的按钮、专属状态、导入和弹层，不改变其他 AI 助手、案件 AI 空间能力。无 API、权限、状态流转、数据库、附件写入或测试数据需要修改。

原文追踪：“这个地方”对应截图红框及 `wb-view-switch` 工作台容器；“删除这个入口”对应工作台 `AI 空间` 按钮及专属弹层接线删除。桌面同步移除空容器；手机保留“工作概况 / 助手对话”两按钮。

当前独立托管工作树：`/Users/taowei/.codex/worktrees/dashboard-remove-ai-space/oa`，基线 `origin/dev`，HEAD `f4a2a65c`，前端版本 `1.1.370`。主工作区原有大量其他任务未提交改动，已将本任务精确小补丁转移到独立树并逐文件撤回主树自己的修改；没有覆盖其他任务内容。主树编辑前快照保存在 `/tmp/oa-dashboard-entry.GZmOUK/`，撤回后逐文件 diff 确认一致。CodeGraph 命令当前不可用，PM 已执行 status 并确认，使用直接源码补充定位。

## 手机适配定位（修改前）

`index.html` viewport 为 device-width；App 的窄屏判断为 `screen and (max-width: 991.98px)`，Dashboard 接收实际窄屏标志。`dashboard.css` 的工作台切换按钮规则在 max-width 1100px 内生效，原来三列。全仓库该容器只有本工作台使用；`mobile-chat-layout.css` 另有更高优先级的手机助手对话模式隐藏规则，保持原行为（助手面板仍有返回概况入口）；桌面专属 `is-desktop` 规则只服务此入口。本次移除桌面规则、将手机概况切换布局改为两列。保留 44px 最小按钮高度、焦点样式和已有页面滚动/底部导航规则。其他 AI 空间入口在 `PersonalAgentCenterPage`、`AssistantPanel`、`AssistantWorkspaceTools`，本任务不修改。

拟修改范围：`apps/admin-web/src/Dashboard.tsx`、`apps/admin-web/src/dashboard.css`、已有 `tests/architecture/centerViews.test.mjs` 的工作台入口断言、本独立记录。不得将其他脏改动计入成果；不新增测试脚本、不控制浏览器、不写业务数据。本任务执行代理不暂存、提交、推送、递增版本或部署，由 PM 核验与编排。

## 核验结果

独立树已完成精确删除：桌面工作台无入口及空容器，手机工作概况保留两个视图按钮并按两列布局；本地弹层状态与接线一起删除。未改其他 AI 空间入口或后端。

2026-10-14，Node.js 22：

- `node --test tests/architecture/centerViews.test.mjs`：5 / 5 通过。既有工作台测试覆盖手机无 AI 空间、两按钮，桌面无入口/空容器；原有指标导航、提醒交给智能体、关联查询权限和失败提示断言保留并通过。
- `npm run typecheck`：退出码 0。
- `git diff --check`：通过。
- 主树自身增量撤回后，与修改前 3 份快照逐文件 diff 退出码均为 0，无差异。

正式版本：PM 持有真实生产三处 mutex lease（PID 427629），通过权威 allocator 分配 `1.1.371`；本执行代理依据该明确分配回执同步 `package.json`、`package-lock.json` 顶层及根 package 的三处版本为 `1.1.371`，不猜号。

前端生产构建及实际构建 CSS 核验：等待 PM 精确提交后统一构建，避免重复构建。正式提交、推送、激活和线上健康尚未完成，待 PM 实际回执。页面浏览器/真机验收尚未执行。未创建业务测试数据、附件或后台写入，无业务清理项；未创建浏览器标签。本执行代理未暂存、提交、推送或部署。

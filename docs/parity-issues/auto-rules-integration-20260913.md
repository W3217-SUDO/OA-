# 自动任务规则整改：最新 dev 集成记录

## 授权与基线

- 用户要求新系统落实对应旧自动任务规则；同意“以 GitHub 最新 dev 为基础，保留并整合现有改动后再统一补齐”。
- 当前集成目录：C:/Users/Administrator/.codex/worktrees/oa-auto-rules-dev-20260913，分支 dev。
- GitHub 与服务器远端 dev 在开始时均为 e9949ed1e73ad1cdcf19c3a0868af4cf8ecf4a15；比原目录 HEAD 3533b8f0 多一条调查线索修复提交。已保留该提交的全部8个文件改动。
- 原目录 C:/Users/Administrator/.codex/worktrees/45fd/9.2-batch4-task-center 未移动、未清理、未重置。其21个已跟踪文件的未提交差异通过 git apply --check 后整体迁入，无冲突；37个 apps/docs/scripts 下未跟踪项目文件一并保留。
- 原本地 dev 指向86ab3992，其提交已保存在 refs/codex-backups/dev-before-auto-rules-20260913，再将本地 dev 对齐已获取的最新远端。未强推远端、未丢弃原提交。
- NUL、临时提示词、旧验收截图等非实现文件继续留在原目录，不纳入新集成产物。

## 本轮范围和分工

| 范围 | 状态 | 文件所有权 |
|---|---|---|
| 催收完成条件与仅更新任务的事务提交 | 本地修复，8项隔离测试通过 | A: core/tasks.py及独立测试 |
| 交接截止时间、旧类型上限与前后端兼容 | 本地修复，7项隔离API测试通过 | B: tp/router.py、models_shared.py、独立类型规则模块、交接前端与测试 |
| 旧28类调度宿主缺口补证 | 只读追踪完成；仍缺生成程序，明确待补 | C: legacy-auto-task-host-followup-20260913.md |
| 既有客户/案件修复整合回归 | 31项隔离API回归通过；拆分组件测试修正 | D: auto-rules-integration-review-20260913.md |

没有旧证据的初始触发条件不得自行补写。此前用户明确要求的交接5天未开始自动完成等规则保留；类型配置存在不等于28类业务闭环已实现。

## 已完成检查

- 新集成目录 npm ci 成功，未变更依赖版本。
- 菜单审计及客户端API路由审计通过，822个前端调用匹配API路由。这是结构检查，不是业务验收。
- 自动任务统一后端回归36/36通过，包含新增催收/事务8项、交接7项和原自动任务21项；165.908秒，内存SQLite，不写入业务库。
- 前端17个定向测试文件合并57/57通过，覆盖此次交接和保留的客户/案件/调查/任务改动。其中源码结构断言不等于真实浏览器业务验收。
- 客户/案件原修复31项隔离API回归通过；API审计工具自身8项测试通过。
- Python全量编译、TypeScript及Vite生产构建通过。Vite有既有大分包警告，没有构建失败。
- Git差异格式检查通过，CodeGraph初始化后完成调用链定位并同步，最终检查为已最新；图谱不作为业务验收证据。
- VibeHub术语核对：幂等性 -> https://vibe-hub.org/idempotency；仅用于表达重复扫描不应重复生成的要求，不替代旧业务证据。
- 服务器只读检查：sunhold-dev-api/web均active；实际WorkingDirectory位于/opt/sunhold-oa/worktrees/production-current。本轮未重启、未改服务器。

## 发布状态

本轮范围是最新dev的本地整合与证据明确的三项规则修复，不递增正式版本号、不执行服务器构建、不重启或部署8089。未改数据库结构，无需数据库备份。

实现提交为 `e7751a327a2c9a97872e685bc55a0a989a84c1bf`。已成功推送至服务器origin/dev及GitHub github/dev，并用两次ls-remote确认两端一致；本条为推送后的文档补记。GitHub main仅在实际正式发布成功后推进，本轮不推进main。线上运行版本不等同于dev集成版本。最终工作树检查无未提交改动（文档补记提交前本文件除外）；本轮辅助智能体全部关闭。

仍未证明：28类初始生成条件/GapDays完整消费程序、旧节点链/协作人节点、旧定时宿主实际策略、PostgreSQL并发行为及真实浏览器结果。未运行会清理共享SMOKE数据的完整verify-local.ps1/smoke-api.py，用隔离ASGI接口回归替代本轮验证；没有写表格完成状态1。

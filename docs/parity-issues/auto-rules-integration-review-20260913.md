# 自动任务整合前回归评审

2026-09-13。本记录仅评审本工作树基于 GitHub `dev` 提交 `e9949ed1` 整合后仍保留的客户/案件修复，以及主会话指定的四个前端测试读取入口。不修改旧系统数据、业务实现、线上环境或生产数据库；未提交、推送、部署、运行浏览器或全局 smoke。

## CodeGraph 与范围

- 已执行 `codegraph status` 与定向 `codegraph explore`。首次 explore 时索引不存在；最终 `codegraph sync` 成功建立并同步索引，当前为 1,323 个文件、18,449 个节点、53,397 条边，状态为最新。以下业务结论仍以定向源码和实际测试为证据，而非图谱本身。
- 本轮只修改四个测试的源码读取路径：`caseTaskChineseNameSearchRow19.test.mjs`、`caseTaskDetailColumns.test.mjs`、`caseDetailTaskPublishRow7.test.mjs`、`taskLifecycleActionsRows12To16.test.mjs`。未改 `core/tasks.py`、`areas/tp/router.py` 或任何业务代码；未修改主会话标注由 B 回归的其他测试。
- 已执行 `git diff --check`，通过。工作树原有未提交改动保留不动。

## 隔离与清理

所有后端命令均在 `apps/api-server` 执行，目标测试在模块导入前设置 `DATABASE_URL=sqlite+aiosqlite:///:memory:`，用 `StaticPool` 创建独立 schema，并在 teardown 关闭 HTTP client、恢复 FastAPI dependency overrides、释放 AsyncEngine。

`case_batch_delete_test.py` 额外用 `TemporaryDirectory(prefix="CODEX-case-batch-delete-")` 放置附件，并在 teardown 清理。该测试模拟的 `Path.unlink` 权限失败仅断言 `cleanup_pending`，未触碰工作树附件、共享目录或任何线上/生产数据库。

## 已通过的旧修复回归

以下 31 项均为真实 HTTP ASGI 路径上的内存 SQLite [回归测试](https://vibe-hub.org/regression-test)，退出码均为 0：

| 范围 | 测试数 | 覆盖结论 |
|---|---:|---|
| 客户回收站释放与拾回 | 6 | 个人、部门、公司回收站释放到公海；不可见记录不变；恢复；菜单能力路径均通过 |
| 回收站 D6 既有契约 | 2 | 已迁移/已回收可释放、公海拒绝；关联合同或案件时不可回收均通过 |
| 客户共享替换 | 7 | 删除/新增接收人、显式取消共享、幂等、空值/离职/禁用/无权限/公海回收站阻断均通过 |
| 最近联系与最近更新 | 6 | 日历月边界、闰年/跨年、时区、分页前过滤、角色和状态范围均通过 |
| 公司案件批量删除 | 10 | 整批校验与回滚、角色/可见性、外键冲突、单条兼容、共享物理文件与附件清理失败均通过 |

结论：本次自动任务规则整合没有破坏上述已存在的客户/案件修复，在 SQLite 隔离合同范围内可继续集成。仍未证明 PostgreSQL 并发锁、真实认证链和浏览器端行为；本轮未安排浏览器验收或部署，未将这些列为已验收。

## 拆分测试读取入口

主会话给出的命令初始为 13 项、6 通过、7 失败。失败都先读取旧的 re-export 壳：`src/CaseCenterPage.tsx` 或 `src/TaskCenterPage.tsx`。

本轮将四个测试改为读取真实组件，并保留全部既有正向和反向断言：

| 测试 | 真实读取范围 | 结果 |
|---|---|---|
| `caseTaskChineseNameSearchRow19.test.mjs` | `src/legal/CaseCenterPage.tsx` | 2 项通过 |
| `caseTaskDetailColumns.test.mjs` | `legal/CaseCenterPage.tsx`、`types.ts`、`CaseDetail/CaseTasksPanel.tsx`、`services/queriesActions.tsx` | 通过：列点击传递 `TaskRow`，处理器按 id 读取详情，详情展示 serial_no |
| `caseDetailTaskPublishRow7.test.mjs` | `legal/CaseCenterPage.tsx`、`CaseDetail/CaseTasksPanel.tsx`、`services/workflowActions.tsx` | 通过：父子传参、权限门禁、创建处理器、抽屉、持久化和刷新链完整 |
| `taskLifecycleActionsRows12To16.test.mjs` | `tp/TaskCenterPage.tsx`、`TaskList.tsx`、`TaskDetail.tsx` | 3 项通过：真实状态门禁与处理器绑定完整 |

重跑同一六文件 Node 命令结果：`13/13` 通过，退出码 `0`。四项原失效断言改为同强度跨组件契约，没有删除负向断言或放宽状态/权限要求。

案件任务详情的真实链为：列表列把 `TaskRow` 交给 `onOpenTask`，父组件以 `openRelatedTask` 校验 `task.id` 并调用 `loadCaseTaskDetail(task)`，查询层读取 `/records/${task.id}`，详情抽屉展示 `viewingCaseTask.serial_no`。这不是旧 `rememberTaskDetailTarget` 的跨页面路由，但 id 查询与 serial_no 呈现链完整。

## 未执行

- 未运行 `scripts/smoke-api.py`、完整 `verify-local.ps1`、npm build 或 npm install，避免共享数据清理与并发前端构建。
- 未执行旧系统写操作、网络访问、生产数据库访问、浏览器验收、提交、推送或部署。

## 给主会话的判断

客户/案件旧修复的 31 项隔离回归通过，可作为整合未破坏这些修复的证据。前端六文件的 13 项同强度跨组件断言现已全部通过；没有发现需要修改业务实现的缺失。本轮仍未做浏览器、部署或完整生产构建，后续统一流程应补齐这些未覆盖项。

## 追加 CRM 测试读取范围

主会话随后报告 `customerUiBatchI14.test.mjs` 的两个失败均读取了 `src/CustomerCenterPage.tsx` 的 re-export 壳。本轮只调整该测试的读取范围：零字节文件/照片反馈仍读取 `src/crm/CustomerCenterPage.tsx`；五处目录自动完成绑定读取真实渲染组件 `CustomerCreatePage.tsx`、`CustomerCreateEditModal.tsx` 和 `CustomerModals.tsx`。所有原断言保留。

追加该文件后与原六文件合并执行的 Node suite 为 `22/22` 通过、退出码 `0`。未改业务源码，未新增浏览器、部署、构建、提交或推送操作。

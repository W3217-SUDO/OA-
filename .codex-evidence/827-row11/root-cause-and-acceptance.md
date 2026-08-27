# OA 8.27 第11行：根因、数据库补丁与验收证据

## 范围与只读边界

- 仅处理《OA系统对接8.27.xlsx》工作表 `8.27` 第11行。
- 原始 Excel、旧系统页面/源码、旧系统迁移数据均只读；未修改第2–8行成果。
- 未改正式版本号，未打 tag，未部署，未切换 systemd，未连接或写入线上数据库，未把台账状态改为 `1`。

## 根因链路

1. 旧页面 `Areas/Legal/Views/CaseList/List.cshtml` 通过 `/Legal/CasePhase/GetCasePhaseList` 获取 `PhaseCaseCounts`，以 `ParentPhaseId` 构造左侧 zTree；点击父阶段后以全部后代阶段筛选案件。
2. 旧控制器 `Areas/Legal/Controllers/CasePhaseController.cs` 调用 `CaseSearchService.Instance.GetCaseCountGroupbyCasePhase` 返回计数；旧阶段主数据来源为只读迁移源 `PRD_CRM_GD_20200211.dbo.BAS_Case_Phase`。
3. 只读迁移主数据明确显示：`一审待执行`、`二审待执行` 的父级均为执行阶段；执行阶段按顺序共有12项；归档阶段共有7项。
4. 新系统前端 `LEGACY_PHASE_CHILDREN` 和后端 `DEFAULT_SYSTEM_PARAMETERS` 被后续提交错误改成：待执行挂到一审/二审，执行阶段只剩7项，并把 `提交法院`、`执行终结` 换成历史兼容名称。该错误同时影响左树展示、分组计数、阶段筛选、阶段选择器及执行状态入口。
5. 服务端 `/cases/search` 的 mine/department/company 数据范围和分页前 `phase_counts` 计算本身正确；问题集中在共享阶段目录及兼容筛选值。

## 旧系统权威阶段映射

- 一审阶段：不含 `一审待执行`。
- 二审阶段：不含 `二审待执行`。
- 再审阶段：保留 `再审待执行`。
- 执行阶段：`一审待执行`、`二审待执行`、`准备材料`、`提交法院`、`执行受理`、`执行中止`、`执行结案`、`执行终本`、`执行终结`、`执行亏损`、`执行异议`、`执行和解中`。
- 归档阶段：`归档审核`、`已归档`、`归档拒绝`、`亏损内审`、`亏损审核`、`亏损归档`、`亏损拒绝`。

## 整改内容

- 前端恢复上述完整目录，mine/department/company 共用同一权威定义。
- 父阶段筛选现在会展开每个子阶段的兼容别名，避免历史状态漏查。
- 兼容映射：`提交法院` 同时匹配 `执行立案`；`执行终结` 同时匹配 `终结执行`；另保留既有公证、一审开庭、归档审核和亏损拒绝兼容值。
- 后端执行状态白名单恢复完整阶段，并把历史 `执行立案`、`终结执行` 规范化为 `提交法院`、`执行终结`。
- 未改变 `CASE_PENDING_EXECUTION_PHASES`，因此第2–8行已集成的控制台待执行统计继续保留。

## 数据库补丁

不需要独立、一次性 SQL 文件。应用启动时已有的幂等参数协调器会按 `DEFAULT_SYSTEM_PARAMETERS`：

- 新增缺失的系统阶段参数；
- 修正既有阶段的 `name`、`extra.parent_code`、`extra.sort_order`；
- 重新启用应存在的阶段；
- 停用已从权威目录移除且由系统创建的民事阶段。

隔离 SQLite 启动后实测得到12条执行子阶段，排序 `501`–`512`，全部启用；`FIRST_CHILD_HAS_PENDING=0`、`SECOND_CHILD_HAS_PENDING=0`。该补丁只会在部署后由应用启动生命周期执行；本次未写共享本地库、旧库或线上库。

## 测试与构建

- 前端聚焦及相邻案件契约测试：25/25 通过。
- 后端阶段树、计数、执行状态契约测试：10/10 通过。
- 案件相关广覆盖前端测试：158/160 通过；2项失败是起点提交已有且与第11行无关的 `caseAuditExportAndCriminalOperations`、`caseDetailLegacySummary`，本分支未修改对应逻辑。
- `git diff --check`：通过。
- 生产构建：`tsc -b && vite build` 通过，5636个模块完成转换。

## 真实浏览器验收

验收实例：本工作树前端 + 本工作树 API + 隔离临时 SQLite；数据前缀 `CODEX-827-11-`。

1. 我的民事争议：执行阶段显示12项；执行阶段总计14，历史别名合并后 `提交法院【2】`、`执行终结【2】`。
2. 点击 `提交法院【2】`：列表仅显示规范状态 `CODEX-827-11-04` 和历史状态 `CODEX-827-11-13`，不显示其他状态，共2条。
3. 部门民事争议：同一12项执行阶段；一审阶段内不存在 `一审待执行`。
4. 公司民事争议：同一12项执行阶段；一审阶段内不存在 `一审待执行`。
5. 权限失败/隔离路径：普通用户打开公司民事争议只能看到本人 `CODEX-827-11-LIMITED`，看不到管理员的 `CODEX-827-11-01` 等14条验收数据；列表共1条。

截图：

- `browser-mine-civil-full-tree.png`
- `browser-mine-submit-court-alias.png`
- `browser-department-civil-full-tree.png`
- `browser-company-civil-full-tree.png`
- `browser-company-limited-scope.png`

## 测试数据清理

浏览器验收前隔离库共有15条 `CODEX-827-11-%` 案件（14条管理员阶段矩阵、1条普通用户权限记录）。验收后删除全部前缀数据和临时普通用户，确认计数为0；停止本工作树临时服务后删除整份隔离 SQLite。共享本地数据库无测试写入。

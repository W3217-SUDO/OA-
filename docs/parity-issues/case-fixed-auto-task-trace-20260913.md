# 案件详情：立案登记、送达跟踪自动任务来源追踪

后续补证：[旧系统自动任务规则与证据清单](./legacy-auto-task-rules-20260913.md)。已查本地恢复旧库，找到28类启用自动任务、SkipDays/GapDays及独立任务服务配置；具体自动生成宿主仍待定位。

日期：2026-09-13。状态：新系统静态调用链已定位；旧系统自动生成器尚未闭环。未修改业务代码、未部署、未验收。

## 用户证据与前端位置

- 用户原话：那你追踪一下这个逻辑 这个自动任务生成的逻辑。
- 截图：`C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-819628d9-5d23-4460-afca-40be83866370.png`。
- 页面：案件中心 -> 案件详情 -> 案件任务；上下文案号 SHMS2600439。
- 目标：类型“自动”的“立案登记”“送达跟踪”，以及提交时间、截止日期、发起人、负责人。
- 截图显示截止日分别 2026-09-09、2026-09-16，提交时间均 2026-09-01。未读取这两条线上数据库记录，不把源码推断当作该记录的实际历史。

## 新系统已确认调用链

源码路径均相对于当前工作树。

| 层级 | 源码与位置 | 已确认行为 |
|---|---|---|
| 页面 | apps/admin-web/src/legal/CaseDetail/CaseTasksPanel.tsx:46 | 渲染任务列表，提交时间取 created_at，缺失时取 submitted_at；按钮打开已有任务，不在此生成 |
| 类型标签 | apps/admin-web/src/legal/constants.tsx:154 | creation_mode=自动、task_type=固定任务或自动任务均可显示“自动”，不能凭该标签区分生成规则 |
| 查询 | apps/admin-web/src/legal/services/queriesActions.tsx:375 | GET /cases/{id}/tasks |
| 查询后端 | apps/api-server/app/areas/legal/router.py:3909 | 查询已关联任务、筛选并分页，不调用固定任务生成器 |
| 触发一 | apps/api-server/app/areas/legal/router.py:3249、3282 | 完成新建且处于待立案审批的案件，审批通过时调用；驳回不调用 |
| 触发二 | apps/api-server/app/areas/investigation/router.py:1585 | 已取证/待公证线索批量转案件，建立案件和关联后调用 |
| 生成器 | apps/api-server/app/core/permissions.py:1163 | _ensure_case_fixed_tasks，两个调用点均传 operator="system" |
| 剩余天数 | apps/api-server/app/core/tasks.py:206 | 截止日期减服务器当天日期，不是工作日计算 |

### 固定生成规则

1. 查询该案件已有 task_type=固定任务的任务，收集 fixed_task_key。
2. 缺少 filing-registration 时生成“立案登记—案号”，截止日期为调用当天加 7 个自然日。
3. 缺少 service-tracking 时生成“送达跟踪—案号”，截止日期为调用当天加 14 个自然日。
4. 两者初始状态为待接收，优先级普通；负责人取 case_record.owner，部门取案件部门，发起人为 system，协作人为空。
5. creation_mode 写“自动”，task_type 写“固定任务”，source 写“案件任务”，case_stage 固定写“立案”。并不根据法院受理日或送达日计算期限，也不读取任务模板配置。
6. 创建 BusinessRecord(module=task)，生成 RW 任务编号，flush 后调用通知函数；更新案件 fixed_tasks_generated 和 fixed_task_ids，由外层接口提交事务。
7. 已存在同键任务就跳过，不在此更新原任务的负责人或截止日期。这是查询式防重复；未证明并发时有数据库唯一约束保障。

截图的两个截止日期对应 9 月 2 日分别加 7/14 天，但截图提交日期为 9 月 1 日。日期差异的原因尚未核实，可能需要核对原始时间值、时区和历史变更；本轮不擅自归因。

## 与另一套新系统自动规则的区别

apps/api-server/app/core/tasks.py:1125 的 _ensure_phase_automatic_tasks 处理阶段触发；1204 的 _apply_case_automatic_task_rules 处理期限和业务条件补偿扫描。

apps/api-server/app/core/system.py:1023 的 _business_rule_loop 调用自动规则并每轮休眠 3600 秒；阶段修改接口也调用阶段规则。这些规则包括提交立案满 20 日跟进、到账满 30 日结算归档、执行和解等，不等同于截图中的固定 7/14 天任务。两套实现同时存在于当前源码。

## 旧系统真实源码证据与边界

旧 Web 根目录：`C:/Users/Administrator/Desktop/OA系统/OA系统_跨电脑继续开发_20260804_完整交接/旧系统归档源码/SH.CRM.WEB`。

反编译根目录：同级 `SH.CRM.Service.Decompiled`。GD/SH 按用户确认视为同一 OA 改名，不能用名称差异阻断。

- 页面读取：Scripts/Legal/Case/Legal.Case.js 的 CaseTasks.List -> /Legal/CaseTask/CaseTaskList -> TP.Task.TaskService.GetTaskList(caseId) -> TaskDao.GetTaskList(caseId)。任务来源不在页面列表生成。
- 反编译 Service/TP/Task/TaskService.cs:33 的 TaskCreateUpdate 当前方法体仅 return true；不能把它当作已经证明的任务创建实现。
- 同文件:38 的 Create(BizTask) 有真实创建逻辑：校验负责人；部分任务类型把 caseAssistant/caseLawyer 解析为案件助理/经办律师的首个账号；构建任务和节点。该方法与“自动触发入口”不是同一证据。
- 反编译 DataAccess/TP/Task/TaskDao.cs:17 的 Insert 写入 Legal_Case_Task，保存 TaskTypeId、CaseId/CaseNo、Initiator、Officer、Associates、TaskBeginTime/TaskEndTime 及节点关联。
- 反编译 Entity/TP/Task/TaskType.cs 包含提交立案任务(1010131)、文书准备(101011)、到账30日结算归档(1001003)、办理退费(1001004)等类型。
- 在本轮检索的旧 Web、业务 Service 和 DataAccess 中未检出“立案登记”“送达跟踪”文本，也未找到截图这两个 fixed_task_key 的旧规则。文本未命中只能说明当前证据不足，不能证明旧数据库任务配置/存储过程/调度中绝不存在对应行为。

## 待继续核实

1. 对照旧库自动任务存储过程、触发器及调度作业定义，确认各类型的真正触发条件、负责人、期限、重复生成和自动结束逻辑。
2. 只读核对截图两条任务的 fixed_task_key、auto_task_type、原始创建时间、截止日和审批/转案事件，确认实际生成来源与日期差异。
3. 根据完整旧规则决定两个新固定任务应保留、替换还是仅限某些入口；未确认前不删除现有业务任务。

## 验证和变更状态

- CodeGraph：本轮先检查状态及查询自动任务调用链；旧外部目录图谱未覆盖部分用 rg 和 C# 原文补证。
- Skill：已加载审计、问题处理和 VibeHub；术语查询无可靠匹配，不附会概念链接。
- 本轮仅追踪并记录，无业务修改、测试数据、浏览器操作、构建或服务器发布。
- 本文为本地追踪记录，未单独提交或推送 GitHub。

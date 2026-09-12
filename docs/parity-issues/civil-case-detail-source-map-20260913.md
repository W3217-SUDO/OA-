# [主要入口已定位，非全量验收] 民事案件详情前端与业务链映射

## 用户与截图
- 日期：2026-09-13。
- 用户原文：“你现在能找到旧系统这个里面所有的前端 跟对应逻辑吗”。
- 截图：`C:\Users\ADMINI~1\AppData\Local\Temp\codex-clipboard-676a5e7c-e5d8-4c8e-b9bd-1a0599a15a8e.png`，已查看消息中完整截图。
- 画面：民事案件详情，案件/法院信息、文档树、费用/事件/提醒/日志/任务/线索页签，右侧提醒和日志，右上操作与案件智能体。
- 用户已确认 GD 与 SH 是同一套 OA、只是改名。按同一业务系统对照，不把名称或 DLL 哈希不同当作停止工作条件；如具体方法出现差异，再定点核实，不预先假设业务不同。

## 源码根
- `W`：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\旧系统归档源码\SH.CRM.WEB`。
- `D`：同级 `SH.CRM.Service.Decompiled`。服务相对根为 `Dchien.Legal.Service/Dchien/Legal/Service`，DAO 相对根为 `Dchien.Legal.DataAccess/Dchien/Legal/DataAccess`。
- `N`：当前工作树 `apps/admin-web/src/legal`。
- 下表是逐项定位证据，不代表所有事件处理函数、分支、状态、SQL和浏览器行为已读完或已验收。

## 主入口已确认

`W/Areas/Legal/Controllers/CaseController.cs:35` 的 CaseView(id, caseNo) 调用 CaseService.GetCase(caseNo)，实际返回 `View("View", model)`。

真实主模板为 `W/Areas/Legal/Views/Case/View.cshtml`，而非同目录的 CaseInfo.cshtml，也不能把注释中的 CivilDispute/View 当成实际入口。主模板按案件类型渲染 CivilDisputeCase_View 等子模板，并加载 Legal.Case.js、Legal.Case.Invoke.js。

服务 `Legal/Case/CaseService.cs:1436` 的 GetCase 已读到调用 CaseDao.GetCaseByCaseNo、解析当事人代理 JSON、补客户名称/管理人、法院及法官名称的业务投影。

## 截图区块对应表

| 截图位置 | 旧前端/事件 | 旧控制器及已找到的下层 | 新前端位置 | 证据状态 |
|---|---|---|---|---|
| 案件信息、法院信息、律师/助理 | View.cshtml:337 -> PartialView/CivilDisputeCase/CivilDisputeCase_View.cshtml；Basic/法院/律师编辑模板 | CaseController.CaseView 与各编辑动作 -> CaseService -> CaseDao、人员/客户/法院服务 | CaseDetail/CaseDetailHeader.tsx、CaseCenterPage.tsx | 主模板、字段及部分取数已读；各编辑动作待逐条闭环 |
| 文档树、上传、查看下载、分类 | Legal.Case.Invoke.js:291 -> CaseFiles.Layout；Legal.Case.js:3074/3097；CaseFile 视图族 | CaseFileController.GetCaseFileList 按文件类型分支调用客户、合同、调查、线索、取证及案件文件服务；CaseFileTypeController.GetCaseFileTypeList -> CaseFileTypeService | CaseDetail/CaseDocumentsPanel.tsx、services/documentsActions.tsx | 已找到关联分支，全部文件类型/写动作尚未验收 |
| 生成操作 | View.cshtml:269 起授权委托书、一/二审/执行所函、身份证明；Legal.Case.js 生成处理 | CaseFileController.AuthorizationLetterCreate、ArchiveLetterCreate、LawyersLetterCreate、IdentificationLetterCreate -> CaseLetterBaseProcessFactory -> CaseFileService.Create | CaseDocumentsPanel、documentsActions | 已定位工厂及写入；实际模板/每种生成结果待逐项查 |
| 律所费用 | btnARCaseFeeList -> CaseFees.List；CaseFee/PartialView/CaseFeeList.cshtml | CaseFeeController.CaseFeeList -> FAM/AR/CaseFee/CaseFeeService；GroupId.Lawfirm 筛选并分页 | CaseDetail/CaseFeesPanel.tsx、services/financeActions.tsx | 已读控制器筛选、总数与分页 |
| 平台费用 | btnTradFeeList -> CaseFees.TradFeeList；TradFeeList.cshtml | CaseFeeController.TradFeeList -> 同一服务，GroupId.Trad 筛选并分页 | CaseFeesPanel、financeActions | 已读分组差别，不能仅按页签文字映射 |
| 内部结算 | btnInternalFeeList -> InternalFees.List；InternalFee/PartialView/List.cshtml | InternalFeeController.List -> FAM/InternalFee/InternalFeeService；另有新增/修改/付款关联删除分支 | CaseCenterPage、financeActions | 入口/服务已定位，付款及审批流程待审 |
| 案件提醒及右侧新增 | View.cshtml:404/408；btnCaseEventCreate -> CaseEvents.CaseEvent.Open | CaseEventController -> CaseEventService.CreateCaseEvent/GetCaseEvents -> CaseEventDao；新增后另写 CaseLogDao | CaseRemindersPanel、CaseCenterPage 侧栏、workflowActions | 已读新增提醒同时写案件日志，其他状态待审 |
| 案件日志、退费日志 | View.cshtml:433；btnCaseLogCreate/btnRefundLogCreate -> CaseLogs.CaseLog.Open/OpenForRefund | CaseLogController -> CaseLogService -> CaseLogDao | CaseLogsPanel、侧栏、workflowActions | 入口和服务已找到，新增/删改/类型筛选待审 |
| 系统日志 | btnCaseLogList -> CaseLogs.OperatingLogList；CaseOperatingLogList.cshtml | CaseLogController.CaseOperatingLogList -> CaseLogService.GetCaseLogs | CaseLogsPanel、CaseCenterPage | 已定位，不将案件日志和系统日志笼统合并 |
| 案件任务 | btnCaseTaskList -> CaseTasks.List；CaseTask/CaseTaskList.cshtml | CaseTaskController -> TP/Task/TaskService.GetTaskList(caseId) -> TaskDao.GetTaskList | CaseDetail/CaseTasksPanel.tsx | 已读按案件查询及人员/状态/剩余天数投影 |
| 客户任务 | btnVipCaseTaskList -> VipCaseTasks.List；VipCaseTask/CaseTaskList.cshtml | VipCaseTaskController -> TP/VipTask/TaskService.GetTaskList(caseId) -> TaskDao.GetVipTaskList | CaseCenterPage 内 customer-tasks 页签、CaseCustomerTasksPanel 的引入位置待继续追踪 | 旧独立任务查询已读，不能与普通任务混用 |
| 线索信息 | btnCaseClueList -> CaseClues.List；CaseClue 视图族 | CaseClueController.CaseClueList -> InvestigationClueService.GetInvestigationClueList | CaseDetail/CaseCluesPanel.tsx | 控制器关联已找到，筛选和下游取证待审 |
| 右上操作 | View.cshtml:135-320，基本信息/阶段/公证/律师/当事人/法院/金额/归档/复制/合并 | CaseController、CasePhaseController、CaseArchiveController 和 CaseService 等 | CaseCenterPage、workflowActions、编辑弹窗 | 主要菜单声明已读，各状态与权限不可只按入口存在判完成 |

## 不能直接宣称已全部对应的部分

- **资助费用**：找到 Legal/Views/Case/PartialView/CaseAssistedFeeList.cshtml，以及旧 Case.Create.CaseInfo.js 中指向 /IPR/Case/CaseAssistedFeeList/Create/Transact 的代码；IPR/CaseController 也有相应动作。但当前 Case/View.cshtml 主页签未挂该入口，旧文件存在不等于本民事详情实际启用。必须继续核实有效加载路径、业务类型和服务，不能拿零散旧模板直接定为本页标准。
- **独立“案件事件”页签**：已找到 CaseEvent 的旧提醒业务，但不能自动认定它与新 CaseEventsPanel 的独立事件实体相同。语义/类型/触发链需继续核对。
- **AI空间、案件智能体**：当前新源码有专门实现；本轮读取的旧主模板没有找到同名入口。按新功能单列保留，不为旧系统凭空补对应，也不因此删除新功能。
- 截图只是当前界面状态，不能证明所有折叠菜单和弹窗。完整映射还要覆盖按钮出现条件、请求参数、错误响应、状态流转、附件模板和下游查询。

## 状态与下一步

- 已建立本详情页主要功能的原始前端 -> 控制器 -> 服务/DAO -> 新前端映射；可以以此开展逐区块完整对齐。
- 本轮只源码定位与文档，不修改业务代码、不创建数据、不部署、不浏览器验收。
- 后续以表中每个入口为最小核查单位，读完服务与 SQL、补实际输入/角色/状态验证，确定差异后再统一整改；保持用户有意新增功能和已明确改变的权限策略。
- “可继续定位到下层”不等于“所有逻辑已读完”，不能把本文件当作整页已验收证明。

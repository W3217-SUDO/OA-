# 旧系统区域基线与新系统对应（进行中）

- 盘点日期：2026-09-12。
- 本轮实际读取的旧源码根：`C:/Users/Administrator/Desktop/OA系统/OA系统_跨电脑继续开发_20260804_完整交接/旧系统归档源码/SH.CRM.WEB`。
- 语言与证据：C# MVC 控制器、Razor `.cshtml`、JavaScript；**业务服务层已完整反编译**（`SH.CRM.Service.Decompiled/`，72 个 DLL，13,650 个 .cs 文件），服务层/DAO 层/SQL 不再是黑盒，可以直接核对业务规则与数据库操作。
- 下表为磁盘文件数量，不是有效业务页面数。副本、被注释入口、未挂载控制器必须在逐页追踪时剔除，不能以数量一致宣称对齐。
- 当前任务不是只修表格条目；所有有效区域都属于后续审计范围。每个确认差异须单独落到前端菜单、路由、按钮、字段和事件处理器。

| 旧 Areas 区域 | 控制器文件 | 视图文件 | 新系统候选对应 | 当前证据状态 |
|---|---:|---:|---|---|
| Account | 3 | 14 | App 登录、UserCenterPage、system 路由 | 待逐入口核对 |
| AWS | 4 | 18 | aws/DocumentCenterPage、aws 路由 | 待逐入口核对 |
| BAS | 5 | 4 | SystemCenterPage 参数与组织信息 | 待逐入口核对 |
| CIT | 10 | 43 | investigation/InvestigationCenterPage | 已读取线索 List 控制器/视图；服务范围未证明 |
| CMS | 11 | 39 | 待按控制器业务辨别，禁止仅凭缩写映射 | 待核实 |
| Console | 2 | 5 | Dashboard 与工作区外壳 | 待逐入口核对 |
| Contract | 1 | 3 | contract 页面族 | 待辨别与 FCM 的关系 |
| CRM | 9 | 38 | crm/CustomerCenterPage | 十列表路由/旧动作与查询分支已建矩阵；客户分配/拾回/共享/关闭/进入公海 服务层源码已通过反编译核实；共享保存本地已修，时间窗口待改，其余流程未证明 |
| FAM | 26 | 177 | finance 页面族 | 仅静态工具通过，未逐页证明 |
| FAS | 7 | 41 | finance 页面族 | 仅静态工具通过，未逐页证明 |
| FCM | 10 | 42 | contract 页面族 | 初步审计完成（见 contract-module-parity-audit.md）；删除/审批/归档/级联更新已定位；客户分配级联更新合同owner已核实SQL |
| FIO | 3 | 20 | finance 页面族 | 待逐入口核对 |
| FSC | 3 | 2 | 待按控制器业务辨别 | 待核实 |
| HR | 4 | 20 | HrCenterPage、OrganizationCenterPage | 待逐入口核对 |
| IPR | 30 | 138 | ipr 页面族 | 待逐入口核对 |
| Lawsuit | 15 | 78 | legal 页面族 | 待核对与 Legal 的入口差别 |
| Legal | 16 | 175 | legal/CaseCenterPage | 初步结构审计完成（见 case-module-parity-audit.md）；删除/分配/合并/参与人/列表范围 已定位差异点；逻辑删除vs物理删除为重要差异；服务层源码已完整可查 |
| RPT | 1 | 15 | ReportCenterPage | 仅静态工具通过，未逐页证明 |
| System | 3 | 44 | system 页面族 | 待逐入口核对 |
| TP | 8 | 37 | tp/TaskCenterPage、VipTaskCenterPage | 已核对普通任务列表操作区、创建模板和注释删除链接 |
| WMS | 2 | 2 | WarehousePage | 待逐入口核对 |

`AFM`、`bin` 没有本次统计类型文件；`Console - 副本` 为另一个目录（2 个控制器、5 个视图），暂不当作独立业务区域计入，仍需核对真实路由注册。

## 本轮已定位的页面证据
- `Areas/TP/Views/Task/TaskList.cshtml:600`：底部 `tfoot` 默认隐藏，601-625 行为撤回、验收、接受、完成、转交等操作，不是通用新建按钮。
- `Areas/TP/Views/Task/TaskCreate.cshtml:239` 与 `Create.cshtml:265`：真实创建提交控件。`Scripts/TP/Task/Legal.Task.js:279,347` 为 TaskCreate 与 CreateUpdate 请求。
- `Areas/TP/Views/Task/TaskDetail.cshtml:156-200`：删除/重新打开等链接位于 Razor 注释内；不能作为当前有效删除入口。控制器仍有删除方法不等于用户可用功能。
- `Areas/CIT/Controllers/InvestigationClueController.cs:33-57`：List 传入 PageId，POST 交给 `InvestigationClueService`；单凭控制器不能证明管理员在个人线索列表应看到全所数据。
- 新系统个人线索明确由 `areas/legal/router.py:641` 的 `scope=mine` 和前端 owner 过滤共同限定；个人调查任务使用另一个真实角色判断，必须分别检查。

## 下一步
将每个区域展开到有效控制器动作 -> Razor/JS 按钮 -> 新页面/接口 -> 数据/权限/状态证据，先整理整批确认差异，再集中修改；不得将当前候选映射当成已对齐。

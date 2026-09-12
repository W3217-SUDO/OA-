# 旧自动任务宿主补证（只读）

日期：2026-09-13。任务 C 的限定补证：只读检查旧服务归档、已有本地旧系统 source 和既有反编译产物；未修改业务源码、未运行旧作业、未写入旧库或 SQLite、未运行浏览器、未提交/推送/部署。

## 结论

未找到 28 类自动任务生成器或候选自动完成器的可执行宿主、`ThreadBase` 派生类或启动入口。因此不能把 `Sys_ProcessSchedule` 中的“任务服务”配置，或 `TaskDao` 的候选查询，解释成任一类型已经有可还原的生成条件、触发频率、幂等策略或自动结束调用链。

本仓库的 CodeGraph 在检查时为 `Not initialized`；未初始化图谱不能提供调用链或 blast radius，故本次使用下列外部旧系统原文作定向补证，未对当前业务源码作推断。

## 已确认的框架边界

- `C:/Users/Administrator/Desktop/OA系统/OA系统_跨电脑继续开发_20260804_完整交接/旧系统归档源码/SH.CRM.Service.Decompiled/Dchien.Legal.Infrastructure/Dchien/Legal/Infrastructure/Thread/ThreadBase.cs:46`：构造函数只接收 `SystemID`；`SystemMonitor()` 从 `ProcessScheduleDao.GetInfo` 读取配置，按 `LastRunStatus` 启停工作线程。
- 同文件 `:137`：工作线程只调用抽象 `Process()`；实现类必须在外部宿主程序集内提供。因此 `ThreadBase` 本身不含任务创建、完成或验收规则。
- 同文件 `:53-67, :226-232`：`CheckInterval` 和普通 `RunInterval` 分别换算为毫秒；当 `SystemParameter3/4/5` 构成有效定点配置时会改走每日/每周/每月分支。没有具体派生类与数据库行参数，不能将已知的 30、5 直接断言为任务生成周期。
- `.../Dchien.Legal.Infrastructure/.../Thread/ProcessScheduleDao.cs:10-16`：该 DAO 只读写 `dbo.Sys_ProcessSchedule` 配置及运行时间；不调用 `TaskService`。
- 在反编译根目录中仅定向搜索 `Dchien.Legal.Infrastructure`、`Dchien.Legal.Service`、`Dchien.Legal.DataAccess`、`Dchien.Legal.Web` 的 `*.cs`，未检出 `class ... : ThreadBase`；`ThreadBase` 的引用仅在其自身和 `ProcessScheduleDao`。

## 任务候选查询的实际止点

`.../Dchien.Legal.DataAccess/Dchien/Legal/DataAccess/TP/Task/TaskDao.cs` 存在下列候选查询：

- `:1147` 到期任务；`:1169` 退费类型 `1001004`；`:1191` 完成后待确认；`:1213` 出库；`:1235` 销毁；`:1257` 离职负责人；`:1279` 到账归档 `1001003`；`:1301` 文书准备 `101011`；`:1323` 催收代理费 `1001005`；`:1345` 公证审核 `101002`。
- `.../Dchien.Legal.Service/Dchien/Legal/Service/TP/Task/TaskService.cs:1396, 1464, 1498` 只将部分 DAO 结果转换为 `BizTask` 返回。对 `Dchien.Legal.Service`、`Dchien.Legal.Web`、`Dchien.Legal.Infrastructure` 的同名候选方法和类型 ID 进行定向全文搜索，未找到调用这些候选结果后再调用 `Finished`、`Checked` 或 `Create` 的外层消费者。

这证明“有候选查询/服务封装”，不证明自动完成、验收、创建或通知已发生。

## 已有本地归档/source 的宿主检查

- 已反编译 API 产物：`C:/Users/Administrator/Desktop/OA系统/_service_decompiled/auto-task-trace-20260913/Dchien.OA.Business`。已有证据仅覆盖 `Dchien.OA.Business.dll`；其中发现的是任务查询、创建、接受、完成、验收、拒绝、交接接口，未发现自动调度宿主。不能外推为全部 API DLL 都已检查。
- 本地恢复 source：`C:/Users/Administrator/Desktop/OA系统/legacy-gdcrm-101-local-20260812/source/`。可见的是 `GD.CRM.WEB`、`GD.CRM.WEB.API`、`GD.CRM.WEB.VIP` Web 宿主；发现 `GD.CRM.WEB/bin/Dchien.Legal.Service.dll.config`，未发现独立的任务/调度 Windows 服务 EXE、服务配置或源项目。已排除 `packages`、`node_modules`、Debug/Release 二进制目录，未泛扫第三方依赖。
- 另两个既有本地目录 `旧系统本地重建_20260812`、`legacy-system-local-20260812` 在该范围内未产出相关任务服务宿主路径。

## 不可安全补写的 28 类

对以下全部启用类型，均**不能安全补写**“首次何时生成、由何案件阶段/费用/证物事件触发、负责人如何确定、`GapDays` 如何参与、重复扫描如何幂等、失败如何重试、是否自动完成/验收”：

`100015, 100016, 100020, 101002, 101011, 101020, 101023, 101024, 102017, 102023, 102024, 103015, 103023, 103024, 104011, 104012, 104014, 104015, 106012, 1001001, 1001002, 1001003, 1001004, 1001005, 1010131, 1001003001, 1001003002, 1001003003`。

其中 `101002`、`101011`、`1001003`、`1001004`、`1001005` 和部分证物相关类型虽有“完成候选”证据，仍缺候选消费者，故也不可将候选直接实现为新系统自动状态变更。其余类型在本次证据范围内连初始生成候选也没有找到。

## 需要的后续证据

1. 旧服务器“任务服务”实际 Windows 服务名、可执行文件/程序集、启动参数和配置（尤其 `SystemId` 到实现类的映射）。
2. 对应宿主 DLL 的可读反编译结果，包括每个 `ThreadBase.Process()` 实现及其 `TaskService.Create/Finished/Checked` 调用。
3. 只读确认的 `Sys_ProcessSchedule` 任务服务完整配置行及最近运行记录；配置仅能佐证运行开关和周期，不能替代代码调用链。
4. 若宿主不再可得，则应将 28 类的未知生成规则保留为“未证实”，不以新系统现有硬编码期限或猜测阶段条件填补。

## 工作树状态

本任务仅新增本文档；保留整合目录原有未提交改动，不执行测试写数据，因此无测试数据需要清理。

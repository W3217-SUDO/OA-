# [可继续审计] 反编译服务层与全量对齐可行性评估

## 用户补充，优先于初次评估
- 用户确认：“这两个都是一个oa系统 只是改了名字而已”。GD/SH 视为同一业务系统的命名差异；不再把目录名或 DLL 哈希不同作为全局阻断，也不要求先重复反编译才能继续审计。
- 下文哈希是二进制溯源证据，不是业务逻辑不同的证明；仅遇到具体方法/字段/流程冲突时定点核实。
- 已继续定位截图中的民事案件详情，见 `civil-case-detail-source-map-20260913.md`。服务导出目录仍有其他任务追加文件，早先 15 目录/4031 文件仅为当时快照，不是最终数。

## 用户请求与本轮范围
- 日期：2026-09-13。
- 用户原文：“查看我源码文件夹 我刚才反编译我服务器层的源码 你看看 能不能把旧系统跟新系统做全量对齐呢”。
- 本轮只盘点源码、抽查业务链和比较本地 DLL，不修改业务代码、不编译反编译源码、不访问或部署服务器。
- 结论：已具备比此前仅有 Web 源码更完整的全系统功能审计基础；但 DLL 版本基线、数据库逻辑、导出完整性和真实页面闭环尚须验证，不能宣布具备无缺口的全量源码或系统已对齐。

## 找到的文件
- 完整反编译根：`C:\Users\Administrator\Desktop\OA系统\OA系统_跨电脑继续开发_20260804_完整交接\旧系统归档源码\SH.CRM.Service.Decompiled`。
- 原始 Web 根：相邻的 `SH.CRM.WEB`，包含 C# 控制器、Razor 页面和 JavaScript。
- 临时客户文件：`C:\Users\Administrator\Desktop\OA系统\_service_decompiled` 只有 CustomerService.cs、CustomerDao.cs，不能拿该目录代表完整导出。
- 磁盘实查：完整根 15 个程序集子目录、4031 个 .cs 文件、0 个 .csproj。README 写 3497 个文件，与当前磁盘总数不同；以后按实际清单核实，不按说明中的旧总数推断完整性。

| 核心目录 | 实查 .cs 文件数 | 主要用途 |
|---|---:|---|
| Dchien.Legal.Service | 157 | 业务规则、事务、审批、分配、状态流转 |
| Dchien.Legal.DataAccess | 117 | 查询 SQL、数据范围、数据库写入、存储过程调用 |
| Dchien.Legal.Entity | 266 | 实体字段、状态标记与业务关联 |
| Dchien.Legal.BizModel | 201 | 页面返回模型、业务输入与搜索条件 |
| Dchien.Legal.Common | 45 | 公共业务辅助逻辑 |
| Dchien.Legal.Infrastructure | 33 | 基础设施 |
| Dchien.Legal.Web | 326 | 编译后的 Web 层补充证据，不能自动替代原始页面文件 |

服务层可见 CRM、FCM、FAM、Legal、TP、HR、AWS、WMS、BAS 等业务目录。其余文件包含第三方框架/文书/压缩库，文件总量不等于有效业务功能数，不必全量移植这些库。

## 关键发现：SH 目录中的导出来源是 GD DLL

反编译 README 记录来源为 `legacy-gdcrm-101-local-20260812/source/GD.CRM.WEB/bin/`。本轮将该目录与原始 `SH.CRM.WEB/bin/` 中四个核心 DLL 的 SHA256 实际比较，全部不同：

| DLL | GD SHA256 | SH SHA256 |
|---|---|---|
| Dchien.Legal.Service.dll | 8D6E461BA9C658D89EDE19F56BAEAFD4125D5873417E69F14C478EF81F92B4A1 | A8AEF7CA49EBA64B7771F41146BFF79F8F1709052D665CAD6E997010311BC6E6 |
| Dchien.Legal.DataAccess.dll | 3AA6A9840E2FA1804EA243AB08D5E47F150800EBB7D472B98EFB31627295AE28 | BC15D3EF84E4E54FFC72F967D17012AE225C9987D167B16BEDD50FD116F8BD19 |
| Dchien.Legal.Entity.dll | CB0A2438B8D1D571D587B6560FB6FE0898827D68D2AF86CEA25073AF5C420EBE | A3D77D76ECE6A2994A6CD8111E13FCC6A94C0DA62D335F4A1E95B49CBE1CD693 |
| Dchien.Legal.BizModel.dll | 91155671534586BCE40253FA1AABC5FBB4C45E707CB557A066BF113FD44B69E9 | EB8371ECE3317837FCB329A0304B1DA9E2BD144FB94A0A64518FD81E587857A1 |

哈希不同仅证明二进制不相同，不能直接推出方法业务不同，也不能据此判定哪套就是线上最终版本。需要建立目标旧站 -> DLL 哈希/MVID/依赖 -> 同版本 Web/SQL 基线。当前没有访问服务器确认运行 DLL；不得仅凭目录名把 GD 服务与 SH 页面拼成权威完整基线。

## 抽样读通的链路及前端对应

样本：客户管理 -> 个人/部门/公司回收站 -> 更多操作 -> 进入公海，以及公海客户 -> 拾回。

- 旧页面：CustomerList.cshtml 的 6001002/6001004/6001010；脚本 CRM.Customer.js 的 InOpen/InClose；控制器 CustomerOpen/CustomerClose。
- 新页面：crm/CustomerCenterPage.tsx，route customer-recycle/customer-dept-recycle/customer-company-recycle/customer-public；originalActionItems、releaseCustomer、action；后端 release_customer/claim_customer。
- 本次反编译 CustomerService.cs:658 的 OpenCustomer 设置 IsOpened=T 与修改时间/人员，交给 CustomerDao.OpenCustomer。
- CustomerDao.cs:150 的 SQL 仅更新 IsOpened 及修改字段，不更新 IsActived，也不清空原负责人字段。
- CustomerService.CloseCustomer 设置 IsOpened=F、IsActived=T，并将 BusinessOwner、CustomerOwner、Holder 设为当前用户；CustomerDao.cs:164 的 SQL实际持久化这些字段。
- DeleteCustomer 明确先检查合同数、案件数再设置 IsActived=F；RestoreCustomer 仅设置 IsActived=T。
- CustomerEntity 同时保存 IsActived、IsOpened、BusinessOwner、CustomerOwner、Holder。新系统使用单一 status 和 owner 等投影，不能仅凭字段数量不同判为缺陷，必须核对组合状态、各角色和后续查询结果是否保持业务含义。
- 这一抽样说明新增源码能进一步确认原子状态、归属和 SQL 影响，但因 GD/SH 基线未统一，本轮不据此擅改 release 的归属逻辑。既有回收站修复的验证状态以原问题记录和后续实际测试为准。

## 尚不能由反编译目录独自证明的内容

1. 数据库逻辑：已见 CaseDao 调用 dbo.P_Legal_Case_EventGenerate、dbo.P_Legal_Case_No_Create，ContractDao 调用 P_FCM_Contract_No_Create 等。方法调用可读不代表存储过程实现已读；须补查目标数据库中的过程、视图、触发器、函数和任务调度。未在本轮判断这些 SQL 文件是否已存在其他归档中。
2. 导出完整性：README 说明过滤了编译器生成类型、缺项目/引用/资源。四个核心目录未搜到常见反编译失败标记，但这不是逐方法完整性证明；须结合 DLL 类型/方法清单、反编译日志与 IL 核对缺失或异常方法。
3. 配置与外部资源：部署配置、菜单/岗位/角色数据、模板、附件、外部接口和定时任务应另外取证，不把第三方 DLL 的实现当作必须重写的业务规则。
4. 实际行为：反编译文件不能直接保证可编译运行，也不能代替新旧页面、真实角色、异常路径、持久化和下游关联验证。
5. 用户特意改变的规则：例如菜单开放后页面动作开放，优先用户当前需求，不能机械恢复旧限制。个人/部门列表业务语义与动作权限分别核实。

## 建议执行顺序

1. 按用户确认的同一 OA 使用原始 Web 和当前反编译业务源码继续逐入口审计；记录来源，仅遇到具体逻辑冲突再比较相应方法，不覆盖用户导出产物。
2. 建立同版本原始 Web + 服务 + DAO + 实体/模型 + 数据库 SQL + 配置/模板清单；缺失项单独列出。
3. 按全部有效菜单建立“页面/按钮/字段 -> 控制器 -> 服务方法 -> SQL/状态/关联 -> 新 React/API/模型”的映射，不按表格范围或反编译文件数宣布完成。
4. 输出全量差异矩阵，区分确定缺口、用户要求的有意差异、基线不明项；每个真实问题独立 MD，落实到前端入口。
5. 统一安排本地整改和回归，再按用户授权决定是否部署；页面测试仅 Chrome，旧系统和现有业务数据保持只读。

## 本轮交付状态
- 已完成目录盘点、核心四 DLL 哈希比较、客户公海链路抽样、数据库过程依赖识别。
- 未执行业务修复、测试或发布，没有改变原交接中的工作树成果。
- VibeHub 使用脱敏词“功能对等”“调用链”核对，无可靠匹配，不添加术语链接。
- 该评估不是全系统对齐完成报告。先解决基线身份问题，再扩大服务/数据链审计，能显著减少此前只依据页面推断的误判。

# Task 26：知产中心 CPC 专利申报

## 原始任务要求

在知产案件操作中增加 CPC 专利申报入口，提供申报文件生成、申报文件下载和申报历史记录；后端提供申报接口、基本 CPC 格式专利申报信息文件和记录管理；若完整 CPC 格式复杂，先交付前端入口、后端接口框架和基础申报信息文件，并保持知产中心既有风格和前端本地构建通过。

## 实施前需求与旧系统证据

- 旧系统入口：IPR 案件文件列表的右键菜单 `生成申请文件`。菜单受 `Permission.CaseFile_CPC` 控制，并且仅在案件类型 ID 为 `1`、`2`、`3` 时显示。
- 调用链：`Scripts/IPR/Case/Case.Create.CaseInfo.js` 的 `CaseFile.CPC.Create()` 先拒绝未保存案件，再 POST `/IPR/CPC/GeneratePatentApplication`，参数仅为 `caseId`。成功后以返回的文件名调用 `CaseFileCenter/CPCFileDownload` 下载，并提示生成成功。
- 控制器：`Areas/IPR/Controllers/CPCController.cs` 获取案件，调用 `CPCServiceFactory.Create(c)`、`PreCheck()` 和 `Generate()`；成功返回 `cpc.ZipFile`。因此旧系统对外产物是 ZIP 文件包，且生成前存在业务字段预检。
- 依赖限制：`Dchien.Legal.Service.IPR.CPC` 的服务实现未随可读旧系统源码提供；仅找到其被控制器引用和 `bin/Dchien.Legal.Common.xml` 的符号文档。因此无法依据该源码复刻国家知识产权局 CPC 的内部模板、字段映射或压缩包目录；本轮以可审计的基础信息 ZIP 为最低可用交付，不能声称已满足官方客户端导入格式。

## 本轮最小闭环

1. 专利案件操作入口仅对专利类型显示，并沿用知产案件权限和数据范围校验。
2. 生成接口先校验案件存在、为专利类型、处于可办理状态及可用基础信息；成功写入受控 ZIP、申报记录和工作流日志。每次生成应创建一个不可覆盖的申报快照，以保留历史；不以“重复生成”作为通用阻断理由。
3. 申报历史返回当前用户可见的记录；下载接口以记录 ID 校验归属后返回实际 ZIP，不接受任意路径或文件名。
4. ZIP 包含 UTF-8 编码的 `CPC基础申报信息.txt` 与 `CPC基础申报信息.json`：文本列出案件号、案件名称、申请人、申请号、申请类型、客户、生成时间与生成操作人；JSON 仅保留用于基础申报信息的字段；缺少案件名称或申请人时明确阻断。

## 新系统根因与改动清单

- 根因：`apps/admin-web/src/IprCenterPage.tsx` 的知产案件操作列此前没有 CPC 入口、历史状态和下载动作；`apps/api-server/app/main.py` 只存在“把某个已上传案件附件压缩为申请文件包”的 `/files/{attachment_id}/generate-application`，它依赖源附件，不能等同于旧 CPCController 的按案件生成动作，也没有 CPC 专用历史接口。
- 后端实现：`apps/api-server/app/ipr_cpc.py` 提供按案件生成、查询历史、按申报记录下载的专用 CPC Router；`apps/api-server/app/main.py` 注入既有案件可见/可写守卫并注册 Router。复用 `FileAttachment` 与 `WorkflowEvent` 保存快照，无需模型迁移；下载不接受自由路径或客户端文件名。
- 前端修改目标：在 `apps/admin-web/src/IprCenterPage.tsx` 的专利案件操作列增加入口，并在详情展示历史、下载和生成反馈；非专利案件不出现入口。
- 验收修改目标：仅在现有审计无法覆盖 CPC 行为时，向 `scripts/audit-menu-coverage.py` / `scripts/smoke-api.py` 增加最小、无副作用的静态或本地测试覆盖。

## 待验收证据

- [ ] 前端入口、生成、下载和历史查看的浏览器可达性（当前无运行本工作树的可控页面）。
- [x] 后端生成、历史、下载、专利类型/基础字段/权限阻断，以及结案后只读。
- [x] ZIP 内容和申报记录/工作流日志关联；重复生成保留独立历史快照。
- [x] 前端生产构建、Python 编译、定向 API 验证与 API 路由覆盖校验。

## 结论边界

本实现是“CPC 申报基础信息包”，用于恢复旧功能的入口、预检、产物、下载和历史闭环。正式 CPC 客户端可导入包仍依赖缺失的旧服务实现、官方模板及其字段规则，须在取得这些资料后替换生成器并做客户端导入验收。

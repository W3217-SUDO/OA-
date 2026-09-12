# [本地自动化验证通过，待页面验收] 公司案件多选删除只处理第一条

## 页面位置
- 发现日期：2026-09-12；来源：主动旧新源码对比。
- 菜单：案件中心 -> 公司案件；动作：列表多选后点击“删除案件”，打开删除确认弹窗。
- 新前端：`legal/CaseCenterPage.tsx` 的 `selectedCase = ...find(...)`、`canDeleteSelectedCompanyCase` 和删除按钮；`legal/services/workflowActions.tsx:deleteCompanyCase`。
- 路由：`?page=case-company` 及 `case-company-*` 普通案件列表，含民事、刑事、仲裁、行政、执行、法律顾问；页面标题“案件列表”，底部 `aria-label="删除案件"`。
- 原接口：`DELETE /cases/{case_id}`；整改后按钮调用 `POST /cases/batch-delete`，单条接口继续兼容。

## 旧系统证据
- 源码根见 [legacy-area-baseline.md](./legacy-area-baseline.md)。
- `Areas/Legal/Views/CaseList/PartialView/CivilDisputeCase/List.cshtml:209-214`：按公司案件 PageId 提供有效的 `btnCaseDelete`。
- `Scripts/Legal/Case/Legal.Case.List.Invoke.js:97-104`：读取 `$.checkbox.vals("chkCaseId")`，仅阻断空选择，向 `c.Cases.Case.Delete(chkCaseIds)` 传递整个数组。
- `Areas/Legal/Controllers/CaseController.cs:1071-1077`：`CaseDelete(List<string> caseNos)` 将整个列表交给 `CaseService.Instance.DeleteCase`。
- 尚未证明旧业务服务内部事务/关联删除规则，不依据控制器推断可以无条件删除。

## 新系统证据与差异
- `CaseCenterPage.tsx` 用 `.find` 获取第一条选择；列表另有 `selectedCases` 全量选择数组，但删除动作未使用它。
- `deleteCompanyCase(row)` 的确认文案只描述单条，API 请求只带 `row.id`；成功后清空全部勾选并刷新。
- 因而旧系统的多条删除意图没有完整传递，批量选择可能被静默缩减成一条。
- 同类风险：其他公司案件类型复用同一删除按钮/handler，需要一起覆盖，不能仅修民事列表。

## 整改要求与出口
- 对完整选择集预检菜单访问、每条数据范围、状态和关联约束；任一不允许时在执行前明确反馈，不得部分删除后伪报全部成功。
- 后端采用受控批量删除流程，不能由前端循环单条接口制造半完成批次；精确清理本批案件所属附件和任务，保留审计证据。
- 复核“仅管理员/经理”限制与用户菜单授权要求，关联记录见 [case-delete-menu-capability.md](./case-delete-menu-capability.md)。
- 定向验证：空选择、单条、两条、多条含无权记录、已归档/已合并、有关联费用/任务/附件、事务失败与刷新后的选择集。
- 当前状态：本地已修改并通过隔离自动化验证；未部署，不操作已有业务数据。

## 2026-09-12 整改进展
- CodeGraph：`delete_case` 位于 legal/router.py，由 main.py 分片挂载；现有覆盖未找到，新增专项测试。新增路由追加在末尾并单独注册 141:142，未移动历史分片。
- `CaseCenterPage.tsx`：删除按钮使用全部 `selectedCases`，所有记录均须具有删除能力；可见行与勾选数量不符时禁用，不允许静默丢弃跨页或失效选择。
- `workflowActions.tsx:deleteCompanyCase`：确认弹窗显示删除总数；一次请求传完整 ID 数组；失败保留选择；顾问列表走自己的刷新函数；刷新失败与删除失败分开提示。
- `models_shared.py:CaseBatchDeleteInput`：非空、正整数、不重复、最多 200 条，与当前列表最大页容量一致。
- `legal/router.py:_delete_company_cases`：完整选择按 ID 加锁，整批数据范围及归档/合并状态预检，通过后才删除；一次提交，异常整批回滚，关联外键阻断返回 409。
- `_delete_case_owned_records`：复用原删除关联范围，补齐本批关联任务的附件文件收集；物理文件在事务成功后清理，仍被其他附件引用的文件不删；清理失败明确返回待处理数量，不伪报数据库删除失败。
- 审计：提交后写服务日志记录操作者和全部案件 ID。未新增数据库审计表；附件清理失败写异常日志，仍需人工处理，不宣称自动重试已实现。
- 角色能力差异仍为独立待核实项，本次未放宽或新增角色限制。归档/合并和既有外键限制仍保留。
- VibeHub 术语核对：已调用解析器核对 [原子性](https://vibe-hub.org/atomicity)，只发送脱敏短术语。这里指整批数据库删除全部成功或全部回滚，不将文件系统与数据库误称为同一事务。
- 聚焦验证：新增前端实际 handler 执行测试 5/5，加两份适配真实源码路径的旧删除/工具栏契约测试，合计 9/9。后端真实 HTTP + 独立内存 SQLite 测试 10/10，开启外键校验。
- 隔离与清理：唯一 `CODEX-case-batch-delete-*` 临时目录和内存数据库，仅操作测试自建记录；每项 tearDown 关闭数据库并清理临时目录。
- 构建：`npm.cmd run build` 通过（1.1.108，仅大块资源警告）；后端 `compileall`、`git diff --check` 通过；CodeGraph 同步完成。
- 静态检查：菜单审计通过，增加完整选择集接线断言；API 覆盖审计 822 处匹配。静态匹配数量不等于已测试 822 个业务功能。
- 页面验收/发布：尚未浏览器验收；无提交、无推送、无部署。

## 验证矩阵与边界
| 验证项 | 结果 |
|---|---|
| 两条选择一次提交，两条均删除，第三条保留 | HTTP + 数据库 + 文件通过 |
| 关联任务、任务通知、任务日志、案件和任务附件 | 删除与剩余数据断言通过 |
| 空、重复、负数、超过 200 条 ID | HTTP 422，数据及文件不变 |
| 第二条不存在或为非案件对象 | HTTP 404，整批不变 |
| 第二条已归档/已合并 | HTTP 409，整批不变 |
| 角色不符、无可见案件 | HTTP 403/404，整批不变 |
| 第二条故障，第一条已经 flush | HTTP 500，数据库回滚、文件不动 |
| 第二条被外键引用禁止删除 | HTTP 409，整批回滚 |
| 原单条 DELETE 接口 | 204，仍可删除单条 |
| 其他记录引用同一物理文件 | 文件保留 |
| 文件被锁无法清理 | 数据库删除成功，明确报告 cleanup_pending，不误报删除失败 |
| 弹窗确认前、失效选择、混合无权限选择 | 前端不发删除请求 |
| 删除失败/顾问列表刷新/刷新失败 | 选择与反馈状态通过实际 handler 测试 |

上述 HTTP 测试使用依赖覆盖注入测试身份，不等于真实登录/菜单中间件已完成验收。SQLite 验证回滚和外键，不证明 PostgreSQL 并发锁行为；同一时刻的并发修改仍待专门验证。既有费用、排期等删除语句保留，本轮未穷举全部历史关联及角色页面。不得将该条记为用户“已验收”或据此宣称全系统已对齐。

# Task 29：人事中心员工绩效管理本地实现与验收

日期：2026-09-05。范围为用户明确要求的独立绩效菜单、列表筛选、方案设置、查看、增删改、导出、权限和日志及本地构建。本轮未选择 Excel 问题行，未提交或部署。修改仅位于用户指定的 `.codex-worktrees/95-task29-hr-performance` 工作区，实际分支 `95-task29-hr-performance`；未切换 `dev`，未把工作树改动宣称为线上版本。

## 原始要求与旧站参考

原始差异：新系统仅有员工详情内的 commission 附属记录，需要独立的人事绩效管理页面。按员工、部门、时间筛选，兼容已有员工提成方案数据，保持人事页面风格。

已阅读既有源码证据 `docs/hr-local-parity-verification.md` 的“员工四个子页归档源码只读证据”和 `docs/旧系统前后端与新系统全量功能差异总表.md` 的绩效条目：旧 `HR/StaffController` 的 `PerformanceList`、`Performance`、`PerformanceView(staffName, caseNo)`；方案包含日期区间、基本工资和开庭/文书/案源/调查/品管五类比例及固定额。旧表格含新增、编辑、删除与分页。上述历史记录只用来支持字段兼容性，不作为本轮旧站页面或完整业务等价证明。

## 验证环境与已知限制

- CodeGraph：本工作树 `codegraph status` 返回 `Not initialized`。未用图谱结论代替功能验收；后续按相关文件和接口直接核对。
- 浏览器：已完整阅读 Browser skill，通过规定运行时选择 `iab` 返回 `Browser is not available: iab`。随后读取 `bootstrap-troubleshooting` 并执行一次浏览器发现，仅发现 Chrome extension；未替代指定内置浏览器，未创建或操作任何标签，保留标签数量为 0。
- `powershell -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1`：已先读确认没有部署/重启行为；执行因工作树缺少 `apps/api-server/.venv/Scripts/python.exe` 在构建前退出，不能记为完整通过。
- 系统 Python 可导入 FastAPI、SQLAlchemy。独立执行全局菜单审计在已有 `CaseCenterPage.tsx:3011` 表单日期 `.format` 守卫失败。另单独计算发现排除扩展菜单后既有节点/叶子实际为 282/236，与历史断言 277/231 存在漂移；未改旧基线以掩盖失败。客户端 API 审计报告已有 PDF 分页预览路径及 InvestigationCenterPage 两个 workspace 路径不匹配。这些文件不属于本任务修改范围，未删除或放宽既有守卫。
- 独立运行 `scripts/smoke-api.py` 因 `SMOKE_PASSWORD` 未配置在联网前退出，未产生数据。该全站脚本含历史 SMOKE 数据扫描清理及系统配置写回，本轮不补凭据在真实数据库运行；本任务的业务验证应使用隔离数据库。

## 已完成实现与检查

1. `App.tsx` 增加人事中心“绩效管理”菜单、独立懒加载页面及路由分支。`HrPerformancePage.tsx` 包含员工/部门/有效期查询、分页、新增/编辑、真实详情读取、确认删除与 CSV 下载；员工列表和查看弹窗均有真实员工详情关联入口。前端列表和导出使用同一已应用过滤条件。
2. `main.py` 提供 `GET/POST /hr/performance`、`GET/PATCH/DELETE /hr/performance/{performance_id}`、`GET /hr/performance/export`。沿用 `HrSubrecord(kind=commission)` 保持员工详情与独立页共享数据；补充方案名/备注及数值有效性校验，写动作写入员工工作流日志。列表/导出共用菜单权限和数据范围过滤；写动作复用员工附属记录维护权限。
3. 静态核对只读角色不会出现新增/设置/删除按钮，admin/manager 与后端既有维护角色一致；菜单授权、员工可见范围仍由服务端决定。前端方案名上限统一为 128，备注 2000；比例保留既有非负数原值，不擅自改变比例单位或按 100 倍展示。
4. `scripts/audit-menu-coverage.py` 增加 `audit_hr_performance()`，并将独立菜单列为扩展项以保留历史菜单基线。独立结构检查通过：`HR_PERFORMANCE_PAGE_CONTRACT_OK`。本页面 10 个前端 API 调用与服务端路由全部匹配：`HR_PERFORMANCE_CLIENT_API_OK: 10 calls`。本页面通过表单日期守卫检查。
5. `scripts/smoke-api.py` 新增独立绩效与原附属记录共享回读、CRUD、日期失败后数据不变、员工/部门/时间过滤、CSV、删除后 404 及日志断言。新建方案使用任务命名，`try/finally` 精确删除方案。此 HTTP 冒烟段本轮未连接真实数据库执行；不能将“覆盖已写”记为“接口已通过”。
6. 验收线程执行 `python -m compileall -q apps/api-server/app scripts/smoke-api.py scripts/audit-menu-coverage.py` 通过，`git diff --check` 通过。前端线程与主会话确认 `npm ci` 成功，`npm run build` 的 TypeScript 与 Vite 生产构建通过（5646 个模块）。
7. 后端线程执行 `python -m unittest hr_performance_management_test.py -v`（目录 `apps/api-server`），3/3 通过，耗时 16.416 秒。已审阅测试：使用 ASGITransport 调用真实 HTTP 路由、独立内存 SQLite、依赖覆盖的身份及菜单/数据范围权限 fixture；覆盖 CRUD/子表共享/案件方案兼容/CSV/日志、有效期交集/部门精确过滤/分页/部门范围/跨范围 404/只读写入 403/无菜单 403，以及无效非有限数值 422 与无部分写入。fixture 身份不是登录认证流程，不能宣称真实角色登录验收。每例结束关闭 HTTP 客户端、清空依赖覆盖并销毁内存数据库；CRUD/无效写入用例另断言方案计数归零。

## 当前证据状态

- 已完成：独立页面、接口、日志、兼容字段、验证脚本覆盖、历史参考读取、全量验证尝试及阻碍记录。
- 已验证：本页面结构与路由契约、3 项后端 HTTP 内存隔离测试、Python 编译、前端生产构建、差异格式检查。
- 仍未证明：旧站与本地新增页面的直接浏览器操作，真实角色登录后的按钮权限与数据闭环。无内置浏览器证据时不标记页面已验收。
- 数据清理：验收线程未启动 API 服务、未连接或写入业务数据库、未创建测试业务数据及附件，因此无数据清理对象。
- Git/部署：未执行 `git add`、`git commit` 或发布；版本号不递增。

术语核对：已读取 VibeHub skill，并仅以脱敏短词 `CRUD` 调用解析器，返回“增删改查” https://vibe-hub.org/crud 。此术语不替代用户原始需求。

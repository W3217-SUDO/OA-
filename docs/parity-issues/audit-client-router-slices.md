# [本地静态验证通过] 接口覆盖审计未识别分片路由注册

## 基本信息
- 发现日期：2026-09-12
- 来源：本地主动审计，运行 `scripts/audit-client-api-coverage.py`。
- 分类：审计工具误报，不是已确认的页面业务缺口。
- 前端对应：`tp/TaskCenterPage.tsx` 的“新建任务”调用 `POST /tasks`；以及客户、案件、财务等页面的真实 API 调用。

## 对比与定位
- 旧审计假设：主要路由写在 `main.py` 的 `@app` 装饰器，少量模块经 `app.include_router` 注册。
- 当前实现：`main.py` 导入 `app.areas.*.router`，按 `include_route_slice(app, router, start, stop)` 注册；`routing.py` 校验区间和覆盖。
- 复现：审计把 `POST /tasks`、`GET /records` 等大量已注册接口报告为不存在。
- 根因：审计未解析绝对模块导入和路由分片，不是相关页面缺少后端接口。
- 旧系统业务证据：不适用，此记录仅比较审计假设与新系统实际注册机制，不能用于证明新旧业务对齐。

## 整改与验证
- 计划：用 Python AST 读取实际导入别名、装饰器注册顺序和分片上下界，只收集被挂载的区间；保留原有路由工厂解析。
- 必须验证：多方法路由、装饰器倒序、未挂载区间不被计入、无效区间报错、真实项目覆盖结果。
- 实现：AST 按底部到顶部的装饰器执行顺序读取区域路由，并且只计入实际分片；通过显式导入追踪路由工厂的重导出，不执行应用启动。
- 同时修正可选链 `${detail?.id}` 被误当查询字符串，以及 `${page}.png` 动态文件后缀匹配；不将 `.jpg` 误匹配为 `.png`。
- `python -m unittest discover -s scripts -p test_audit_client_api_coverage.py -v`：8/8 通过。
- `python scripts/audit-client-api-coverage.py`：822 处可静态提取调用匹配注册路由，退出码 0。
- 局限：动态表达式、变量构造 URL、泛型调用及非 TSX 文件并未因此获得完整覆盖；方法/路径匹配不证明鉴权、数据或页面行为。
- 状态：审计工具已本地验证，尚未部署，不涉及数据库或业务数据修改。

# 财务结算管理待结算接口 503

## 问题来源与原文

- 来源：阿里云生产服务器日志，用户说明“问题别人已经处理了，但是待分配接口报错，用问题处理 skill 找到问题，参考旧的系统”。本问题按用户选择的第 1 个生产接口错误处理。
- 原文片段：待分配接口报错。
- 服务器入口：`https://huzhilawfirm.com/?page=finance-settlement-pending`。
- 失败请求：`GET /api/v1/finance/general-settlements/pending?customer=&case_no=&payer=&payment_method=&case_customer=&hearing_lawyer=&assistant=&customer_manager=&source_person=&page=1&page_size=10&finance_scope=firm`。
- 生产证据：2026-10-16 16:19:16，HTTP 503；API 慢日志为 `total_ms=30042.3`、`queries=6`、`sql_execute_ms=29943.8`。该请求在 30 秒计算预算内未完成，返回 503；不是前端参数缺失，也不是健康检查可以替代的功能验收。

## 子问题与证据链

| 原文片段 | 子问题 | 页面/接口证据 | 旧系统证据 | 新系统根因 | 修改与验收 |
|---|---|---|---|---|---|
| 待分配接口报错 | 待结算首屏请求超时并返回 503 | `finance-settlement-pending` 调用 `/finance/general-settlements/pending`，失败请求带 `finance_scope=firm` | 旧系统 `/5001007001/FAM/Settlement/PendingList` 为只读待结算列表，默认 10 条分页、全局合计、回款与分配明细；既有交接记录已逐项记录 10 项筛选和 14 列表头 | `_general_settlement_rows` 在未限定旧回款头和金额聚合范围时扫描全量历史来源，SQL 计划被旧回款头连接放大，首个业务查询超过 30 秒 | `74ad0143` 在唯一来源关系、财务中心和待提交状态条件下先构造候选回款头，并以候选头限制金额聚合；保留原分配、权限、状态、筛选和分页逻辑。需完成本地定向回归、构建和线上同参数验收 |

## 旧系统对照

旧系统只作为只读业务证据。项目交接记录确认路径 `/5001007001/FAM/Settlement/PendingList` 的业务契约为：10 项筛选、勾选列、14 个命名表头及末尾占位列、表头全局金额合计、回款方式/银行备注/回退审核备注上下文、默认 10 条及六档分页、行内查看/分配/记录入口和行内分配明细。修复只处理查询性能，不改变这些业务字段、状态和分配计算。

## 新系统定位

1. `apps/api-server/app/areas/finance/settlements.py::list_general_settlement_candidates` 调用 `_general_settlement_rows`，在返回前计算全局合计并切片分页。
2. `apps/api-server/app/core/finance.py::_general_settlement_rows` 负责回款、分配、案件、费用、结算申请和权限关联。
3. `apps/api-server/app/core/finance_centers.py::incoming_settlement_candidates` 沿旧回款来源唯一性和 `SettlementStatus == 5` 构造候选头，并按 `finance_scope` 限定中心。
4. `apps/api-server/app/core/incoming_legacy_amounts.py` 接收候选头范围后再计算旧回款金额聚合。

## 修改、测试和发布状态

- 修改提交：`74ad0143c902f7aff86af3485e30656c22b39c92`，说明为“fix(finance): bound pending settlement legacy amount query”。
- 发布提交：`efaa8f7378230fad165e5c2cc248bdf5d7931187`，生产运行包 `1.1.446`；生产 `current` 已指向该包。
- 本问题未创建业务测试数据，未写入或修改生产数据。
- 定向验证：后端 Python 编译通过；带 `finance_scope=firm` 的真实 ASGI 待结算请求返回 200，响应包含 `items`、`total`、`totals`、分页字段；前端类型检查通过，财务定向回归 63 项通过，生产构建通过，`git diff --check` 通过。
- 完整门禁：推送 hook 的 source 范围检查通过；hook 报告完整后端隔离回归 266 项仍待隔离环境补证，不能把它写成全量通过。
- 生产复核：运行包 `1.1.446`、源码提交 `efaa8f7378230fad165e5c2cc248bdf5d7931187`，`sunhold-oa-api.service` 和 `sunhold-oa-web.service` active，`/health` 返回 200；无认证直接请求目标接口返回 401，路由和认证层可达。浏览器现有标签已失效停在登录页，真实账号页面验收待登录后补证。
- 当前状态：性能修复已部署并完成接口层复核；页面业务验收仍待真实登录，不能仅凭 `/health` 或历史提交标记为完全验收。


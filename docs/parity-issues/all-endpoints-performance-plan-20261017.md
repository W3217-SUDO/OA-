# 全接口性能优化执行手册（给 Codex 逐步执行）

> 版本：2026-10-18 · 基线：线上 `1.1.447`（提交 `cdcc05d6`）+ 本地两个未上线提交（`0e6baed1` 案件详情按需加载、`44969663` 测试对齐）
> 工作分支：`perf/all-endpoints-20261017`，worktree：`/Users/taowei/Desktop/oa/.tmp/wt-perf`
> 本手册中所有数字都来自 2026-10-16～18 对生产 `oa-production`（47.93.166.123）的**只读**实测。

---

## 第 0 章 必须先读懂的四条铁律

1. **结果必须完全一致。** 任何优化后，同一用户、同一参数下，接口返回的 `items`（全部分页拼接）、`total`、`totals/summary`、排序顺序、每个字段的值，必须和优化前**逐字节相同**（JSON 规范化后）。导出文件逐单元格相同。不一致就是失败，不论快了多少。
2. **先建对比工具，再改任何一行业务代码。** 第 1 章的"等价性快照工具"是所有后续步骤的验收门槛。没有它，不允许开始第 3 章以后的任何改动。
3. **一步一提交。** 每个步骤独立一个提交，提交前必须跑完该步骤的"验收"小节。步骤之间不混改。
4. **只读访问生产。** 对生产数据库的一切操作都必须带 `default_transaction_read_only=on`。不允许在生产写任何业务数据。测试数据只能用 `CODEX-*` 前缀并在本地或测试环境执行，结束后精确清理。

另外遵守仓库 `AGENTS.md`：动代码前跑 `codegraph status/sync/explore`；按 `docs/skills/oa-fast-deploy/SKILL.md` 发布；版本号、`package.json`、`package-lock.json` 一致。

---

## 第 0.5 章 现状事实（作为改前基线，不需要再测）

### 运行环境
- 4 核 / 15 GiB；PostgreSQL 16.15；`shared_buffers=2GB`、`work_mem=4MB`；**没有 `pg_stat_statements`**。
- API：`uvicorn app.main:app --host 127.0.0.1 --port 8001`，**单进程**（`scripts/native_runtime.py:240` 没有 `--workers`）。单进程常驻内存约 5.8%（≈900 MB）。
- 数据量：`business_records` 178,927 行/351 MB（`finance` 81,485 行、JSON 103 MB；`finance_application` 25,695；`customer` 12,698；`case` 6,459；`invoice` 3,376）；`incoming_payments` 3,203；`users` 168；`file_attachments` 161,869。
- `business_records` 索引只有：`module`、`status`、`owner`、`title`、`serial_no`（唯一）。**没有任何复合索引，没有 `updated_at` 索引。**

### 最关键的一条结论
单进程是"所有接口都慢"的首要原因。证据：
- `/auth/me` 只有 3 条 SQL，日志平均 3.0 秒；`/agent/skills/catalog` SQL 合计 2 ms，接口 2.5 秒。这些接口本身不干活，是在**排队**。
- 进程内直接计时（绕过 HTTP、绕过排队）：`internal-fees` 3.3 s（SQL 1.4 s + Python 1.9 s）、`fees/query` 7.9 s（SQL 2.0 s + Python 5.9 s）。日志里这两个接口平均 20–26 s、最大 44 s。差值全部是排队。

### 已排除的方向（不要做）
- **不要改 `app/core/json_relation_query.py` 的 `json_scalar_overlap`。** 实测绑定参数下旧写法约 340 ms、新写法约 395 ms，旧写法不是瓶颈。
- **不要把 `business_records.data` 从 `JSON` 改成 `JSONB`。** 需要整表重写，且代码有意保留逐值文本口径（`dashboard_finance_read_model_migration.py:167`）。

### 近 7 天慢请求（`slow_api` 日志，2,526 条）
| 接口 | 次数 | 平均 | 最大 | 平均 SQL 条数 |
|---|---:|---:|---:|---:|
| `GET /dashboard` | 739 | 4.3 s | 14.4 s | 22 |
| `POST /personal-agent/messages` | 120 | 24.9 s | 150 s | 34 |
| `GET /cases/{id}/relations` | 267 | 5.0 s | 12.6 s | 43 |
| `GET /finance/general-settlements/export` | 40 | 20.6 s | 138 s | 115 |
| `GET /finance/internal-fees` | 33 | 20.1 s | 44 s | 9 |
| `GET /cases/search` | 133 | 4.3 s | 15.9 s | 11 |
| `GET /cases/{id}/documents` | 125 | 3.7 s | 7.3 s | 13 |
| `GET /finance/invoices/export` | 5 | 92 s | 124 s | 389 |
| `GET /legacy-ls-history/current-records/{id}` | 122 | 3.6 s | 6.6 s | 14（**全部 503**） |
| `GET /finance/general-settlements/pending` | 49 | 8.0 s | 30 s | 22 |
| `GET /cases/{id}/logs` | 142 | 2.4 s | 5.0 s | 9 |
| `GET /notifications` | 87 | 3.4 s | 6.0 s | 5 |
| `GET /customers` | 73 | 3.3 s | 8.9 s | 12 |
| `GET /finance/payment-workflow/list` | 21 | 9.6 s | 14.5 s | **9,380** |
| `GET /tasks/unread-messages` | 59 | 3.0 s | 4.5 s | 3 |
| `GET /auth/me` | 55 | 3.0 s | 5.6 s | 3 |

`1.1.447` 上线后 9 小时（周六低峰）仅 8 条慢请求：`case-fees/refunds` 12 s/165 条 SQL、`fees/query` 8.4 s、`incoming-payments` 5.5 s。**低峰数据不能代表工作日**，第 9 章要求工作日复测。

---

## 第 1 章 P0：等价性快照工具（第一步，必须先做）

**目的**：证明"改前改后结果完全一样"。后面每一个步骤都用它验收。

### 步骤 1.1 新建工具脚本 `apps/api-server/scripts/perf/snapshot_endpoints.py`

要求：
1. 用**独立 engine** 连接数据库，`connect_args={"server_settings": {"default_transaction_read_only": "on", "statement_timeout": "300000"}}`。工具绝不能写库。
2. 直接 import 并调用**路由处理函数**（不经 HTTP、不经缓存包装）。注意：`install_finance_query_cache` 会把 `route.dependant.call` 替换为缓存包装，所以要调用模块里的原始函数（如 `app.areas.finance.router.query_finance_fees`），并**显式传入每一个参数**（FastAPI 的 `Query(...)` 默认值是 `FieldInfo` 对象，不能依赖默认值）。
3. 身份 `identity` 必须用真实逻辑构造：从 `users` 表读出用户，调用 `app.core.permissions._user_permission_payload(user, db)`，再按 `app/security.py:232-272` 的 `current_identity` 组装字典。`_page_menu_capability` 按目标路径计算（参考 `app/security.py:224` 的 `_page_menu_authorized`，可构造一个只含 `url.path` 的假 `Request`）。
4. **抓全量**：对分页接口，使用 `page_size=200` 从第 1 页循环到 `ceil(total/200)` 页，把所有 `items` 按返回顺序拼接；同时记录 `total`、`totals`/`summary`/`unread` 等所有非 `items` 字段。
5. **规范化**输出：`json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)`。浮点数原样保留（不四舍五入）。集合类型（若有）排序后输出。
6. 每个用例输出一个文件 `<out>/<case_id>.json`，并输出 `<out>/_timing.json` 记录每个用例的 wall/SQL/条数（用 `before/after_cursor_execute` 事件统计，参考第 0.5 章计时方法，已在 `.tmp/perf-probe/profile.py` 验证可用）。
7. 导出类接口：返回 `Response`/`StreamingResponse` 时，读出字节；`xlsx` 用 openpyxl 读出所有工作表所有单元格值（`ws.iter_rows(values_only=True)`）转成 JSON 列表；`csv` 按行解析；`docx` 用 python-docx 读段落和表格文本。**比较的是内容，不是字节**（xlsx 内含时间戳）。

### 步骤 1.2 新建用例矩阵 `apps/api-server/scripts/perf/snapshot_cases.json`

每个用例：`{"id", "endpoint": "模块.函数名", "params": {...}, "user": "<用户名>"}`。

**用户**：至少三类，从生产 `users` 只读挑选并记录用户名（不要写进提交信息以外的地方暴露密码，用户名可以写）：
- `admin`；
- 一个拥有财务菜单、`data_scope=全所数据` 的财务角色用户；
- 一个 `data_scope` 非"全所数据"的普通律师/助理用户。

**参数**：每个接口至少覆盖：
- 无筛选（默认参数）；
- 每个筛选参数各单独一个用例（取生产里真实存在的值，例如一个真实案号、一个真实客户名、一个日期区间）；
- 两个以上筛选组合一个用例；
- 一个"不可能命中"的值（验证空结果形状一致）；
- 每个 `scope` 枚举值各一个用例；
- 排序/页码边界：`page` 超过最后一页。

接口清单 = 第 5、6、7 章列出的全部接口。

### 步骤 1.3 新建比较工具 `apps/api-server/scripts/perf/compare_snapshots.py`

- 输入两个目录（改前/改后），逐文件比较规范化 JSON；任何差异打印第一个差异路径（如 `items[37].data.paid_amount: 1200.0 != 1200`）并以非 0 退出码结束。
- **不允许**设置"忽略字段"列表，除非该字段在改前两次运行之间本身就变化（如生成时间）。如有此类字段，必须在本文件第 10 章"已知易变字段"登记理由。

### 步骤 1.4 在生产上跑基线

1. 把**线上运行包**的代码目录（`readlink -f /opt/sunhold-oa/runtime/enterprise/current` 下的 `api/`）作为改前代码；工具脚本和用例上传到生产 `/tmp/oa-perf/`。
2. 运行环境变量来自 `/opt/sunhold-oa/private/production-native.env`（只 `source`，不打印）；Python 用 systemd 里的 `OA_NATIVE_PYTHON`；`PYTHONPATH=<运行包>/api`。
3. 低峰时段运行（避免影响业务），输出到 `/tmp/oa-perf/baseline/`，拉回本地 `.tmp/perf-probe/baseline/`（`.tmp` 已被 git 忽略），**不要提交快照数据**（含业务数据）。
4. 在生产上用同一份改前代码**连续跑两次**，比较两次结果：必须一致；不一致的字段登记到第 10 章。

### 步骤 1.5 候选代码的对比方法（以后每一步都这样做）

1. 本地改完代码 → `rsync` 候选 `apps/api-server/` 到生产 `/tmp/oa-perf/candidate/api/`（只读运行，不替换线上包）。
2. 同一时间段先后运行改前和改后，输出 `/tmp/oa-perf/before/`、`/tmp/oa-perf/after/`。
3. 本地运行 `compare_snapshots.py before after`，必须 0 差异。
4. `_timing.json` 对比填入第 10 章的进度表。
5. 运行完毕删除生产 `/tmp/oa-perf/`。

**验收**：工具能在生产跑通全部用例；改前代码两次运行 0 差异；提交 `test(perf): add read-only endpoint equivalence snapshot tool`。

---

## 第 2 章 P1：线上真实报错（全部有确切位置）

每个修复都要：先在本地或生产只读复现 → 修 → 单测 → 快照工具对比（不影响其它结果）。

### 步骤 2.1 `/legacy-ls-history/current-records/{id}` 100% 返回 503

- **根因（已在生产确认）**：生产库中**不存在表 `legacy_ls_cases`**（`to_regclass('public.legacy_ls_cases')` 为空）。`app/legacy_ls_history_router.py:213-233` 的查询抛 `UndefinedTable`，被 `except SQLAlchemyError` 捕获后统一返回 503。前端每打开一个案件就请求一次，所以 122 次全部失败，且每次耗时 3.6 秒（排队）。
- **改法**：
  1. 在 `app/legacy_ls_history_router.py` 增加一个"承载表是否存在"的检查函数，对每个进程只查一次并缓存结果（PostgreSQL：`SELECT to_regclass('public.legacy_ls_cases') IS NOT NULL`；SQLite：`sqlite_master`）。
  2. 表不存在时，`current-records` 返回 **404**，`detail` 保持与"未找到唯一映射"相同的文案：`"No unique LS history is mapped to this current case"`。这与表存在但没有映射时的行为完全一致，前端已有对应处理。
  3. 同文件其它路由（`:130`、`:179`、`:206`、`:229`、`:249` 附近）一并改为：表不存在时返回与"无数据"一致的 404，表存在时的 SQL 错误仍返回 503（保持原有语义）。
  4. **不要**建这张表，也不要迁移数据（那是另一项业务迁移，不属于本次）。
- **验收**：前端打开案件详情时该请求返回 404 且耗时 < 50 ms；前端历史卡片显示与"无历史"一致；单测覆盖"表不存在 → 404""表存在无映射 → 404""表存在有映射 → 200"。

### 步骤 2.2 `operator does not exist: json ~~ text`

- **位置**：`app/core/permissions.py:628-630`（`_case_mine_scope_condition`）：
  ```python
  data["case_team_usernames"].contains(exact_username_token),
  data["handling_lawyer_usernames"].contains(exact_username_token),
  data["legacy_participants"].contains(f'"staff_name":"{username}"'),
  ```
  `data` 有两种来源：`record_json_text_projection` 返回的 `Text` 列（安全），或 `app/core/dashboard_scope.py:141` 传入的 `projected_data`（来自 `dashboard_finance_relations` 等读取模型的 **JSON 类型列**）。后者在 PostgreSQL 上编译成 `json_col LIKE ...`，直接报错。
- **生产证据**：2026-10-16 02:28–02:38 共 8 次，触发请求 `GET /cases/279523/relations?include=fees` 返回 500。
- **改法**：在这三处统一先转成文本：用 `sqlalchemy.cast(expr, Text).contains(...)`。对 `record_json_text_projection` 已是 `Text` 的列，`cast` 是幂等的，结果不变。同函数中 `func.coalesce(data[...], "")` 的几处也做同样处理（`coalesce(json, '')` 同样会类型冲突）。
- **全局排查**：用 `rg -n "\.contains\(" app` 列出全部调用，逐个确认左侧是 `Text/String` 或已经 `.as_string()` / `.cast(String)`。目前已确认安全的写法见 `permissions.py:591-592`、`705-709`、`case_list_tasks.py:16,24`、`contract_delete.py:32-40`。
- **验收**：新增单测，用 `projected_data` 为 JSON 列的情况在 PostgreSQL 方言编译 SQL，断言不含 `json ... LIKE`；快照用例 `/dashboard` 与 `/cases/{id}/relations?include=fees` 结果与改前一致（改前若报错，则改后返回 200 且数据与 admin 视角下同一记录的关联一致）。

### 步骤 2.3 `the number of query arguments cannot exceed 32767`

- **位置**：`app/core/finance.py:1866-1869`（`_refund_case_fee_authorized_ids`）：
  ```python
  conditions.append(BusinessRecord.data["case_id"].as_integer().in_(case_ids))
  conditions.append(BusinessRecord.data["case_no"].as_string().in_(case_nos))
  ```
  `case_ids/case_nos` 是用户可见的全部案件，数量可超过 32,767，asyncpg 直接报错。生产证据：`GET /finance/case-fees/refunds/export` 报错 5 次。
- **改法**：改用仓库已有的 `app.core.json_relation_query.scalar_in_values(column, values)`，它把整个集合作为**一个** JSON 参数传入（已在 `finance.py:1494-1495` 等处使用）。语义等价（同样是 `IN`）。
- **全局排查**：`rg -n "\.in_\(" app` 中，参数来自"全部可见记录/全部关联 ID"而非"当前页"的，一律改为 `scalar_in_values`。已知还有：`app/areas/crm/router.py:1765`（`WorkflowEvent.record_id.in_(candidate_ids)`）、`app/areas/tp/router.py:627`、`app/core/formatters.py:281,283`。
- **验收**：单测构造 40,000 个 ID 不报错；快照用例结果一致。

### 步骤 2.4 `float() argument must be ... NoneType`（`/finance/summary`）

- **位置**：生产堆栈指向 `app/core/finance_readmodel.py`（旧版本第 50 行，当前 PostgreSQL 分支已是 `float(amount or 0)`，第 62 行）。当前仍存在的风险点：`finance_readmodel.py:76` 的 `amounts[fee_type] += float(amount)`（非 PostgreSQL 分支，`kind` 不是 null 但 `amount` 可能为 None）。
- **改法**：第 76 行改为与第 62 行同一口径：`float(amount or 0)`。PostgreSQL 分支不改。
- **验收**：生产日志在 `1.1.447` 上线后无此报错（已确认）；补一个 SQLite 单测：`amount` 为 JSON `null` 以外的空值时不抛错。

### 步骤 2.5 `'coroutine' object is not iterable`（`/personal-agent/memory`）

- **位置**：生产堆栈是旧版本 `1.1.401` 的 `app/areas/personal_agent/router.py:211`。当前代码第 212 行已经是 `for state in await conversations.read_conversation_states(...)`，**已修复**。
- **动作**：只做核对，不改代码。用 `rg -n "for .* in [a-zA-Z_.]+\(" app/areas/personal_agent` 检查同目录是否还有对 `async def` 函数未 `await` 的迭代；有则修。

**本章验收**：本章所有修复合成一个发布批次（可以先于其它章节单独发布）。发布后 24 小时 `journalctl -u sunhold-oa-api` 中上述五类报错为 0。

---

## 第 3 章 P2：API 多进程 + 后台任务只在一个进程运行（收益最大）

> 这是解决"所有接口都慢"的关键。**3.1～3.4 必须在同一个版本里一起上线**，否则会重复发送通知。

### 步骤 3.1 盘点后台任务（先读代码，确认后再改）

`app/core/lifecycle.py:237-241` 在每个进程启动时会创建：

| 任务 | 定义位置 | 周期 | 是否写库/对外发送 | 多进程策略 |
|---|---|---|---|---|
| `_business_rule_loop` | `app/core/system.py`（`_run_business_rules_once`，含"附件暂存协调"等规则，会 `commit`） | 60 s | 写库 | **只允许一个进程** |
| `_dingtalk_notification_loop` | `app/core/tasks.py` | 10 s | 发钉钉 | **只允许一个进程** |
| `notification_scheduler_loop` | `app/core/notification_scheduler.py` | 30 s | 生成通知、发短信 | **只允许一个进程** |
| `_automatic_cache_cleanup_loop` | `app/core/system.py` | `max(system_cache_ttl_seconds, 60)` | 只清**本进程**内存缓存 | **每个进程都要跑** |
| `case_agent_runtime.start()` | `app/core/constants.py` 中 `create_case_agent_runtime(...)` 创建 | — | 待确认 | 读实现后决定（见 3.3） |

必须读懂：`notification_delivery.dispatch_one`、`mark_expired_claims_unknown` 和钉钉发送的"认领"机制。即便有认领去重，也**仍然**只让一个进程跑，作为双保险。

### 步骤 3.2 新增 `app/core/background_leader.py`

实现"后台任务主进程选举"：

1. 用一个**专用、长期持有**的数据库连接（`engine.connect()`，不放回连接池）执行 `SELECT pg_try_advisory_lock(:key)`（**会话级**锁，不是 `xact` 锁）。`key` 用一个固定的 64 位常量，例如 `7_310_412_018_001`，在文件顶部注释说明用途，并全仓库搜索确认不与现有锁 ID 冲突（现有：`startup_migrations.py` 的 `_STARTUP_LOCK_ID`，`customer_identity.py:37`，`imported_incoming_payments.py:113` 的 `hashtext(...)`）。
2. 拿到锁的进程：启动"仅主进程"任务（`_business_rule_loop`、`_dingtalk_notification_loop`、`notification_scheduler_loop`，以及 3.3 判定需要的 `case_agent_runtime` 后台部分）。
3. 没拿到锁的进程：每 15 秒重试一次 `pg_try_advisory_lock`；一旦拿到就启动上述任务（原主进程退出或崩溃时，PostgreSQL 会自动释放会话锁，实现接管）。
4. 主进程每 30 秒对锁连接执行 `SELECT 1` 做心跳；连接断开时，**立即取消**本进程的"仅主进程"任务，回到重试状态（防止"自以为是主"）。
5. 关闭时（`lifespan` 的 `finally`）：先取消任务并等待结束，再执行 `pg_advisory_unlock` 并关闭连接。
6. SQLite（本地/测试）：直接认为自己是主进程，行为与改前一致。
7. 增加一个环境变量 `OA_BACKGROUND_TASKS`：`auto`（默认，按上面选举）/`off`（本进程不跑后台任务，用于运维排障）。

### 步骤 3.3 `case_agent_runtime`

读 `create_case_agent_runtime` 的实现（`rg -n "def create_case_agent_runtime" app`）：
- 如果 `start()` 只初始化客户端/连接池、没有轮询或常驻后台任务 → 每个进程都调用，保持现状。
- 如果 `start()` 会启动轮询器/调度器/消费者 → 只在主进程启动，其他进程只初始化客户端。
- 把结论写进本文件第 10 章。

### 步骤 3.4 修改 `app/core/lifecycle.py:237-262`

- `_automatic_cache_cleanup_loop` 保持每个进程都启动。
- 其余三个循环改为交给 `background_leader` 管理。
- `finally` 中的取消顺序保持：先停后台任务，再 `case_agent_runtime.stop()`，最后 `close_dashboard_metrics_cache()`。
- `migrate_startup_schema` 与 `initialize_startup_data` 已经用 `pg_advisory_xact_lock` 串行（`startup_migrations.py:131-137`），多个 worker 同时启动是安全的。**确认** `initialize_startup_data` 也处在同一把锁内；若不在，给它加同样的锁。

### 步骤 3.5 多进程启动参数

- 修改 `scripts/native_runtime.py:240` 的 uvicorn 参数：增加 `--workers`，值取环境变量 `OA_NATIVE_API_WORKERS`，默认 `3`（4 核留 1 核给 PostgreSQL/Nginx）；校验为 1–8 的整数，非法值启动失败并给出中文报错。
- 生产 systemd 的 `ExecStart` 指向 `tools/<版本>/native_runtime.py`，**工具目录也是按版本封存的**。按发布 skill 生成新的工具版本，不要修改旧工具目录。
- 内存估算：3 × ~900 MB ≈ 2.7 GB，可用内存 11 GiB，充足。

### 步骤 3.6 进程内状态审计（多进程后会不一致）

`rg -n "lru_cache|^_[A-Z_]+ *[:=] *(\{|dict\(|\[)|asyncio.Lock\(\)|global " app` 找出全部进程级缓存/全局变量，逐个判断：
- 只读缓存（如费用类型目录）：可接受，但修改时只清当前进程。必须改为：修改操作后写入一个"缓存版本号"（Redis 已在用，`dashboard_metrics_redis`），各进程读取时比较版本号，不一致就丢弃本地缓存。重点：`_clear_all_system_parameter_cache`（`app/core/system.py:577`）。
- 锁（`asyncio.Lock`）：只在进程内有效。若用于防止并发写同一业务对象，必须改为数据库行锁或咨询锁。
- 连接注册表（WebSocket/SSE）：若存在，确认消息投递不依赖"同一进程"。

**本章验收**：
1. 生产 `ps` 看到 1 个 master + 3 个 worker；`SELECT pid FROM pg_locks WHERE locktype='advisory' AND objid=<key 低32位>` 恰好 1 行。
2. 连续 24 小时：钉钉、短信、站内通知**没有重复**（查投递表按业务键分组 `count>1` 为 0）。
3. `kill` 主进程的 worker 后 15 秒内另一个 worker 接管（日志可见）。
4. 并发压测：用 10 个并发请求打 `/finance/fees/query`，同时测 `/auth/me` 的 p95 必须 < 300 ms（改前约 3 s）。
5. 快照工具全量对比 0 差异（多进程不应改变任何结果）。

---

## 第 4 章 P3：复合索引（版本化启动迁移）

### 步骤 4.1 新增迁移版本

- 文件：`app/core/startup_migrations.py`。
- 新增常量 `BUSINESS_RECORD_QUERY_INDEX_REVISION = "business_record_query_indexes_v1"`，新增函数 `_apply_business_record_query_indexes(connection, _upgrade_schema)`，写法完全参照已有的 `_apply_legacy_settlement_indexes`（第 58-81 行）：非 PostgreSQL 直接 `return`，每条 `CREATE INDEX IF NOT EXISTS`。
- 加到 `revisions` 元组（第 106-114 行）**末尾**。
- **不要**用 `index=True` 改 model：`Base.metadata.create_all` 只在一次性的 `startup_schema_bootstrap_v1` 中执行，已初始化的库不会补建。

### 步骤 4.2 索引清单（每一条都要在 4.3 里用 EXPLAIN 证明被使用，未被使用的删掉不建）

```sql
CREATE INDEX IF NOT EXISTS ix_br_module_updated   ON business_records (module, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_br_module_status_updated ON business_records (module, status, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_br_module_owner_updated  ON business_records (module, owner, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_br_module_created   ON business_records (module, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_br_fee_type ON business_records (module, (data->>'fee_type'));
CREATE INDEX IF NOT EXISTS ix_br_case_no  ON business_records (module, (data->>'case_no'));
CREATE INDEX IF NOT EXISTS ix_br_case_id  ON business_records (module, (data->>'case_id'));
CREATE INDEX IF NOT EXISTS ix_br_contract_no ON business_records (module, (data->>'contract_no'));
CREATE INDEX IF NOT EXISTS ix_ft_record_type ON finance_transactions (finance_record_id, transaction_type);
CREATE INDEX IF NOT EXISTS ix_ip_received   ON incoming_payments (received_date DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_ip_status_received ON incoming_payments (status, received_date DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_notifications_recipient_unread ON notifications (recipient, recipient_deleted, is_read, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_workflow_events_record_action ON workflow_events (record_id, action, created_at DESC);
```

说明：
- `data->>'x'` 必须和代码编译出的表达式**完全一致**，查询才能用上索引。SQLAlchemy 的 `BusinessRecord.data["fee_type"].as_string()` 编译为 `(business_records.data ->> 'fee_type')`；`.as_integer()` 编译为 `CAST((data ->> 'case_id') AS INTEGER)`，这种情况索引要写成 `((CAST(data->>'case_id' AS INTEGER)))`。**以 4.3 的 EXPLAIN 为准调整。**
- 表名/列名以生产 `\d` 为准（`workflow_events`、`notifications` 先确认真实表名）。

### 步骤 4.3 生产只读证明

在生产只读事务里**不能**建索引。做法：
1. 在本地或测试库（导入生产结构 + 足量数据）执行迁移，跑 `EXPLAIN (ANALYZE, BUFFERS)` 证明计划从 `Bitmap Heap Scan + Sort (external merge)` 变为 `Index Scan`。
2. 对照生产已有的改前计划（第 0.5 章：`internal-fees` 主查询 472 ms、排序落盘 6–13 MB；全量 fees 104 ms、排序落盘 24–35 MB）。
3. 每一条索引写一行"被哪个查询使用"，填入第 10 章。

### 步骤 4.4 上线注意

- 迁移在启动事务内执行（`engine.begin()`），不能 `CONCURRENTLY`；建索引期间会阻塞对应表的写入。`business_records` 351 MB，预计数十秒。**发布必须在低峰执行**，并在发布回执里记录迁移耗时。
- 上线一周后查 `pg_stat_user_indexes.idx_scan`，为 0 的索引在下一个版本用新迁移版本删除。

**本章验收**：EXPLAIN 前后对比；快照全量 0 差异（索引不改变结果，但排序键必须保持 `updated_at DESC, id DESC`，确认没有因为索引改变平局顺序）。

---

## 第 5 章 P4：查询缓存（让缓存真正生效）

### 步骤 5.1 缓存键里的集合排序

- **位置**：`app/core/query_cache.py` 的 `_digest`（第 20-22 行）用 `jsonable_encoder` 编码身份。`app/core/dashboard_scope.py` 构造的 `scoped_identity` 含 `_dashboard_case_ids`、`_dashboard_fee_ids`、`_dashboard_record_ids` 等 **Python set**，`jsonable_encoder` 按迭代顺序转成列表，大集合在不同进程间顺序不稳定 → 键不同 → 永远不命中。多进程上线后问题更严重。
- **改法**：在 `_digest` 编码前递归把 `set/frozenset` 转为 `sorted(list)`（元素类型混合时按 `(type名, str值)` 排序）。只影响缓存键，不影响返回内容。
- **验收**：单测：同一身份，set 元素插入顺序不同，`_digest` 相同。

### 步骤 5.2 失效判定从"整库快照"改为"按表版本号"

- **现状**：`app/core/query_cache_flow.py:18-25` 的 `visible_snapshot` 用 `pg_current_snapshot()`。全库任意提交都会改变它；后台循环每 10–60 秒提交一次，所以缓存几乎永不命中，还会在单飞锁上等待并返回 503（7 天 147 次）。
- **已有更好的机制**：控制台用 `app/core/dashboard_revision.py` 的 `dashboard_snapshot`（按依赖表触发器累加 `dashboard_change_revisions`），只有依赖表变化才失效。
- **改法**：
  1. 读 `dashboard_revision.py` 的 `DEPENDENCY_TABLES`，确认已覆盖财务查询依赖的表：`business_records`、`incoming_payments`、`finance_transactions`、`file_attachments`、`users`、`system_parameters`、`role_permissions`、`contract_objects`、`legacy_finance_*`（以各财务查询实际 `select` 的表为准，逐个列出）。缺的表按该文件已有方式（新迁移版本）补触发器。
  2. `app/areas/finance/query_cache_routes.py` 的 `_wrap_query` 调用 `cached_query(...)` 时传入 `snapshot_reader=dashboard_snapshot`（`cached_query` 已支持该参数，见 `query_cache.py:31`）。
  3. **注意**：`business_records` 的任何写入都会使全部财务缓存失效（因为是同一张表）。这是正确的，不要尝试做更细的按模块失效。
- **验收**：
  - 同参数连续请求 10 次：第 1 次计算，第 2–10 次命中（日志计数）。
  - 写入一条 `CODEX-*` 测试费用后立即请求：必须重新计算，且结果包含新数据；测试完精确删除并回查为 0。
  - 后台循环写 `notifications` 时，财务缓存**不**失效（`notifications` 不在财务依赖表里）。
  - 快照工具对比 0 差异。

---

## 第 6 章 P5：财务接口（逐个改，逐个验收）

### 6.0 统一改造模式（所有财务列表都按这个做，必须保证结果一致）

Codex 在 `1.1.447`（提交 `9cc5ceee`）已经对 `fees/query` 用过"轻量筛选 + 当前页回读"的模式，**以它为模板**。规则如下，务必逐条遵守：

**规则 A：哪些筛选能下推到 SQL**
只有满足下列全部条件的筛选才允许下推：
1. 筛选目标是**单一来源**的存储值（一个列或一个 JSON 键），没有 `a or b or c` 的回退取值；
2. 比较方式在 SQL 与 Python 中语义一致：
   - 等值：Python `==` ↔ SQL `=`，注意 Python 端如果先 `str()`/`strip()`，SQL 端也要同样 `trim(...)`；
   - 包含：Python `needle.strip().casefold() in str(value or "").casefold()` ↔ SQL **不能直接等价**（`casefold` 与 PostgreSQL `lower/ILIKE` 对 `ß`、`ﬁ` 等少数字符不同）。**做法：SQL 端用 `ILIKE '%' || :needle || '%'` 只做预筛，Python 端保留原 `contains` 再判一遍。** 预筛对中文、数字、ASCII 是超集，只要 Python 复判，结果就与原来一致；
   - 日期区间：只有当 Python 比较的日期就是该列本身时才能下推（例如 `paid_date` 是"最近一笔付款日期或 JSON 回退"，**不能**下推）。
3. 下推后**保留** Python 端的原判断（双重过滤，结果不变，只是行数变少）。

**规则 B：派生字段筛选**（付款状态、开票状态、已付金额、退款金额、生命周期状态、回退取值的案号/律师/助理等）
- 不下推。顺序改为：SQL 预筛 → 只对预筛后的行计算派生字段 → 按派生字段过滤。
- 派生字段的计算函数一律**调用原函数**（`_finance_fee_payment_status`、`fee_paid_amount`、`fee_refund_progress`、`_case_commission_lifecycle_statuses`、`_case_fee_display_type`、`_case_party_values` 等），不允许重写同等逻辑。

**规则 C：分页与汇总**
- 请求**没有**派生字段筛选时：SQL 层用同样的排序键（通常 `updated_at DESC, id DESC`）做 `COUNT(*)` + `OFFSET/LIMIT` 拿当前页 ID，再按 ID 回读完整行并计算派生字段。
- 请求**有**派生字段筛选时：对预筛集合计算派生字段 → 过滤 → Python 排序 → 切片。
- `totals/summary`：若原代码是对"过滤后的全部行"求和，改后必须仍是对同一集合求和。纯存储列的合计改用 SQL `SUM`；含派生值的合计在轻量投影上计算（只取需要的列，不构建完整 ORM 对象）。
- `round(..., 2)` 的位置、`float` 转换次序必须与原代码一致（浮点求和顺序不同会差 0.01，快照会抓到）。为此：先按原顺序得到行列表，再求和。

**规则 D：人员显示名、权限字段裁剪**
- `apply_finance_person_displays`、`_record_dict(item, allowed_fields)` 只对**当前页**调用（原来对全量调用，返回的只有当前页，结果相同）。

**规则 E：N+1**
- 任何 `for row in rows: await db...` 改为循环前一次批量查询（`scalar_in_values` 传 ID 集合），循环里查字典。
- 权限判断（`_ensure_record_visible` 等）批量化时，**无权限的行为必须保持一致**：原来逐条 404 的，批量后对同一行仍返回同一错误。

### 步骤 6.1 `GET /finance/payment-workflow/list`（9,380 条 SQL → 目标 < 20 条）

- 位置：`app/areas/finance/payment_workflow.py`（原 `:33-40` 循环内逐条 `await _ensure_record_visible(int(package_id), identity, db)`；`9cc5ceee` 已部分改为按付款包 ID 批量读取，**先确认剩余的 N+1**）。
- 做法：用规则 E。先确认生产上 `1.1.447` 的实际 SQL 条数（快照工具 `_timing.json`），若仍 > 20 继续定位。
- 验收：SQL 条数 < 20；快照 0 差异；无权限付款包的处理与原来一致（单测）。

### 步骤 6.2 `GET /finance/internal-fees`

- 位置：`app/areas/finance/router.py` `list_internal_fees`（约 `:808`）→ `app/core/finance.py` `_internal_fee_rows`（约 `:2293`）→ `app/core/internal_finance_query.py` 的 `filter_internal_rows`、`internal_page`。
- 现状：一次读出 48,762 条内部费用（`data->>'fee_type' = '内部费用'`），全部构建字典后在 Python 过滤 13 个条件，`internal_page` 切片并对全量算合计。
- 做法：规则 A–D。可下推：`scope` 已下推部分、`legacy_kind`、`status`；`payee`/`customer` 等若为单一存储字段可用 ILIKE 预筛；`case_no`、`handling_lawyer`、`assistant` 等存在"费用字段 or 案件字段"回退，**不下推**。
- 目标：管理员 3.3 s → < 1 s。

### 步骤 6.3 `GET /finance/fees/query`

- 位置：`router.py` `query_finance_fees`（约 `:668`）→ `_fee_query_rows` → `_invoice_case_fee_rows`（约 `:1329`）。
- `1.1.447` 已改为"轻量汇总筛选 + 当前页回读"。剩余：仍在每次请求读取全部发票、全部退款、全部回款分配做派生计算。
- 做法：派生计算所需的发票/退款/回款，只读取与**预筛后费用**相关的记录（用 `scalar_in_values` / `json_scalar_overlap` 按费用 ID 与案号过滤，函数参数 `filter_related=True` 路径已存在）。注意：`unambiguous_case_nos` 的判定依赖"全库该案号的费用数"，**不能**只用预筛集合计算（`finance.py` 注释"单条可见费用不能证明全库中该案只有一笔费用"），保持调用 `unambiguous_fee_case_nos`。
- 目标：7.9 s → < 1.5 s。

### 步骤 6.4 `GET /finance/case-fees/refunds`（12 s、165 条 SQL）

- 位置：`router.py` 约 `:460` → `finance.py` `_refund_case_fee_rows`。
- 现状：先调用 `_fee_query_rows` 得到全量，再 `select(BusinessRecord).where(id.in_(fee_ids))` 把同一批费用重新读一遍。
- 做法：去掉二次读取，复用第一次的结果；`_refund_case_fee_authorized_ids` 已在 2.3 改为单参数。确认 165 条 SQL 的来源（快照工具逐条打印），消除循环内查询。

### 步骤 6.5 `GET /finance/incoming-payments`（5.5 s）

- 位置：`app/areas/finance/incoming_query.py`（`1.1.447` 已拆为汇总扫描 + 当前页明细）。
- 剩余：确认汇总扫描是否仍读取 `allocations` 大字段；若是，改为只读汇总需要的列，`allocations` 只对当前页读取。

### 步骤 6.6 `GET /finance/general-settlements/pending`、`GET /finance/settlements/pending`

- 位置：`finance.py` `_general_settlement_rows`（约 `:2576`）、`app/areas/finance/settlements.py`、`internal_payments.py`。
- 现状：一次请求读全部回款、全部 `finance`、全部 `finance_settlement`、全部客户、全部用户（`_settlement_customer_manager_resolver`）。
- 做法：回款主表的付款人、日期已在 `1.1.447` 下推；继续把客户经理解析改为只查当前涉及的客户名；`finance_settlement` 只读与当前回款相关的记录。

### 步骤 6.7 导出：`/finance/invoices/export`（92 s）、`/finance/general-settlements/export`（138 s）及其他导出

- 共性根因：`finance.py` 的 `_invoice_fee_details` 按每 100 个 ID 递归调用 `_invoice_case_fee_rows`，**每批都重跑整条费用管线**（全量发票、全量退款、全量回款）。1,000 条导出 = 10 次全管线。
- 做法：改为一次调用 `_invoice_case_fee_rows(ids=全部ID)`，内部按 `scalar_in_values` 单参数读取（不再分批递归）。
- `general-settlements/export` 返回 409 前已经算完全部数据：把会返回 409 的校验**移到重查询之前**（409 的条件与文案不变）。
- 所有导出：用快照工具比对文件内容（逐单元格），必须一致。
- 目标：< 10 s。

### 步骤 6.8 其余财务导出

`/finance/fees/query/export`、`/finance/internal-fees/export`、`/finance/case-fees/refunds/export`、`/finance/case-fees/invoice-status/export`、`/finance/incoming-payments/query/export`、`/finance/archive-settlements/*/export`：复用 6.2–6.7 的改造结果；`export_projection.py:56` 读取**全部用户**构建显示名，改为只查导出行涉及的用户名。

---

## 第 7 章 P6：通用接口

### 步骤 7.1 `GET /customers`（3.3 s）

位置与问题（已核实）：
- `app/areas/crm/router.py:1547` 与 `:1816`（经 `_allowed_field_keys` → `app/core/system.py:202`）**同一请求完整解析两次权限**（各含 `select(User)`、角色权限、`_is_contract_approver`）。→ 第一次结果存入局部变量复用。
- `app/core/customer_readmodel.py:36-40` `customer_relationship_counts`：**每次请求扫描全部合同和案件**（`module IN ('contract','case')`，无 ID 限制），再在 Python 中匹配当前页 ≤200 个客户。→ 改为按当前页客户的 `id`/`serial_no`/客户名过滤（三种关联键都要覆盖：`data->>'customer_id'`、`data->>'customer_record_id'`、`data->>'customer_no'`、`customer` 列），匹配逻辑保持原 Python 判断。
- `app/core/customer_readmodel.py:78-80` `customer_person_names`：**`users` 全表无 WHERE**；`:96-99` 全部 HR 记录。→ 只查当前页出现的用户名/工号（集合用 `scalar_in_values`）。
- `app/core/customer_readmodel.py:13-16` `customer_summary`：对全部匹配客户流式求和。对 `sql_paged` 的 scope，改用 SQL `SUM`（注意原代码 `float(value or 0)` 且 `try/except` 跳过非法值：SQL 端要用 `CASE WHEN data->>'x' ~ '^-?[0-9]+(\.[0-9]+)?$' THEN (data->>'x')::numeric ELSE 0 END`，并且最后 `round(..., 2)` 与原来一致）。**若无法证明逐值等价，保留原流式实现。**
- 非 `sql_paged` 的 7 个 scope（`mine`、`recycle`、`department` 等）全量物化后 Python 切片：其筛选依赖 `customer_managers` JSON 数组的精确成员判断，可先用 `data->>'customer_managers' ILIKE '%"用户名"%'` 预筛，Python 保留原判断（规则 A）。

### 步骤 7.2 `GET /tasks/unread-messages`（3.0 s）

位置与问题（已核实）：
- `app/areas/tp/router.py:606-618` 读取用户**全部**未读任务通知，无 LIMIT。
- `:641` 调用 `_task_display_dicts`（`app/core/formatters.py:225`）时没有传 `lightweight=True`，导致 `formatters.py:269-271` **加载全部在职 HR 记录**。→ 确认 `lightweight=True` 下返回字段是否完全一致；一致则传入，不一致则改为按用户名过滤 HR 记录。
- 10 个文本筛选、4 个日期筛选、排序、分页全在 Python（`:637-695`）。
- 做法：规则 A–C；`total` 原本是 `len(items)`（筛选后），改后必须一致。

### 步骤 7.3 `GET /notifications`（3.4 s）

已核实：筛选和分页都已在 SQL。问题只在于：
- 每次请求执行 3 条带相关子查询 `visible_notification_condition()` 的语句（总数、当前页、未读数）。
- 无复合索引 → 第 4 章的 `ix_notifications_recipient_unread` 解决。
- 改完多进程 + 索引后复测；若仍 > 300 ms，再考虑把总数与未读数合并为一条 `COUNT(*) FILTER (WHERE ...)` 语句。

### 步骤 7.4 认证依赖 `current_identity`（所有接口都付这个成本）

`app/security.py:232-272` 每个请求：`select(User)` + `_user_permission_payload`（角色权限、岗位、`_explicit_system_role_menu_keys`、`_is_contract_approver` 扫 `hr` 模块）+ `_page_menu_authorized`。很多接口内部又再算一次。
- 做法：
  1. 请求级复用：把 `_user_permission_payload` 的结果缓存在 `db.info`（每个请求一个 session），同一请求内后续调用直接返回（`_permission_payload_for_identity`、`_allowed_field_keys`、`_record_scope_conditions` 都走它）。
  2. 跨请求缓存（可选，第二阶段）：以 `(username, 权限版本号)` 为键缓存 60 秒；权限版本号在用户、角色、岗位、权限配置任一写入时递增（用第 5 章的按表版本号）。
- 验收：`/auth/me` SQL 条数下降；快照工具对三类用户的所有接口 0 差异。

### 步骤 7.5 案件接口

`/cases/{id}/relations`（43 条 SQL）、`/cases/search`、`/cases/{id}/documents`、`/cases/{id}/logs`、`/cases/{id}/tasks`、`/case-spaces/{id}/context`、`/case-spaces/{id}/workflow-guide`、`/cases/{id}/normal-basic`：
- 本地提交 `0e6baed1`（案件详情二级标签按需加载）已在本分支，**先**用快照工具量化它的效果。
- 对每个接口：用快照工具打印逐条 SQL 及耗时，找出循环内查询（规则 E）和全模块扫描（规则 A），按 6.0 规则改。
- 注意 2.2 修复的 `_case_mine_scope_condition` 会影响 `/cases/search` 的"我的案件"范围，快照用例必须覆盖非管理员用户。

### 步骤 7.6 合同接口

`/contracts/{id}/objects`（148 条 SQL）、`/contracts/{id}/payment-candidates`、`/contracts/{id}/payment-applications`：`finance.py` `_contract_payment_candidate_rows`（约 `:732`）中 `for fee in fee_records:` 逐条 `await _ensure_record_visible(...)`、`for item in objects:` 逐条全模块扫描 `module=='finance'`。→ 规则 E 批量化。

### 步骤 7.7 `GET /records`、`/records/{id}/history`、`/system/menus/navigation`、`/people/options`

按同样方法量化后再决定是否改；多进程上线后若已 < 500 ms 则不改。

---

## 第 8 章 P7：控制台与个人助手

### 步骤 8.1 `GET /dashboard`（739 次、平均 4.3 s、22 条 SQL）

- 位置：`app/areas/system/router.py:1246`。
- 做法：
  1. 快照工具打印 22 条 SQL 及耗时，找出最慢的前 5 条。
  2. 各卡片如果是串行 `await`，在**不同 session** 中并行会引入一致性差异，**不允许**。只允许优化单条查询（索引、读取模型）和去掉重复查询。
  3. 第 5.1 步的缓存键修复会直接提升控制台下钻的命中率。

### 步骤 8.2 `POST /personal-agent/messages`（平均 24.9 s、最大 150 s）

- 先定性：读 `app/areas/personal_agent/router.py:304` 的调用链，确认耗时是否主要在等待外部大模型返回（SQL 平均 1.5 s，其余是等待）。
- 若是：这不是数据库性能问题。多进程上线后它不再阻塞别人（关键收益）。是否改为流式/异步任务属于产品改动，**本次不做**，记录在第 10 章。
- 确认请求超时设置合理（不超过 Nginx 超时），避免 499。

### 步骤 8.3 `GET /personal-agent/workspace`（29 条 SQL）

按第 7 章方法量化，消除循环内查询。

---

## 第 9 章 发布与线上复测

### 批次与顺序

| 批次 | 内容 | 依赖 |
|---|---|---|
| 批次 1 | 第 1 章（工具，只提交不发布）+ 第 2 章（报错修复） | 无 |
| 批次 2 | 第 3 章（多进程 + 选主） | 批次 1 |
| 批次 3 | 第 4 章（索引）+ 第 5 章（缓存） | 批次 2 |
| 批次 4 | 第 6 章（财务） | 批次 3 |
| 批次 5 | 第 7、8 章（通用、案件、控制台） | 批次 3 |

每个批次：
1. 快照工具在生产对比 0 差异；
2. 定向测试、`py_compile`、前端构建（若有前端改动）、`git diff --check`；
3. 按 `docs/skills/oa-fast-deploy/SKILL.md` 领取版本号、构包、激活；
4. 激活后立即：`systemctl status sunhold-oa-api`、`/health`、目标页面 200；
5. 发布后 24 小时与下一个**工作日**各汇总一次 `slow_api`（脚本：`.tmp/perf-probe/allslow.sh` / `since.sh` 的逻辑，提交为 `apps/api-server/scripts/perf/slow_api_report.sh`）。

### 回滚

- 代码批次：激活上一个封存的运行包（发布 skill 的标准回滚）。
- 索引批次：新迁移版本 `DROP INDEX IF EXISTS ...`（不要回退已登记的迁移键）。
- 多进程：把 `OA_NATIVE_API_WORKERS=1` 写入环境文件重启即可回到单进程，选主逻辑在单进程下自然退化为"自己是主"。

### 最终目标（工作日实测）

- 所有列表接口 p95 ≤ 1.5 s；导出 ≤ 10 s；`/auth/me`、`/notifications` 等轻接口 p95 ≤ 300 ms。
- 5xx（除确实的上游不可用）为 0；503 为 0。
- 快照工具全部用例 0 差异。

---

## 第 10 章 执行记录（Codex 每完成一步就填写）

### 进度表

| 步骤 | 提交 | 快照差异 | 改前 wall/SQL/条数 | 改后 wall/SQL/条数 | 发布版本 | 备注 |
|---|---|---|---|---|---|---|
| 1.x 工具 | | — | — | — | 不发布 | |
| 2.1 legacy-ls 503 | | | 3.6 s / 503 | | | |
| 2.2 json~~text | | | 500 | | | |
| 2.3 参数超限 | | | 500 | | | |
| 2.4 float None | | | | | | |
| 2.5 coroutine | | | 已修复，核对 | | | |
| 3.x 多进程 | | | `/auth/me` 3.0 s | | | |
| 4.x 索引 | | | `internal-fees` 主查询 472 ms | | | |
| 5.x 缓存 | | | 命中率≈0，503×147/7天 | | | |
| 6.1 payment-workflow | | | 9.6 s / 9,380 条 | | | |
| 6.2 internal-fees | | | 3.3 s（进程内） | | | |
| 6.3 fees/query | | | 7.9 s（进程内） | | | |
| 6.4 case-fees/refunds | | | 12 s / 165 条 | | | |
| 6.5 incoming-payments | | | 5.5 s | | | |
| 6.6 settlements pending | | | 8.0 s | | | |
| 6.7 导出 | | | 92 s / 138 s | | | |
| 7.1 customers | | | 3.3 s | | | |
| 7.2 unread-messages | | | 3.0 s | | | |
| 7.3 notifications | | | 3.4 s | | | |
| 7.4 auth | | | 3.0 s | | | |
| 7.5 cases | | | 5.0 s / 43 条 | | | |
| 7.6 contracts | | | 4.6 s / 148 条 | | | |
| 8.1 dashboard | | | 4.3 s / 22 条 | | | |

### 已知易变字段（快照比较时允许忽略的字段及理由）

（改前代码连续运行两次仍不同的字段才可登记）

### 待定结论

- `case_agent_runtime.start()` 是否启动后台任务：
- 各索引被哪个查询使用：
- `personal-agent/messages` 耗时构成：

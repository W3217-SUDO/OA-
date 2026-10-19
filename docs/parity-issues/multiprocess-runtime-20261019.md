# API 多进程运行（R7）

- 日期：2026-10-19
- 背景：生产 API 由单个 uvicorn 进程处理全部请求。一个 5～9 秒的财务查询在事件循环里做 JSON 解码和逐行计算时，其他所有请求（包括 `/api/v1/auth/me`）都要排队。
- 目标：以多个工作进程运行，慢请求不再阻塞其他请求；业务行为与单进程完全一致。

## 一、启用方式

代码本身不改变进程数。未设置时仍是单进程，行为与改动前相同。

uvicorn 在未传 `--workers` 时读取环境变量 `WEB_CONCURRENCY`。生产通过 systemd drop-in 设置：

```ini
# /etc/systemd/system/sunhold-oa-api.service.d/60-workers.conf
[Service]
Environment=WEB_CONCURRENCY=4
```

```bash
systemctl daemon-reload && systemctl restart sunhold-oa-api
```

**回滚**：删除该 drop-in，`daemon-reload` 后重启，即回到单进程。不需要回退代码。

### 容量

| 项 | 数值 |
|---|---|
| 服务器 | 4 核 / 15.5 GB，可用约 11.5 GB |
| 单进程常驻 | 约 950 MB |
| 4 进程预计 | 约 4 GB |
| 数据库连接 | 每进程连接池 5+10，4 进程最多 60；PostgreSQL `max_connections=100`，改动前实际使用 12 |

## 二、多进程下必须处理的进程内状态

逐项排查了全部进程内全局状态、全局锁、后台任务和磁盘状态文件。

| 位置 | 单进程时的保证 | 多进程下的问题 | 处理 |
|---|---|---|---|
| 后台循环：业务规则、钉钉通知、通知/短信调度（`lifecycle.py`） | 只运行一份 | 每个进程各跑一份：重复写业务数据、重复发钉钉/短信 | PostgreSQL 会话级 advisory lock 选主，只有主进程运行；主进程退出或连接断开时锁释放，其他进程在 15 秒内接管 |
| 后台循环：系统缓存定时清理 | 清本进程缓存 | 清的是本进程缓存 | 每个进程都运行（不变） |
| `case_agent_runtime.start()` | 启动一次 | 多个进程同时初始化 LangGraph 检查点表，个别进程可能失败而使案件智能体不可用 | 用 advisory lock 串行化初始化 |
| 合同编号 `_contract_serial_lock`（`asyncio.Lock`） | 防止并发新建合同时编号重复 | 只约束本进程，不同进程会生成同一编号（唯一索引报 500） | `_next_contract_serial_no` 加事务级 advisory lock，持有到调用方提交 |
| 系统参数缓存 `SYSTEM_PARAMETER_CACHE` | 修改参数时清除缓存 | 只清处理修改请求的那个进程，其他进程一直返回旧参数 | 缓存条目记录对应分类全部参数行的数据库指纹，读取前比对，不一致即作废（`app/core/system_parameter_cache.py`） |
| 个人智能体会话文件 `STATE_LOCK` | 读-改-写互斥 | 不同进程同时写同一会话/索引文件会丢更新 | 改为“进程内锁 + 跨进程文件锁” |
| 个人智能体 `_ACTIVE_OPERATIONS` | “对话正在处理”409 保护；“停止生成”找到并取消正在生成的任务 | 停止请求落到另一个进程时找不到任务，按钮静默失效；两个进程可同时操作同一对话 | 运行中的操作登记到共享文件；其他进程据此返回 409；“停止生成”跨进程时写入取消请求，由所在进程取消任务，请求方等待其释放后返回（与单进程等待任务结束一致） |
| 个人智能体记忆文件（`memory_graph.py`） | 同步函数天然原子 | 不同进程同时读-改-写丢更新 | 跨进程文件锁；同进程嵌套调用按深度计数，不重入死锁 |
| 银行流水识别 `_recognition_slot = Semaphore(1)` | 外部识别接口同一时刻只调用一次 | 变成同时 N 次 | 增加跨进程文件锁 |

确认无需处理：

- 启动迁移和基础数据初始化：已用 `pg_advisory_xact_lock` 串行化
- MCP 网关：`stateless_http=True`，无会话状态
- 查询缓存：Redis 共享
- 控制台统计缓存：每次按数据库快照校验
- 智能体流式响应：任务在单个请求内创建和结束
- 技能目录配额 `skill_catalog._requests`：代码注释已写明按进程计数，多进程下总配额放大为 N 倍，属外部目录请求限流，不涉及业务数据

锁文件和登记文件放在临时目录下的 `sunhold-oa-coordination/`。生产服务 `PrivateTmp=yes`，同一服务的所有工作进程共享该临时目录，服务重启时清空。

## 三、验证

### 单元测试

`tests/test_multiprocess_coordination.py`，11 项：跨进程文件锁互斥（真实子进程持锁）、等待锁不阻塞事件循环、其他进程的对话操作返回 409、已退出进程的残留登记被忽略、跨进程“停止生成”写取消请求并等待释放、不可中断操作拒绝停止、取消请求转给本进程任务、本进程停止行为不变、记忆函数嵌套不死锁、只读查询不创建用户目录、非 PostgreSQL 直接运行后台循环。

相关现有测试：个人智能体、记忆、启动迁移、合同编号、钉钉等 95 项通过，14 项跳过。

### 本地 4 进程实例（生产数据副本）

| 检查 | 结果 |
|---|---|
| 主进程锁持有者 | 恰好 1 个，连接处于 idle（无长事务） |
| 依次 `SIGKILL` 工作进程 | 每个被杀进程立即由 uvicorn 补回；杀到主进程后锁在 25 秒内转移，始终只有 1 个持有者，`/health` 一直 200 |
| 系统参数指纹 | 修改参数行后指纹变化、缓存条目作废；回滚后指纹恢复 |
| 合同编号锁 | 第一个连接持锁期间第二个连接等待，释放后才拿到编号 |

所有写操作在事务中回滚。

### 慢请求阻塞对比

三个财务慢查询并发进行时，每 0.5 秒请求一次 `/api/v1/auth/me`：

| | 1 进程 | 4 进程 |
|---|---|---|
| `auth/me`（6 次） | 1.01 / 0.03 / 0.22 / 1.68 / 0.05 / 0.27 秒 | 0.004～0.008 秒 |
| `fees/query` | 9.0 秒 | 5.0 秒 |
| `case-fees/refunds` | 8.7 秒 | 8.2 秒 |

## 四、已知限制

- 主进程的数据库连接静默断开时，最长 10 秒（心跳间隔）后才发现；这段时间内新主进程可能已接管，两个进程的后台循环会短暂重叠。仅在数据库连接异常时发生。
- 多进程只消除排队，不降低单个慢查询本身的耗时；单接口优化见 `finance-endpoint-performance-analysis-20261019.md`。

## 五、上线记录（2026-10-20）

### 1.1.480 与多进程

- 1.1.480（提交 `2bf8f79b`）按部署 skill 发布：发布租约、领号、门禁、封存、激活，队列/账本/回执齐全；GitHub `dev`、`main`、`v1.1.480` 一致。
- 发布前 1.1.479（`codex-finance-totals-sticky-20261019`）已上线但缺少 `v1.1.479` 标签，分配器拒绝领号。核对生产 `current`=1.1.479、`source_commit`=`ed65394e`、manifest SHA256 `548ec423…` 与队列记录一致后补打该标签；其账本缺少的 1.1.479 记录未改动。
- 启用：`/etc/systemd/system/sunhold-oa-api.service.d/60-workers.conf` 设置 `WEB_CONCURRENCY=4`。核对：4 个工作进程，后台主进程锁持有者 1 个，API/Web active，`/health` 200，公网 200，无错误日志。

### PostgreSQL 内存配置

改前生产库累计排序/聚合溢出写盘 22,988 次、154 GB（`work_mem` 为默认 4MB）。本地生产数据副本上对 21 个财务接口对比：

| 接口 | work_mem 4MB | 64MB | 64MB + 关 JIT |
|---|---|---|---|
| 一般结算申请 | 10.1 秒 | 4.7 秒 | 4.3 秒 |
| 待归档结算 | 14.4 秒 | 7.1 秒 | 7.1 秒 |
| 归档结算付款 | 10.4 秒 | 5.1 秒 | 5.0 秒 |
| 合计 | 80.8 秒 | 57.6 秒 | 55.9 秒 |

关 JIT 只差 3%，未采用。

已通过 `ALTER SYSTEM` + `pg_reload_conf()` 应用（无需重启）：

| 参数 | 原值 | 新值 |
|---|---|---|
| `work_mem` | 4MB | 64MB |
| `maintenance_work_mem` | 64MB | 512MB |
| `effective_cache_size` | 8GB | 10GB |

基线（用于之后对比溢出是否减少）：2026-10-20 01:08:58 `temp_files=22988`、`temp_bytes=154 GB`。

回滚：`ALTER SYSTEM RESET work_mem; ALTER SYSTEM RESET maintenance_work_mem; ALTER SYSTEM RESET effective_cache_size; SELECT pg_reload_conf();`（改前的 `postgresql.auto.conf` 备份为 `postgresql.auto.conf.bak-claude-20261020`）。

内存预算按保留 6 GB 余量：改后可用约 10.3 GB；`work_mem` 按需临时占用，最坏情况约 17 个连接同时做大聚合时约 4 GB，仍在余量内。

### shared_buffers 提到 8GB（用户要求，2026-10-20 01:27）

- 生产库 `huzhi_oa_20261003` 为 3.8 GB（另有 3.4 GB 的预拷贝库平时不访问）。`shared_buffers` 按实际读取的数据占用，预计稳定后约 4 GB，可用内存仍在 6 GB 以上。
- `ALTER SYSTEM SET shared_buffers = '8GB'` 后重启 `postgresql@16-main`，1 秒恢复。核对：`shared_buffers`=8GB；PostgreSQL、API、Web active；`/health` 200；公网 200；后台主进程锁持有者 1 个（重启后自动重新选出）；API 无错误日志。
- 重启后缓存为空，随访问逐步加载，前几分钟查询可能略慢。
- 回滚：`ALTER SYSTEM SET shared_buffers = '2GB'` 后重启数据库；改前配置备份为 `postgresql.auto.conf.bak-claude-shared-buffers-20261020`。

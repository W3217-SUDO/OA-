# 生产权威（Mac 发布机）

GitHub `origin` 是唯一源码权威；生产服务器是版本队列、锁和运行版本的权威。腾讯已于 2026-10-12 退役；测试服务器 `150.158.3.104` 已暂停使用。两者都不连接、不部署。

## 生产服务器身份

最近一次核实：2026-10-20，从本 Mac 只读检查。以下是线索，每次发布前重新读取；主机名、IP 或主机密钥不一致时停止。

| 项目 | 值 |
| --- | --- |
| 主机名 | `oa-production-app` |
| 公网 IP | `47.93.166.123` |
| 公网入口 | `https://huzhilawfirm.com`（`/health`、`/build-info.json`） |
| 系统 | Ubuntu 24.04.5 LTS，`root` 登录，本机密钥 `~/.ssh/id_ed25519_oa` |
| systemd | `sunhold-oa-api`、`sunhold-oa-web`、`sunhold-oa-cache-redis`（以 `sunhold-oa` 用户运行） |
| 本机端口 | API `127.0.0.1:8001/health`，Web `127.0.0.1:8089`，Nginx `80/443` |
| 运行入口 | `/opt/sunhold-oa/runtime/enterprise/current` → `packages/<版本>`（root 所有，`chattr +i`） |
| 激活环境文件 | `/opt/sunhold-oa/private/production-native.env`（含秘密，只在服务器上引用，不读出、不复制） |
| 运行 Python | `runtime/enterprise/environments/requirements-<lock 的 SHA256 前 12 位>-py3123/bin/python` |
| 运行工具 | `runtime/enterprise/tools/<版本>/native_runtime.py`（以 `systemctl cat sunhold-oa-api.service` 最后一条 `ExecStart` 为准；2026-10-20 为 `1.1.484`） |

## 唯一的锁、队列和暂存目录

| 用途 | 唯一路径 | 说明 |
| --- | --- | --- |
| 发布锁 | `/opt/sunhold-oa/locks/formal-release.lock` | 改队列或 `current` 的命令一律 `flock -n` 它 |
| 领号锁 | `/opt/sunhold-oa/locks/version-allocation.lock` | `release_queue.py` 内部自动使用，不手动拿 |
| 队列 | `/opt/sunhold-oa/releases/queue.tsv` | 6 列 TSV：版本、状态、提交、owner、范围、UTC 时间 |
| 账本 | `/opt/sunhold-oa/releases/ledger.tsv` | `activating`/`released`/`failed` 同步追加 |
| 回执 | `/opt/sunhold-oa/releases/<版本>-<主题>-receipt.json` | |
| 暂存 | `/opt/sunhold-oa/staging/` | 只放本次文件，发布后删自己的 |

`releases/formal-release.lock`、`runtime/enterprise/formal-release.lock`、`runtime/enterprise/release-queue.tsv`（停在 1.1.450）是历史遗留，不是锁也不是队列，不读不写。

2026-10-28：`current` 为 `1.2.28`。版本号以队列和 GitHub 标签为准，每次发布前重新读取，不凭这里的记录。

## 连接方式

本 Mac 不配置 SSH 别名。主机密钥已在 `~/.ssh/known_hosts`，保持严格校验。

```bash
OA_SSH=(ssh -i ~/.ssh/id_ed25519_oa -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes root@47.93.166.123)
OA_SCP=(scp -i ~/.ssh/id_ed25519_oa -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes)
"${OA_SSH[@]}" hostname    # 必须输出 oa-production-app
```

2026-10-20 直连已验证，不需要代理。开 VPN 后若在认证前超时，给该 IP 设直连规则，不改系统路由。

## 版本号与分配器

- `1.1.602` 之后改从 `1.2.1` 起编号（用户 2026-10-27 要求），此后沿 `1.2.x` 递增：下一号 = 队列与 GitHub 标签中最大的 `1.2.x` + 1，不再发 `1.1.x`。`release_queue.py` 同时认 `1.1.N`（只用于识别历史）和 `1.2.N`（`CURRENT_MINOR = 2`），`github_release_refs.py` 抓取 `v1.1.*`、`v1.2.*` 两种标签。
- 生产 `/opt/sunhold-oa/scripts/` 中的 `reserve_oa_version.sh`、`reassign_oa_version.sh`、`release_queue.py`、`github_release_refs.py` 与仓库 `docs/skills/oa-fast-deploy/scripts/` 同名文件一致（2026-10-28 核对，四个文件 SHA256 全部相同；`release_queue.py` 为 `d210b4d8cedc5d20353057ade202bf5ba9e1a7d481f9ddc01848b37b02387ce3`）。替换前两边核哈希，一起安装。
- 本地运行这些脚本（生成 refs 快照等）要用**发布 worktree 里**的副本：共享工作区的 `dev` 可能停在旧提交，旧副本只认 `v1.1.*` 标签，领号会报“生产已发布基线与 GitHub 标签不一致”。
- `reserve` 要求：目标提交等于 GitHub `dev`、已发布基线与其标签一致、GitHub 上没有队列不认识的更高版本、队列无 `assigned`/`activating`。输出即本次版本号。
- `reassign` 只用于把自己 `assigned` 且尚无正式标签的版本改绑到新提交。
- 生产机访问 GitHub 曾出现 GnuTLS 错误，所以 refs 由 Mac 用 `github_release_refs.py capture --remote origin` 生成快照（45 秒上限，拒绝覆盖已有文件），连同 SHA256 传到生产；快照超过 5 分钟作废重做。环境变量：`OA_RELEASE_SOURCE_URL=https://github.com/W3217-SUDO/OA-.git`、`OA_RELEASE_PYTHON`（运行环境 python 绝对路径）、`OA_RELEASE_REFS_FILE`、`OA_RELEASE_REFS_SHA256`。

## 依赖变化（慢路径）

运行 Python 环境按 `apps/api-server/requirements.lock`（去掉 `\r` 后）的 SHA256 前 12 位命名：`tr -d '\r' < requirements.lock | shasum -a 256 | cut -c1-12`。Windows 打包的旧包 lock 带 CRLF，直接算哈希会不同（如 `d191e96f1bcd` 实为 `d544fdf35ade`），不要据此误判依赖变化。lock 未变则直接复用现有环境；lock 变化时，先在生产新建 `environments/requirements-<新 hash>-py3123` 并带哈希安装，再新增 systemd drop-in 指向它，`daemon-reload` 后激活。这一步会让发布多出 5～10 分钟，提前规划。

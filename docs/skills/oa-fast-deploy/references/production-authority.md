# Production Authority (Mac 发布机)

腾讯服务器已于 2026-10-12 退役。GitHub 是唯一源码权威；当前生产服务器是版本队列、计数、分配锁和激活锁的权威。不要再连接腾讯，也不要把它的状态作为发布步骤。

## 生产服务器身份

最近一次核实：2026-10-20，从本 Mac 只读检查。

| 项目 | 值 |
| --- | --- |
| 主机名 | `oa-production-app` |
| 公网 IP | `47.93.166.123` |
| 公网入口 | `https://huzhilawfirm.com` |
| 系统 | Ubuntu 24.04.5 LTS |
| 登录 | `root`，本机密钥 `~/.ssh/id_ed25519_oa`（注释 `oa-mac-claude-20261020`） |
| 部署根目录 | `/opt/sunhold-oa`（`locks/`、`releases/`、`runtime/`、`scripts/`、`staging/`） |
| systemd | `sunhold-oa-api`、`sunhold-oa-web`、`sunhold-oa-cache-redis`，以 `sunhold-oa` 用户运行 |
| 本机端口 | API `127.0.0.1:8001`（`/health`），Web `127.0.0.1:8089`，Nginx `80/443` |
| 运行入口 | `/opt/sunhold-oa/runtime/enterprise/current` → `packages/<版本>` |

以上是交接线索，不是当前事实：每次发布前都要重新读取。主机名、IP 或主机密钥与上表不一致时，停止并核实，不要连到别的机器。

## 连接方式

本 Mac 不配置 SSH 别名，直接写完整参数。主机密钥已在 `~/.ssh/known_hosts`，保持严格校验，不使用 `StrictHostKeyChecking=no`。

```bash
OA_SSH=(ssh -i ~/.ssh/id_ed25519_oa -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes root@47.93.166.123)
"${OA_SSH[@]}" hostname    # 必须输出 oa-production-app
```

`scp` 使用同样的 `-i`、`-o IdentitiesOnly=yes`、`-o StrictHostKeyChecking=yes` 参数。2026-10-20 本机直连已验证，不需要代理或绑定网卡；若开启 VPN 后连接在认证前超时，先关闭 VPN 的全局模式或给该 IP 设直连规则，不改系统路由、不复制凭据。

## 核对目标

- 用有界的直连 SSH 检查，确认主机名、有效 systemd 单元、运行解释器、`current` 指向和 manifest、公开 build-info 与 health。
- 运行解释器以 `systemctl cat sunhold-oa-api.service` 最后一条 `ExecStart` 为准（2026-10-20 为 `runtime/enterprise/environments/requirements-d544fdf35ade-py3123/bin/python` 和 `tools/1.1.484/native_runtime.py`）；不要凭记忆填路径。
- 激活只把 `/opt/sunhold-oa/runtime/enterprise/current` 切到新的封存包；生产上不构建、不拉源码。

## 保护队列

安装或调用分配器前，对比生产 `releases/queue.tsv`、`ledger.tsv`、当前运行回执和 GitHub 已发布标签。修改发布元数据前，先把受影响的那几行导出到部署树之外；这类只改元数据的操作不需要业务数据库备份。

占用、失败、待定的版本都要连同准确提交和所有者一起保留。保留原始分配时间；没有就写 `unknown`，交接时间另记，不能拿就绪或交接时间冒充。标签存在不代表发布成功。不删除他人预留、不复用其版本号、不另起计数器。前一个所有者仍在活动时，先协调再激活；跨会话消息需要用户授权。

2026-10-20 的状态：`current` 为 `1.1.493`（提交 `eeae41673a4e7e6eca4185143adc44ade7aaf6b2`，`claude-finance-cache-20261020`），队列中没有未收口的预留，三个锁文件为 `locks/formal-release.lock`、`locks/version-allocation.lock`、`locks/metadata-handover.lock`。分配前必须重新读取；队列无法解释某个未完成版本时，停止分配，先处理该条记录。

## 版本号

按用户 2026-10-20 的决定，版本号沿生产实际序列继续 `1.1.x` 递增（`1.1.493` 之后是 `1.1.494`），不进位到 `1.2.x`。生产 `scripts/release_queue.py` 与仓库 `scripts/release_queue.py` 已对齐为同一份（SHA256 `f927c749e8a82310d13084a83c3f3903fd2a1248e49061d4c88bc840e83c3aa7`）；安装或替换前核对哈希，两边不一致时以生产正在使用的版本为准并先查清差异。

## 生产分配器

使用生产服务器 `/opt/sunhold-oa/scripts`（不可变运行包之外）中的脚本。替换前先查看已安装脚本及其调用方；`reserve_oa_version.sh`、`reassign_oa_version.sh`、`release_queue.py`、`github_release_refs.py` 必须一起安装并核哈希。包装脚本保留原有位置参数，并使用：

- `OA_RELEASE_SOURCE_URL`：必填，已核实的 GitHub 远端 URL（`https://github.com/W3217-SUDO/OA-.git`）；用已配置的认证，不在 URL 里嵌 token。
- `OA_RELEASE_ROOT`：部署根目录，默认 `/opt/sunhold-oa`。
- `OA_RELEASE_PYTHON`：必填，来自生产有效运行环境的绝对 Python 路径。
- `OA_RELEASE_REFS_FILE`、`OA_RELEASE_REFS_SHA256`：必填，从 Mac 传过去的 refs 快照及独立核对的 SHA256。
- 生产 `locks/version-allocation.lock` 和 `releases/queue.tsv`。

生产机读 GitHub 曾出现 GnuTLS 接收错误，所以 refs 由 Mac 生成快照后传过去，不在生产上重试或换源。快照脚本对已配置的 GitHub HTTPS 源执行 `git ls-remote`（45 秒上限），读取 `dev`、`main` 和全部已占用的 `v1.1.*`，不会覆盖已存在的快照文件；生产上不需要源码检出或 GitHub 凭据。

本 Mac 的仓库里 GitHub 远端名为 `origin`（不是 `github`），必须显式传 `--remote origin`：

```bash
PY=~/.local/bin/python3.12
REFS="$(mktemp -d)/github-refs.json"    # 每次用新目录，脚本拒绝覆盖已有文件
"$PY" -B docs/skills/oa-fast-deploy/scripts/github_release_refs.py capture \
    --repository "$PWD" --remote origin --output "$REFS"
shasum -a 256 "$REFS"    # 与脚本返回的 SHA256 对比后再 scp 到生产 staging
```

生产分配器要求：源 URL 和 SHA256 匹配、快照不超过 5 分钟、`dev` 与已发布一致、基线标签匹配、占用版本交接完整且没有未收口预留。分配前、以及激活前快照超时都要重新生成。缺权限、快照无效或过期、队列元数据不完整都是明确错误，不允许空结果当成功。快照及其哈希保存在服务器之外的发布回执里，用完精确删除服务器 staging 路径。

## 合批与串行

正常发布按生产实际队列串行。正式整合前先把候选分支正常推送到已核实的 GitHub 远端，并核对远端准确 SHA。同时开发或存在别的未完成候选，不是合批或拖延就绪工作的理由。只有就绪所有者确实争用同一个正式发布/版本切换时段，才可协商合并已授权、已推送的 Codex 候选；否则保持串行。涉及 Claude 的冲突一律串行。用户明确要求单独发布时以其为准。

Codex 合批或另获授权的合并发布：在生产元数据锁内，按原始目标、所有者、范围和时间导入每个未收口的原预留，再调用分配器。只有协调者可以为已导入、已分配、已打标签的候选设置 `OA_RELEASE_CONSOLIDATE_VERSIONS=<准确版本列表>`。分配器在新预留上记录 `consolidates=`，原行不动。新包健康上线后，再给每个原版本追加 `consolidated`，保留原提交和所有者并写 `consolidated_into=<新版本>`；失败时原记录保持未收口。正在激活的版本不能改成合并候选。Claude 冲突队列中的等待不是合并，不产生这些记录。

当前唯一发布者持有正式 mutex，负责共享 dev 更新、版本分配和激活；运行准确 HEAD 检查，在 Mac 本地构建，封存并激活一个不可变包，核对运行，记录回执，并把 GitHub `main` 快进。完整整合后精确删除多余的临时远端分支，fetch/prune 并确认不存在；保留正式分支、标签以及未完成或仍需要的候选。冻结后的发布不再收新改动。

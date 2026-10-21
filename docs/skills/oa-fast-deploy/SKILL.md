---
name: oa-fast-deploy
description: OA 正式发布（Mac 发布机 → 生产服务器 oa-production-app）。按生产队列串行、一次推送、一个版本号、不可变运行包激活并可回滚。用于把已验证的 dev 改动快速发布上线、回滚和清理临时分支。
---

# OA 快速发布（Mac）

目标：一次发布约 10 分钟，只推一次 `dev`，只跑一次门禁，不等 GitHub CI。生产服务器、端口、路径见 [production-authority.md](references/production-authority.md)，每次发布前重新读取，不凭记忆。

## 不变的底线（任何加速都不能破）

- **只发生产，不发测试服务器。** 测试服务器（`150.158.3.104`、8088/8089/8091）已暂停，不部署、不重启、不作为验收入口；腾讯已退役。
- **串行。** 生产 `releases/queue.tsv` 中有 `assigned`/`activating` 未收口时不发布，先查清所有者。不删他人记录、不复用占用或失败的版本号、不改正式标签、不 force-push。
- **一把锁。** 生产上每条会改队列或 `current` 的命令都用 `flock -n /opt/sunhold-oa/locks/formal-release.lock <命令>` 执行，拿不到就停。只认这一个文件；`releases/`、`runtime/enterprise/` 下的同名文件不是锁。领号后队列里的 `assigned` 行会挡住其他人领号，所以领号与激活之间不必一直挂着 SSH。
- **不可变包。** 新版本只装进 `runtime/enterprise/packages/<版本>`，`chattr -R +i` 封存后切 `current`；不改旧包，不在生产构建或拉源码。旧包保留为回滚点。
- **数据库。** 无迁移/数据补丁就不备份；有则先对受影响表做最小外置备份并写明恢复方法，禁止无授权的全库替换。
- **问题表来源的候选**须先有 `docs/skills/problem-remediation/SKILL.md` 要求的逐行文档和证据；发布只代表已上线，不代表 `1/已验收`。
- **默认自动部署（用户 2026-10-21 授权）。** 用户直接提出 OA 功能修改或问题修复，即授权在该范围完成实现和必要检查后，正常推送 GitHub `dev`、串行排队、分配版本并部署生产，不等待第二次“部署”或发布确认；健康通过后自动将 `main` 快进至本次发布提交。用户明确要求“仅本地”“先预览”“暂不提交/推送/发布”时，按该次限制停止对应步骤。Excel 批次或明确要求统一发布的任务，仍须整批完成后一次发布，不逐行部署。此授权不扩大修改范围，不允许夹带其他会话未就绪内容、绕过发布锁或检查、另行写业务数据或覆盖数据库；遇到构建、基线、版本、迁移或发布锁阻碍时保留成果并报告具体原因。

## 分支规则：dev 是测试，main 是已上线

- **`dev`**：集成与测试分支。所有改动都先推到 `dev`（必须过 pre-push 门禁），可以包含尚未上线的提交。
- **`main`**：只代表已经上线且验证没问题的代码。不在 `main` 上直接提交、不 merge commit、不 force-push，只做快进。
- **何时合并到 `main`**：生产激活成功、`build-info.json` 显示本次 `N`/`TARGET`、健康检查和错误日志都正常后，立即把 `main` 快进到本次发布提交 `TARGET`（第 6 步）。**这一步自动执行，不再等用户确认**（用户 2026-10-21 决定）：直接 OA 修改/修复的默认发布授权或用户明确要求发布，均同时授权推送 `main`，发布流程里不得停下来询问“是否推 main”。只有回滚、发布失败、健康或错误日志不正常，或用户在本次发布请求里明确说“先不要推 main”时，`main` 才不动；此时要在汇报里写明原因。
- **同步关系**：`main` 必须始终是 `dev` 的祖先（`git merge-base --is-ancestor origin/main origin/dev` 成立）。发布收尾后 `main` = 本次发布提交；发布期间 `dev` 上新增的提交等下一次发布再随之进入 `main`。快进被拒绝说明有人直接改了 `main`，停下查清，不强推。

## Mac 环境（一次性，已就绪则跳过）

- Node 22：`~/.local/node`；门禁 Python：`~/.local/share/oa/quality-py312`（按两个 lock 文件带哈希安装）。`~/.zprofile` 已导出 `OA_QUALITY_NODE`、`OA_QUALITY_PYTHON`。
- pre-push 门禁：`sh scripts/install-quality-hook.sh`（装到 `.git/hooks`，不设 `core.hooksPath`，不需要 PowerShell）。
- GitHub 远端名 `origin`；只 fetch `origin`，不 `fetch --all`。本机没有 GitHub HTTPS 凭据，推送走 SSH（本机密钥 `id_ed25519_oa` 已绑定 GitHub 账号 `W3217-SUDO`），不改 `origin` 的地址（refs 快照脚本要求 fetch/push 地址一致）：

  ```bash
  OA_GH=git@github.com:W3217-SUDO/OA-.git
  export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_oa -o IdentitiesOnly=yes -o BatchMode=yes"
  ```

- 工作区有别人未提交的改动时，门禁会拒绝推送：在临时 worktree（`git worktree add --detach <目录> origin/dev`）里 cherry-pick 自己的提交再推，推完用 `git reset --keep origin/dev` 同步本地 `dev`，别人的改动原样保留。
- `apps/admin-web/node_modules` 用 `npm ci` 安装。

## 快速流程

以下在仓库根目录执行。`OA_SSH`/`OA_SCP` 的定义见 production-authority.md；`OWNER` 用本次唯一会话名（如 `claude-<主题>-<日期>`）。

### 1. 准备（本地，约 1 分钟）

```bash
git switch dev && git fetch origin && git rebase origin/dev   # 线性，冲突就停下解决
git status --short                                            # 必须为空
"${OA_SSH[@]}" 'tail -n 3 /opt/sunhold-oa/releases/queue.tsv; readlink -f /opt/sunhold-oa/runtime/enterprise/current'
git ls-remote --tags origin 'v1.1.*' | sed 's#.*/v##; s#\^{}##' | sort -t. -k3 -n | tail -1
```

队列最后一行必须是 `released` 且等于 `current`。下一个版本号 `N` = 队列与 GitHub 标签中最大号 + 1（只沿 `1.1.x`，不进位）。

### 2. 写版本号并推送一次（本地，约 1 分钟门禁）

```bash
cd apps/admin-web && npm version "$N" --no-git-tag-version && cd ../..   # 同时改 package.json 与 package-lock.json
git add -- apps/admin-web/package.json apps/admin-web/package-lock.json   # 加上本次必要的交接文档
git commit -m "chore(release): set <主题> version $N [skip ci]"
git push "$OA_GH" HEAD:dev      # pre-push 门禁自动跑，失败就修，不绕过
TARGET=$(git rev-parse HEAD)
```

一次发布只推一次 `dev`：版本号与代码同批推送，不再先推代码、领号后再推版本。

### 3. 取锁、领号（生产，几秒）

```bash
REFS="$(mktemp -d)/github-refs.json"
~/.local/bin/python3.12 -B docs/skills/oa-fast-deploy/scripts/github_release_refs.py capture --repository "$PWD" --remote origin --output "$REFS"
SHA=$(shasum -a 256 "$REFS" | cut -d' ' -f1)
"${OA_SCP[@]}" "$REFS" root@47.93.166.123:/opt/sunhold-oa/staging/refs-$OWNER.json
```

在生产上领号（整条命令包在 `flock -n /opt/sunhold-oa/locks/formal-release.lock` 里）：

```bash
OA_RELEASE_SOURCE_URL=https://github.com/W3217-SUDO/OA-.git \
OA_RELEASE_PYTHON=<current 运行环境的 python> \
OA_RELEASE_REFS_FILE=/opt/sunhold-oa/staging/refs-$OWNER.json OA_RELEASE_REFS_SHA256=$SHA \
/opt/sunhold-oa/scripts/reserve_oa_version.sh "$TARGET" "$OWNER" "<范围>;no-schema|<迁移说明>"
```

输出必须等于 `N`。不等于说明有人插队：停止，按实际队列重新写版本号（第 2 步）后用 `reassign_oa_version.sh <N> <旧提交> <新提交> <OWNER> <范围>` 改绑，不另起号。refs 快照超过 5 分钟要重新生成。

### 4. 构建与打包（本地，约 2 分钟，可与第 3 步并行）

```bash
cd apps/admin-web && npm ci && "$OA_QUALITY_NODE" scripts/build-production.mjs && cd ../..
PKG="$(mktemp -d)/$N"
"$OA_QUALITY_PYTHON" scripts/runtime_package.py build --output "$PKG"
"$OA_QUALITY_PYTHON" scripts/runtime_package.py verify --output "$PKG"
# 只传差异（用户 2026-10-21 决定，所有发布都这样）：以生产上一版（current 指向的包）为参照做增量上传，
# 未变文件直接复用，通常只传 1MB 左右、1 分钟内完成；整包 scp 在这条线路上要 15 分钟以上，不再使用。
PREV=$("${OA_SSH[@]}" 'readlink -f /opt/sunhold-oa/runtime/enterprise/current')
"${OA_SSH[@]}" "mkdir -p /opt/sunhold-oa/staging/$N-dir"
rsync -a -c -z -e "ssh -i ~/.ssh/id_ed25519_oa -o IdentitiesOnly=yes -o BatchMode=yes" --link-dest="$PREV/" "$PKG/" root@47.93.166.123:/opt/sunhold-oa/staging/$N-dir/
# 逐文件核对：本地与服务器文件清单的 SHA256 汇总必须一致，文件数也一致，否则不得继续
(cd "$PKG" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256)
"${OA_SSH[@]}" "cd /opt/sunhold-oa/staging/$N-dir && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum"
```

构建绑定 `TARGET`：构建后不再改源码；`build-info.json` 与 manifest 的版本和提交必须是 `N`/`TARGET`。构建和校验始终在 Mac 上完成，生产只接收核对一致的包，不在生产构建或拉源码。

### 5. 安装、封存、激活（生产，约 1 分钟，整段包在 `flock -n` 里）

```bash
E=/opt/sunhold-oa/runtime/enterprise
test ! -e $E/packages/$N                                 # 目标目录必须原本不存在
cp -a /opt/sunhold-oa/staging/$N-dir $E/packages/$N       # 复制成独立文件，不与旧包共用硬链接
chown -R root:root $E/packages/$N && chattr -R +i $E/packages/$N
printf '%s\tactivating\t%s\t%s\t%s\t%s\n' "$N" "$TARGET" "$OWNER" "<范围>;sealed" "$(date -u +%FT%T%:z)" | tee -a /opt/sunhold-oa/releases/queue.tsv >> /opt/sunhold-oa/releases/ledger.tsv
<运行环境 python> -B $E/tools/<当前工具版本>/native_runtime.py --env-file /opt/sunhold-oa/private/production-native.env \
    activate --package $E/packages/$N --current $E/current --expected-commit "$TARGET"
```

- 运行环境 python 与工具版本以 `systemctl cat sunhold-oa-api.service` 最后一条 `ExecStart` 为准。
- 若 `apps/api-server/requirements.lock` 有变化（去掉 `\r` 后 SHA256 前 12 位不等于现用 `environments/requirements-<hash>-py3123`），这是慢路径：先在生产按新 lock 带哈希建新环境并更新 systemd drop-in，再激活。
- `activate` 失败会自动切回旧包并重启；按实际结果记录 `failed`，该版本号作废。
- 成功后追加 `released` 行（同上格式，范围加 `health=passed;current=$N`），写 `releases/$N-<主题>-receipt.json`（版本、提交、owner、包 SHA、manifest SHA、previous/current、health、时间）。

### 6. 收尾（约 1 分钟）

```bash
curl -s https://huzhilawfirm.com/build-info.json     # version/source_commit = N/TARGET
curl -s -o /dev/null -w '%{http_code}\n' https://huzhilawfirm.com/health
"${OA_SSH[@]}" 'systemctl is-active sunhold-oa-api sunhold-oa-web; journalctl -u sunhold-oa-api --since "-5 min" -p err --no-pager | tail'
git tag -a "v$N" -m "OA $N" "$TARGET" && git push "$OA_GH" "v$N"
git push "$OA_GH" "$TARGET:main"      # 健康通过后自动快进 main 到本次发布提交，复用同提交门禁；回滚/失败/不健康时不执行
git fetch origin && git merge-base --is-ancestor origin/main origin/dev && echo MAIN_SYNCED
```

- 删除本次 staging 文件（只删自己上传的 `refs-$OWNER.json`、`$N-dir`）和已合入的临时分支。回执里记录包内文件清单的 SHA256 汇总（替代原来的 tgz SHA）。
- 汇报：版本、提交、健康结果、回滚点（上一版本）、待用户验收。不做线上业务写测试。

## 回滚

```bash
<运行环境 python> -B $E/tools/<工具版本>/native_runtime.py --env-file /opt/sunhold-oa/private/production-native.env \
    activate --package $E/packages/<上一版本> --current $E/current --expected-commit <上一版本提交>
```

包在 `flock -n` 里执行，队列追加 `rolled_back` 记录；有数据库迁移时按该版本记录的回滚说明处理。

## 部署失败时

激活失败、健康不过或卡在半途：先确认 `current` 实际指向（目标包则回滚，原基线则只验健康），记录 `failed`，向用户报告具体阻碍。需要后续盯守时用 `/loop 5m` 每 5 分钟只读检查，确认成功或回滚后删除该循环。

## 不再做的事（为提速删除）

- 不等 GitHub Actions：版本提交带 `[skip ci]`，发布以本地 pre-push 门禁和生产健康为准（用户 2026-10 决定）。
- 不默认合批、不做跨会话合并协调：多个就绪候选按队列各发各的。
- 不为补文档再发版本；交接文档随版本提交一起推送。

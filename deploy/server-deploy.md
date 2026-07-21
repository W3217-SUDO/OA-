# Linux 服务器部署与迁移

本目录提供单机 Linux Docker Compose 的生产基础方案。它适合先迁移到一台服务器；高可用、跨主机数据库和对象存储应改用托管服务或独立集群。

## 0. Git 源码与发布纪律

- 本地仓库是唯一源码源头，日常开发统一使用 `dev` 分支；测试服务器不得直接修改源码。
- 测试服务器裸仓库为 `/opt/sunhold-oa/git/sunhold-oa.git`，本地远程名为 `test-server`。代码必须先在本地完成 `verify-local.ps1`，提交后再执行 `git push test-server dev`。
- `.env.production`、数据库、附件、服务器密钥和运行日志不进入 Git。测试服务器私有配置保存在 `/opt/sunhold-oa/private/.env.production`，权限必须为 `0600`。
- 每次发布从裸仓库的 `dev` 分支创建新的只读版本目录，再复制私有环境文件、构建带时间戳的镜像并切换 `/opt/sunhold-oa/current`；不得直接在 `current` 或历史版本目录中改代码。
- `dev` 只用于开发和测试发布。正式生产上线前应另建受保护的 `main` 分支，并以经过完整验收的提交或标签发布。

本地首次配置及推送：

```powershell
git checkout dev
powershell -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1
git add -A
git commit -m "说明本次改动"
git push test-server dev
```

## 1. 前置条件

- 64 位 Linux 服务器，建议至少 4 核 CPU、8 GB 内存和独立数据盘。
- Docker Engine 与 Docker Compose v2。覆盖文件使用 `!reset`/`!override`，建议 Compose 2.24.4 或更高版本。
- 域名、DNS 和 HTTPS 入口。建议在主机上使用 Caddy、Nginx 或云负载均衡，将 HTTPS 请求转发到 `127.0.0.1:8080`。
- 防火墙只允许 SSH、HTTP 和 HTTPS。不要对公网开放 8000、9000、9001、5432 或 6379。

当前应用附件实际保存在 `uploads_data`；MinIO 尚未承载现有附件。迁移时必须同时备份 PostgreSQL 与 `uploads_data`，不能只复制 `minio_data`。

## 2. 准备生产配置

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

替换所有 `CHANGE_ME`。可用以下命令生成 URL 安全的随机值：

```bash
openssl rand -hex 32
```

`POSTGRES_PASSWORD` 必须与 `DATABASE_URL` 中的密码一致，`REDIS_PASSWORD` 必须与 `REDIS_URL` 中的密码一致。若密码包含 `@:/?#%` 等保留字符，URL 内必须使用百分号编码；使用随机十六进制密码可避免该问题。

生产环境首次创建数据库时，当前应用仍会创建已知的开发管理员密码。正式对外开放前必须登录并立即修改管理员密码。后续代码应改为一次性初始化变量并移除固定密码。

## 3. 校验并部署

```bash
docker compose --env-file .env.production \
  -f docker-compose.yml -f compose.prod.yml config --quiet

docker compose --env-file .env.production \
  -f docker-compose.yml -f compose.prod.yml up -d --build

docker compose --env-file .env.production \
  -f docker-compose.yml -f compose.prod.yml ps
```

对于仅供 1～3 人验收、内存为 2GB 的非正式测试服务器，可在上述命令最后追加
`-f compose.test-server.yml`。该覆盖文件把 Celery 固定为单并发，并收紧六个服务的
CPU/内存上限；它不适用于正式交付或高并发运行。

若测试机没有独立域名，可把 `deploy/nginx-test-server.conf.example` 安装到主机
Nginx 的 `conf.d`，使用独立的 `8088` 端口转发至回环地址 `127.0.0.1:8080`。
该入口仅用于验收，不提供 HTTPS；正式部署必须改用域名和 HTTPS。

生产覆盖文件只把 Web 绑定到主机，默认为 `127.0.0.1:8080`。API、数据库、Redis 和 MinIO 控制台仅在 Compose 内部网络可访问。HTTPS 入口应设置真实客户端 IP 转发头，并将请求转发到该地址。

基础镜像已锁定到审计时验证过的摘要，保证重建结果稳定。升级基础镜像时先在测试环境验证，再更新摘要。`API_IMAGE` 与 `WEB_IMAGE` 也应在接入镜像仓库后改成不可变版本或 digest。

### 3.1 使用 Caddy 开启 HTTPS

仓库提供 [`deploy/Caddyfile.example`](Caddyfile.example)，其中只有占位域名，不包含真实域名、证书或私钥。模板要求 Caddy 2.10 或更高版本，因为公网入口使用 `request_body` 将请求体限制为 21 MB；应用自身仍保留 20 MB 文件限制。反向代理上游固定为仅本机可访问的 `127.0.0.1:8080`，连接超时为 5 秒，等待上游响应头最多 120 秒。

启用前完成以下准备：

1. 为正式域名配置指向服务器公网地址的 DNS `A` 记录；只有服务器真实启用 IPv6 时才配置 `AAAA`，避免证书校验访问到错误地址。
2. 云安全组和主机防火墙允许公网访问 TCP 80、443；应用端口 8080 继续只监听回环地址。
3. 按 Caddy 官方安装方式安装并启用 systemd 服务，确认 `caddy version` 不低于 2.10。
4. 若 `/etc/caddy/Caddyfile` 已存在，先在仅 root 可读目录保存带时间戳的回滚副本。

复制模板并把 `legal.example.com` 替换为真实正式域名：

```bash
sudo cp -a /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.before-sunhold.$(date -u +%Y%m%dT%H%M%SZ)"
sudo install -o root -g root -m 0644 deploy/Caddyfile.example /etc/caddy/Caddyfile
sudo sed -i 's/legal\.example\.com/你的正式域名/g' /etc/caddy/Caddyfile
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

如果这是新服务器且原来没有 `/etc/caddy/Caddyfile`，跳过第一条备份命令。`你的正式域名` 必须替换为纯域名，不能保留中文占位文字，也不要加 `http://`。当站点地址是有效域名、DNS 已生效且 80/443 可从公网到达时，Caddy 会自动申请并续期公开可信证书，同时将 HTTP 重定向到 HTTPS；证书和账户资料由服务器上的 Caddy 数据目录管理，不复制进项目或交付包。

先验证本机上游，再验证公网 HTTPS、响应头和自动跳转：

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS "https://你的正式域名/health"
curl -I "https://你的正式域名/"
curl -I "http://你的正式域名/"
sudo systemctl --no-pager --full status caddy
sudo journalctl -u caddy --since '10 minutes ago' --no-pager
```

验收标准：两个 `/health` 请求成功；HTTPS 响应包含 `Strict-Transport-Security`、`X-Content-Type-Options`、`X-Frame-Options` 和 `Referrer-Policy`；HTTP 返回到同域 HTTPS 的重定向；Caddy 日志没有证书签发、上游连接或配置错误。模板中的 HSTS 初始有效期为 1 天，确认域名及所有入口稳定后再评估延长；不要在尚未验证全部子域 HTTPS 时增加 `includeSubDomains`。

若证书申请、代理或应用验收失败，不要修改或暴露 Compose 内部端口。恢复先前备份的 Caddyfile并重新校验、加载：

```bash
sudo install -o root -g root -m 0644 /etc/caddy/Caddyfile.before-sunhold.实际时间戳 /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

若新服务器此前没有 Caddy 配置，则停止 Caddy并保留 `127.0.0.1:8080` 上的应用栈用于排查；不要删除生产数据卷。回滚后再次检查 Caddy 状态和旧入口，确认服务恢复。

## 4. 源服务器备份

脚本会先记录原来正在运行的服务并进入维护窗口：停止 Web、API 和 worker，阻断新的业务写入；随后执行 PostgreSQL 逻辑备份，再停止 MinIO，获得与数据库处于同一维护窗口的上传附件和对象存储快照。PostgreSQL 不会停止。完成或异常退出时，`trap` 会按依赖顺序恢复备份前原本正在运行的服务。备份期间网页会暂时不可用，应提前通知用户并由外层反向代理显示维护页。

```bash
chmod +x deploy/backup.sh deploy/restore.sh
ENV_FILE="$PWD/.env.production" ./deploy/backup.sh
```

备份默认写入 `backups/<UTC时间>/`，包括：

- `postgres.dump`：可跨服务器恢复的 PostgreSQL 逻辑备份；
- `uploads_data.tgz`：现有业务附件；
- `minio_data.tgz`：MinIO 数据；
- `docker-compose.yml`、`compose.prod.yml`：未展开环境变量的原始无秘密配置，仅用于审计和版本对照；
- `runtime-versions.txt`、`service-images.txt`：Docker/Compose 版本与服务镜像清单；
- `SHA256SUMS`：覆盖上述全部配置、清单、数据库和卷归档。

备份目录权限为 `0700`，目录内文件为 `0600`。脚本不会写出已插值的 `docker compose config`，也不会复制 `.env.production`；因为已插值配置会包含数据库、Redis、MinIO 和应用密钥。请使用密码管理器、加密归档或云密钥服务单独备份生产密钥，切勿将其提交到 Git。不要降低备份目录权限，传输前还应使用独立密钥加密整个备份目录。

Redis 在当前架构中只承担 Celery broker 和运行时缓存，不是权威业务数据源，因此生产备份故意不包含 `redis_data`。恢复脚本会创建新的空 Redis 卷，避免迁移或灾难恢复后重新投递旧 Celery 队列并重复执行任务。权威业务状态来自 PostgreSQL、`uploads_data` 和 MinIO；如将来在 Redis 中引入必须持久化的业务状态，必须先完成数据职责拆分和幂等设计，再重新评估备份策略。

## 5. 传输并恢复到目标服务器

通过 `rsync`/`scp` 的加密通道传输项目、备份目录和生产密钥。在目标服务器先校验文件完整性，然后确保目标栈全部停止。

首次恢复到空服务器：

```bash
ENV_FILE="$PWD/.env.production" \
  ./deploy/restore.sh --start backups/20260101T000000Z
```

若目标卷已存在，脚本默认拒绝覆盖。确认现有数据可删除后才能显式执行：

```bash
ENV_FILE="$PWD/.env.production" \
  ./deploy/restore.sh --force --start backups/20260101T000000Z
```

`--force` 会删除并重建四个数据卷，是破坏性操作；其中 Redis 卷始终以空卷恢复。恢复脚本从合并后的 Compose 配置解析真实卷名，不依赖固定项目名称。

恢复脚本会先校验 `SHA256SUMS` 中的全部产物。备份内的两份 Compose 源文件和版本/镜像清单只用于核对来源版本；实际恢复始终使用目标服务器项目目录中的 Compose 文件与单独保管的 `.env.production`。恢复前必须确认目标代码版本、镜像清单与备份记录匹配，不能把备份目录中的配置直接覆盖到目标项目。

## 6. 切换前验收

1. `docker compose ... ps` 中所有服务均为运行或健康状态。
2. 经 HTTPS 访问 `/health`，确认反向代理与 API 正常。
3. 使用临时管理员会话登录并立即修改初始密码。
4. 抽查客户、合同、案件、财务数据数量。
5. 上传、下载并删除一份测试附件，确认 `uploads_data` 权限正常。
6. 验证 Redis/Celery worker 和任务自动规则。
7. 检查 Docker 日志、磁盘空间和系统时间。
8. DNS 切换前再做一次增量停机备份，并准备旧服务器回切方案。

## 7. 当前生产化边界

- 数据库仍由应用启动时 `create_all` 和自定义补列逻辑维护，尚未引入 Alembic。升级版本前必须先备份；接入 Alembic 后应在启动 API 前仅执行一次迁移。
- API 容器镜像尚未创建非 root 用户。覆盖文件已启用 `no-new-privileges`、去除 API/worker capabilities、只读根文件系统、资源限制和日志轮转，但后续仍应在 Dockerfile 中加入专用非 root 用户。
- 不要简单增加多个 Uvicorn worker/API 副本；当前应用生命周期内含业务规则循环，多副本会重复执行。应先把它迁移到单独 scheduler 或增加可靠的分布式锁。
- 备份只有在定期恢复演练通过后才算有效。建议至少每日数据库备份、每日附件备份，并将副本加密保存到另一台机器或对象存储。

# OA 腾讯云测试服务器连接说明

更新时间：2026-07-19

## 服务器身份

- 标注名称：**OA 腾讯云测试服务器**
- 腾讯云实例 ID：`ins-ggzft8rn`
- 地域：上海（`ap-shanghai`）
- 公网 IP：`101.35.24.73`
- 内网 IP：`172.17.0.14`
- 主机名：`VM-0-14-opencloudos`
- 系统：OpenCloudOS Server 9.4
- 配置：4 核、8GB 内存
- 系统盘：20GB，首次检查时可用约 14GB
- 登录用户：`root`

## SSH 连接

当前电脑已配置 SSH 别名：

```powershell
ssh oa-test-tencent
```

SFTP 与文件传输：

```powershell
sftp oa-test-tencent
scp 本地文件 oa-test-tencent:'/root/目标目录/'
scp oa-test-tencent:'/root/目标文件' 本地目录
```

SSH 配置文件：`C:\Users\Administrator\.ssh\config`

```sshconfig
Host oa-test-tencent
    HostName 101.35.24.73
    User root
    IdentityFile ~/.ssh/tencent_oa_101_35_24_73_ed25519
    IdentitiesOnly yes
    ConnectTimeout 10
    ConnectionAttempts 3
    ServerAliveInterval 30
    ServerAliveCountMax 3
    TCPKeepAlive yes
```

## SSH 密钥与密码

- 新增私钥：`C:\Users\Administrator\.ssh\tencent_oa_101_35_24_73_ed25519`
- 新增公钥：`C:\Users\Administrator\.ssh\tencent_oa_101_35_24_73_ed25519.pub`
- 新增公钥指纹：`SHA256:jKnqqb2wp5/ul9Cm2kVjLQuHzKQe/TJ97/lGU1cM3JQ`
- 服务器 ED25519 主机密钥指纹：`SHA256:RvqrYYNelPEzP71h8EjuecFRe/iCcJdOgEarHqWsMx0`
- 云端原有密钥 `skey-2t5b4dbl (gold)` 已保留，未被覆盖。

服务器当前 SSH 配置仅接受公钥认证，不接受密码认证。用户提供的 root 密码已保存到当前电脑 Windows 凭据管理器，作为腾讯云控制台/应急用途：

- 凭据目标：`OA测试服务器-腾讯云-101.35.24.73`
- 用户名：`root`
- 密码明文不写入项目或 Markdown。

检查凭据记录：

```powershell
cmdkey /list:OA测试服务器-腾讯云-101.35.24.73
```

## 首次接入记录

- 腾讯云 TAT 自动化助手版本 `1.2.1` 在线。
- 通过 TAT 临时命令把本机公钥追加到 `/root/.ssh/authorized_keys`，未覆盖原密钥、未重启实例、未开放密码认证。
- 已使用新密钥实际登录并确认身份为 `root`。
- 腾讯云 API Secret 仅在当前进程临时使用，未写入文件、文档、环境配置或凭据管理器。由于 Secret 曾出现在聊天记录中，应尽快在腾讯云访问管理控制台轮换。

## OA 部署资源判断

- 4 核、8GB 内存能够承载当前 OA 六容器测试环境；首次检查时可用内存约 6.4GB。
- 服务器并非空机：已有 `MT5 Signal Sharing API Service`，目录 `/opt/mt5-signal-api`，由 Python 3.11 虚拟环境和 systemd 运行，直接监听公网80端口，检查时约占 208MB。MariaDB 10.11 正在运行，业务数据库名为 `mt5_signals`，检查时约占 247MB；不得覆盖、停用或复用该数据库。
- 当前未安装 Docker，也未发现 PM2 或运行中的容器。腾讯云 TAT、云监控、安全代理、SSH 和系统定时任务正常运行。部署 OA 时应新建独立目录、独立 Compose 网络及 PostgreSQL/Redis/MinIO 数据卷，Web 绑定 `127.0.0.1:8080`，避免占用现有80端口。
- 当前系统盘仅 20GB、可用约 14GB，不适合长期保存构建缓存、PostgreSQL、MinIO 附件和备份。正式上传并启动 OA 前，建议系统盘扩容至至少 60GB，推荐 80GB。
- 部署时只允许上传 `scripts/export-delivery-source.ps1` 生成的脱敏白名单包，不上传真实 `.env`、私钥、数据库备份、附件、日志或受保护的 `sfhc/` 目录。

## 快速健康检查

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 oa-test-tencent "echo SSH_OK; hostname; whoami; free -h; df -hT /"
```

正常结果应包含主机名 `VM-0-14-opencloudos` 和用户 `root`。

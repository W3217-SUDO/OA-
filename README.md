# 思法汇成法律服务机构管理系统（重构版）

网页端优先的本地 Docker 工程，API 同时面向网页端、后续 Taro 小程序和 Dify 智能体。

## 本地启动

### 不使用 Docker（当前开发方式）

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

网页端为 `http://127.0.0.1:5173`，FastAPI 文档为 `http://127.0.0.1:8000/docs`。
本地数据库使用 SQLite 文件；后续 Docker/服务器环境通过 `DATABASE_URL` 自动切换 PostgreSQL。

### 一键本地验收

先保持本地 API 正在运行，然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1
```

该命令会依次执行前端生产构建、Python 语法检查、265 菜单/220 叶子页面结构覆盖、17 组 API 端到端业务流与零残留清理，并验证 Docker Compose 配置。

明日交付候选版在 Docker 启动后使用更严格的交付门禁：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-delivery.ps1
```

Linux 服务器正式启动前还必须使用真实的私有环境文件运行：

```bash
./deploy/preflight-production.sh .env.production
```

该预检会拒绝 `CHANGE_ME`、默认管理员密码、过短密钥、宽松环境文件权限和生产演示数据开关；不会打印秘密值。

### 使用 Docker（已完成本机验证）

1. 在 BIOS/UEFI 中开启 CPU 虚拟化；AMD 主板通常叫 `SVM Mode`。
2. 启动 Docker Desktop。
3. 在项目目录运行 `powershell -ExecutionPolicy Bypass -File .\scripts\docker-preflight.ps1`。
4. 通过后运行 `powershell -ExecutionPolicy Bypass -File .\scripts\start-docker.ps1`。
5. 打开 `http://localhost`；README 中的本地演示账号只允许开发机使用，生产环境必须通过私有 `.env.production` 设置一次性强密码。

启动脚本会在缺少 `.env` 时从 `.env.example` 创建本地配置，并执行 `docker compose up -d --build`。附件保存在独立的 `uploads_data` 数据卷中，PostgreSQL、Redis、MinIO 和附件均不会因普通容器重建而丢失。

本机已验证 `postgres`、`redis`、`minio`、`api`、`worker`、`web` 六个服务能够完整启动。网页入口为 `http://127.0.0.1/`，API 健康检查为 `http://127.0.0.1:8000/health`。

服务器迁移使用 `.env.production.example`、`compose.prod.yml` 和 `deploy/server-deploy.md`。数据库与附件备份/恢复脚本位于 `deploy/backup.sh`、`deploy/restore.sh`；正式迁移前必须在 Linux 服务器替换全部秘密并完成一次恢复演练。

接口文档：`http://localhost:8000/docs`；MinIO 控制台：`http://localhost:9001`。

> 初始账号仅用于本地开发，上服务器前必须修改密码和 `SECRET_KEY`。

若预检显示 `Firmware virtualization: False`，说明 Windows 功能虽然安装完成，但 BIOS 的 SVM/VT-x 仍未开启；这一步不能在网页项目或 Docker 配置中代替完成。

当前实现范围与剩余工作见 [`docs/功能实现清单.md`](docs/功能实现清单.md)。

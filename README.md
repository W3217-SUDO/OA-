# 思法汇成法律服务机构管理系统（重构版）

律所 OA 系统的网页端重构：以原申浩/沪知 OA 的业务规则和数据为依据，用 FastAPI + React 重新实现客户、合同、案件、知识产权、调查取证、财务、人事、用印和智能体等业务。API 同时供网页端、后续小程序和智能体调用。

- 线上地址：<https://huzhilawfirm.com>
- 源码仓库：<https://github.com/W3217-SUDO/OA->（`dev` 测试集成，`main` 已上线版本）
- 旧系统 C# 源码：[脱敏只读归档](legacy/csharp/README.md)（含 GD 两个项目与 SH 源码片段，不参与新系统构建或部署）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 19、TypeScript、Vite 7、Ant Design 6（Node.js 22） |
| 后端 | FastAPI、SQLAlchemy（Python 3.12） |
| 数据 | 本地 SQLite；服务器 PostgreSQL、Redis 缓存、附件存储（MinIO/OSS） |
| 智能体 | 个人与案件智能体、MCP 工具、技能库（DeepSeek 运行时） |
| 生产运行 | systemd + Nginx，不可变运行包（非 Docker） |

## 目录

```text
apps/admin-web/     前端源码（src/）与前端单元测试（tests/）
apps/api-server/    后端源码（app/）、后端测试（tests/）、数据维护脚本（scripts/）
scripts/            质量门禁、运行包构建、数据迁移与本地启动脚本
tests/quality/      门禁与发布工具自身的测试
deploy/             生产运行配置、Nginx 片段、备份与恢复脚本
docs/               业务资料、功能清单、交接记录和项目技能（docs/skills/）
frontend/ backend/ aiagent/   只放导读 README，不参与运行；真实代码在 apps/
```

详细的代码阅读路线见 [docs/项目结构导览.md](docs/项目结构导览.md)。

## 本地开发

需要 Python 3.12 和 Node.js 22（版本见 `.python-version`、`.nvmrc`）。

### macOS / Linux

```bash
# 1. 后端依赖（按锁文件带哈希安装）
cd apps/api-server
python3.12 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock -r ../../requirements-dev.lock

# 2. 前端依赖
cd ../admin-web
npm ci

# 3. 启动（两个终端）
cd apps/api-server && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd apps/admin-web && npx vite --host 127.0.0.1 --port 5173
```

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

启动后：网页 <http://127.0.0.1:5173>，接口文档 <http://127.0.0.1:8000/docs>，健康检查 <http://127.0.0.1:8000/health>。本地默认使用 `apps/api-server/legal_platform.db`（SQLite，已被 git 忽略）；设置 `DATABASE_URL` 即切换到 PostgreSQL。前端开发服务器把 `/api` 代理到 `VITE_API_PROXY_TARGET`（默认 `http://localhost:8000`）。

也可以用 Docker Compose 一次起全套（PostgreSQL、Redis、MinIO、API、Worker、Web）：复制 `.env.example` 为 `.env` 后运行 `docker compose up -d --build`，网页入口 <http://127.0.0.1/>。

## 提交与推送

- 所有改动先进 `dev`；`main` 只做快进，代表已上线、验证没问题的代码。不在 `main` 上直接提交，不强推。
- 推送 `dev`/`main` 时，pre-push 门禁自动运行（约 1 分钟）：后端静态检查、门禁工具测试、前端单元测试、前后端接口对照、菜单覆盖、后端单元/结构/回归测试。工作区必须干净，失败就修，不绕过。
- 安装门禁（每个克隆一次）：

  ```bash
  sh scripts/install-quality-hook.sh          # macOS / Linux
  ```

  Windows 用 `scripts\setup-local.ps1 -InstallQualityHook -QualityHookOnly`。推送前设置 `OA_QUALITY_PYTHON`（装好依赖的 Python 3.12）和 `OA_QUALITY_NODE`（Node.js 22）的绝对路径。
- 不提交 `.env`、密钥、数据库、附件、`node_modules` 或构建产物。

## 发布上线

正式发布只发生产服务器（`huzhilawfirm.com`），流程、命令和服务器信息见发布技能 [docs/skills/oa-fast-deploy/SKILL.md](docs/skills/oa-fast-deploy/SKILL.md)。要点：

- 按生产队列串行，一次发布只推一次 `dev`、只领一个版本号（沿 `1.1.x` 递增）。
- 本地构建不可变运行包，上传后封存并切换；失败自动回到上一版本，旧包保留用于回滚。
- 生产健康通过后，`main` 快进到本次发布提交。
- 测试服务器（`150.158.3.104`）已暂停，不再部署。

## 文档

| 文档 | 用途 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 开发规则与业务红线（AI 会话开始前必读） |
| [docs/功能实现清单.md](docs/功能实现清单.md) | 功能实现范围与状态 |
| [docs/迁移交接与当前状态.md](docs/迁移交接与当前状态.md) | 最近的交接记录 |
| [docs/skills/problem-remediation/SKILL.md](docs/skills/problem-remediation/SKILL.md) | 问题表逐行定位、整改与验收方法 |
| [docs/skills/oa-fast-deploy/SKILL.md](docs/skills/oa-fast-deploy/SKILL.md) | 正式发布流程 |
| [docs/新电脑恢复与继续开发.md](docs/新电脑恢复与继续开发.md) | 换电脑后的恢复步骤 |
| `docs/原OA*`、`docs/旧系统*` | 原系统业务逻辑、数据库与页面对照资料 |

2026-10-20 之前的问题台账、逐行证据和历史交接已从 `dev` 移除，可从标签 `archive/before-cleanup-20261020` 取回，例如：

```bash
git show archive/before-cleanup-20261020:docs/迁移交接与当前状态.md
```

## 安全

- `.env.example` 里的账号密码只用于本地开发；服务器使用私有环境文件，上线前必须替换全部默认密码和 `SECRET_KEY`。
- 生产环境预检：`./deploy/preflight-production.sh .env.production`（拒绝默认密码、弱密钥和宽松的文件权限，不打印秘密值）。
- 数据库与附件备份/恢复脚本：`deploy/backup.sh`、`deploy/restore.sh`。

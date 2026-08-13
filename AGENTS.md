# Codex 项目工作纪律

本文件适用于整个仓库。新的 Codex 会话开始工作前必须先阅读本文件、`README.md`、`docs/功能实现清单.md` 和 `docs/迁移交接与当前状态.md`。

## 项目目标

- 以申浩律师协作平台原系统、已归档服务器源码和数据库关系为业务证据，完成网页端本地重构；原页面只用于理解入口和操作场景，不再作为逐像素视觉复刻目标。
- 功能覆盖必须完整：旧系统现有业务页面中的全部有效按钮、查询条件、弹窗、明细、导入导出、打印、上传下载、审批动作、状态变化、权限限制、数据范围和异常阻断，都必须在新系统中有真实可用的对应实现；允许重新设计页面布局和交互表达，但不得因视觉重构遗漏功能或改变业务含义。
- 后端使用 FastAPI，前端使用 React + TypeScript，Docker Compose 负责 PostgreSQL、Redis、Celery、MinIO、API、Web。
- REST API 必须可供后续微信小程序和 Dify 智能体复用。
- “全部完成”必须由逐模块业务闭环、逐角色权限、逐状态流转、逐阻断规则、逐按钮真实行为和逐接口证据证明，不能仅凭菜单能打开或测试通过宣称完成；页面颜色、图标、间距和旧站布局不作为单独交付标准。

## 不可破坏的业务规则

- `admin` 是最高权限：全部菜单、全所数据、全部字段；任何配置和旧会话都不能降低管理员权限。
- 原系统以对照为主；允许创建带任务专属 `CODEX-*` 前缀的测试数据，并且只能编辑、保存、审批、上传、下载、状态流转和删除本任务自己创建的数据。严禁修改、审批、删除、覆盖或破坏任何已有数据；无法确认归属的一律不动。闭环结束后必须精确清理本任务创建的数据、附件和临时文件，并回查零残留。

- 测试数据写入规则：用户已允许本项目创建测试数据。每次测试必须使用本轮唯一的 `CODEX-*` 标识，创建前记录唯一标识和记录 ID，测试后核对业务记录、审批/流水、附件及临时文件并精确清理为零；不得借测试修改或删除已有数据。
- 本地测试产生的数据必须在测试结束后清理；不得删除用户已有数据。
- 任务规则必须保留：超过 30 天拒绝、交接后可以重新开始、交接满 5 天未开始自动完成。
- 专用业务流程不能被通用记录接口绕过，包括合同审批、案件归档、用印、财务、人事和证物生命周期。

## 开发质量要求

- 开发与发布分支固定为 `dev`：所有后续修改、提交、测试服务器发布均直接在 `dev` 上完成；不得再创建或使用其他开发分支作为发布源。项目版本基线从 `1.0.0` 开始，后续按语义化版本递增。
- 本项目已启用 CodeGraph：每次开始涉及代码的开发、审查、修复、前后端比对、页面跳转追踪或影响范围分析前，必须先运行 `codegraph status`，存在待同步内容时运行 `codegraph sync`，再使用 `codegraph explore` 查询相关页面、函数、接口、调用链和 blast radius 后修改代码；每次代码修改后必须再次运行 `codegraph sync`。只有 CodeGraph 无法解析或明确无结果时，才使用 `rg` 和直接文件读取补充。交接记录须写明 CodeGraph 结论，但不得把代码图谱当作业务验收证据，仍须完成构建、接口测试和浏览器验收。
- 不允许死按钮、假弹窗、硬编码成功提示、伪造图表数据或“暂无数据”假柱状图。
- 不得用“入口存在”代替功能完成。每个旧站按钮都要建立对应关系，并至少证明：出现条件正确、权限正确、输入校验正确、调用真实接口、成功状态正确、失败提示正确、数据实际落库或文件实际生成、后续状态和关联页面同步更新。
- 业务关联字段（如调查/线索编号、案号、合同号、客户或权利人）不得只作为展示文本；存在可查看的关联对象时必须可点击进入真实只读详情，目标不存在或无权限时必须明确提示。修复其中任一入口时，必须同步审计并统一修复同模块及其他模块中语义相同的关联入口，不能只处理截图或当前页面中的单一字段；列表、抽屉、详情和关联查询结果中的同一字段均按此规则执行。每次新增或修复同类关联入口，都要补浏览器点击证据、精确清理临时测试数据，并更新交接记录。
- 任何修复涉及可点击字段、点击命中区域、表格列宽、滚动容器、固定列、浮层或层级时，必须同步审计所有使用相同布局模式或相同语义字段的页面；特别是宽表右侧操作列不得遮挡左侧关联字段。不得仅针对当前截图、当前路由或单个组件修补。每个受影响入口均须确认可点击目标实际可达，并保留浏览器验证证据；没有可用数据时应明确记录为“已部署、仍未证明”。
- 按钮文案必须与实际文件格式和行为一致，例如 CSV、ZIP。
- 页面路由必须匹配菜单语义，深层路由应自动展开父级菜单。
- 改动后至少运行：前端生产构建、Python 编译、菜单覆盖审计、API 冒烟测试。
- 完整验收命令：`powershell -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1`。
- Docker 改动后重新构建受影响服务，并检查 `docker compose ps` 和最近日志。
- 继续维护 `scripts/audit-menu-coverage.py` 与 `scripts/smoke-api.py`，新增功能必须补覆盖。

## 文件和数据安全

- 保留用户已有改动，不使用 `git reset --hard`、递归删除或覆盖不明文件。
- `.env`、API Key、服务器密钥和原系统密码不得提交到代码或普通文档。
- 工作区中的 `sfhc/` 属于另一个项目且含保密资料，不得读取、修改、复制进本项目迁移包。
- 生产部署前必须更换默认密码、`SECRET_KEY`、MinIO 密码，并启用 HTTPS。
- 测试站页面验收需要认证时，Codex 应在用户已明确授权的范围内自行使用测试凭据登录并继续验证；不得将密码、令牌或任何秘密写入仓库文件、交接文档、提交信息或回复内容。
- 本地重构系统与用户授权的测试系统，Codex 可自行打开、刷新、导航和操作页面以执行验收；常规页面访问、登录、任务自建 `CODEX-*` 测试数据创建、状态流转和精确清理无需重复向用户确认。原系统仅允许操作本任务自己创建且可确认归属的 `CODEX-*` 测试数据；浏览器或平台自身的安全策略、外部发布、生产数据、已有业务数据与任何未授权的敏感传输仍不得绕过。
- 页面验收遇到浏览器标签失效、卡住或接管不同步时，Codex 必须先自行恢复：弃用失效标签对象，重新获取或新建可控验收标签并回到目标页面；不得把常规浏览器恢复工作转交给用户。仅当浏览器能力本身不可用且已完成可用的恢复步骤后，才可说明该外部阻断。

## 交接纪律

- 测试服务器发布纪律：用户已授权测试服务器部署后，每完成一项字段或功能修改，必须先完成该项的定向验证、Git 提交，再自动部署到测试服务器；无需等待用户再次要求部署。部署后检查服务健康状态并在测试站完成对应验收。不得把未部署的修改标记为已完成或已验证。
- 当前固定部署目标：本会话后续所有 OA 修改均与 Terra 使用同一个 `dev` 分支，并直接在测试服务器非 Docker `dev` worktree `/opt/sunhold-oa/worktrees/codex-resume-20260731` 完成、验证、提交并部署；当前统一版本号记为 `1.0.2`。非 Docker 服务为 `sunhold-dev-web`（公网前端 `http://150.158.3.104:8089/`，本机 `0.0.0.0:8089`）和 `sunhold-dev-api`（本机 `127.0.0.1:8001`）。不要部署到 Docker 容器链路 `127.0.0.1:8080/8000`，不要再切换到 `release-v*` detached worktree，也不要把 `8088` 当作主要直连验证入口。每次提交后重启 `sunhold-dev-api` 与 `sunhold-dev-web`，并验证 `http://150.158.3.104:8089/`、目标页面和后端健康检查。

- 每轮结束更新 `docs/功能实现清单.md` 或 `docs/迁移交接与当前状态.md`，明确已完成、已验证、仍未证明三类状态。
- 不得把“未发现问题”写成“业务逻辑已完成”。最终交付按合伙人确认的业务蓝图验收角色责任、流程、权限、状态、审批、阻断规则和数据闭环；视觉仅需清晰、可用、风格统一，不要求与旧站完全一致。
- 新电脑恢复后先运行 Docker 健康检查与 15 组冒烟测试，再继续功能开发。

## 当前会话补充规则

- 浏览器验收页面或 iframe 出现卡住、超时、标签失效或接管不同步时，立即弃用旧标签对象并重新打开可控页面；旧系统与本地开发系统都要重新定位到当前目标页面后再继续，不反复操作已经失效的标签。
- 申浩旧系统用于业务对照，并仅允许创建和操作本任务自己的 `CODEX-*` 测试数据；已有数据及无法确认归属的数据严格只读。本地开发系统使用 `dev` 分支作为唯一修改目标。
- 当前会话不再等待单独发布指令：每次修复均在非 Docker 测试服务器 `dev` worktree 内完成，验证通过后立即提交、重启 `sunhold-dev-api`/`sunhold-dev-web` 并部署到 `http://150.158.3.104:8089/`。如需本地辅助验证，可以先本地复现，但最终仍必须同步到该非 Docker 测试系统。

## 主会话项目经理职责

- 主会话只担任项目经理，不直接编写或修改业务功能代码；功能盘点、旧站与本地双页面对照、实现、测试、验收记录和 Git 提交均派给 4 个独立 Codex 会话线程执行。
- 主会话负责按模块和顺序拆分任务、维持 4 个会话持续工作、监督进度、检查浏览器对照证据与测试结果、发现遗漏后立即退回原会话补做，并在一个模块完成后立刻向该会话续派下一个模块。
- 每个会话必须同时检查申浩旧系统页面和本地开发页面；需要写入才能验证的动作只能使用本任务自己的 `CODEX-*` 数据。每个按钮、子页面、弹窗、跳转、字段、权限、状态、异常提示和数据闭环都要逐项对照。发现本地缺失立即修改并回到两个页面复验；本地已有的额外功能或字段保留，不因旧站没有而删除。
- 4 个会话应从不同且边界清晰的模块并行推进，避免修改同一文件；存在共享文件冲突风险时，由主会话重新分配边界。会话完成当前任务后不得自行停工，主会话应续派下一项未完成模块。
- 子代理模型规则：为控制 token 消耗，后续新派的子代理默认使用 `gpt-5.6-terra`；只有任务复杂度明确需要更高能力时，主会话才可例外升级模型，并在派工记录中说明原因。正在运行的代理不因该规则被强制中断。
- 主会话不得以自己的检查代替会话交付；验收必须包含旧站页面证据、本地页面证据、真实接口或数据落库证据、失败/阻断路径、临时数据精确清理、定向测试、完整构建和 Git 提交号。
- 任何会话遇到浏览器卡住或标签失效，必须自行重新打开旧系统与本地系统目标页面继续，不得等待用户处理；不得请求绕过安全边界或要求用户代为完成常规审批。
- 独立会话不得在完成一个小步骤、遇到首个失败或形成阶段结论后自行停止。准备结束当前轮次前，必须先向主会话项目经理汇报：已完成的可核验证据、尚未完成的清单、测试数据清理状态、测试/构建/Git 状态、当前阻碍和建议的下一步；主会话验收后给出下一步计划或明确允许阶段停止。
- 主会话收到汇报后必须及时判断“通过、补证、返工或续派”，给出范围清晰的下一步计划，并继续监督执行；不得让会话因没有后续指令而空闲。只有模块完整验收通过或主会话明确要求暂停时，对应会话才可停止。
- 浏览器标签必须及时回收：每个独立会话原则上只保留当前任务所需的旧系统只读标签和本地开发标签各 1 个；切换子页面优先在现有标签内导航，不得为每次点击无限新建窗口或标签。标签失效、超时、完成当前证据采集或不再使用时，必须立即关闭；重新打开页面前先清理本会话遗留的无用标签，并在阶段汇报中说明当前保留标签数量。
- 独立会话标题必须反映当前正在完成的模块、子功能和状态，格式建议为 `A/B/C/D｜模块·当前子功能｜进行中/待验收/已完成`。主会话每次续派、退回、进入待验收或确认完成时，都要同步修改对应会话标题，确保侧边栏可直接看到实时进度，不得长期保留旧任务名称。
- 共享工作树的 Git 提交必须串行执行。各会话完成开发、测试和清理后，先向主会话汇报并列出仅属于本线程的精确文件清单，等待主会话发放提交时段；未获准时禁止执行 `git add` 或 `git commit`。获准后只能使用 `git add -- <明确文件>`，禁止 `git add .`、`git add -A` 或提交其他会话文件；提交后立即回报提交号与 `git status --short`。主会话确认提交结束后才可向下一个会话发放时段。
- 四线程的完整目标、派工格式、六项汇报、通过/补证/返工/续派判定、20 分钟卡点升级、Git/浏览器/共享后端文件排队规则，以 `docs/superpowers/plans/2026-08-01-fast-full-site-parity-plan.md` 为当前执行协议。主会话每次续派前必须按该协议给出明确入口、允许修改范围和验收出口；子会话不得自行扩大范围或在汇报后空闲等待。
- 浏览器验收不再采用全局独占排队。A/B/C/D 各自固定并维护旧系统与本地开发标签各 1 个，可同时对照；旧系统写动作仅限本任务自建 `CODEX-*` 数据。每个会话必须登记并只操作自己的两个标签 ID，不得导航、关闭或复用其他会话标签，也不得为子页面继续增加标签。

## 8089 部署与版本号规则

- 本会话所有已验证修改必须部署到测试服务器公网入口 `http://150.158.3.104:8089/`，对应非 Docker 服务 `sunhold-dev-web` 和 `sunhold-dev-api`。
- 部署必须按版本号管理，不能无版本覆盖。每次发布前读取当前版本号，发布后在汇报中写明本次部署版本号、部署目录、服务名、重启结果和健康检查结果。
- 当前 8089 非 Docker 发布目录以服务器实际运行的 systemd 配置为准；部署前必须用 `systemctl cat sunhold-dev-web`、`systemctl cat sunhold-dev-api` 或等效命令确认真实 `WorkingDirectory`，不得凭记忆部署到旧 worktree。
- 当前已识别的 8089 发布树为 `/opt/sunhold-oa/worktrees/release-v1.0.32`；如 systemd 指向变化，以最新 systemd 配置为准，并在回复中说明。
- 前端版本号以 `apps/admin-web/package.json` 为准；涉及发布时必须确认版本号。若需要递增版本，必须同步 `package.json` 与 `package-lock.json`，并确保构建通过后再部署。
- 每次部署后必须执行并汇报：定向测试、前端生产构建、后端相关测试或 `py_compile`、`git diff --check`、`systemctl restart sunhold-dev-api sunhold-dev-web`、服务 active 状态、`/health`、目标页面 HTTP 200。
- 不能把未部署、未重启、未健康检查或未打开 8089 验证的修改说成“服务器已解决”。

## Excel and Legacy Reference Rule

- Excel issue workbooks are evidence backlogs, not the project objective or the agent's sole operational state. The active conversation goal defines the current objective and scope.
- When the active goal explicitly includes an Excel batch, process exactly one selected row at a time. Before implementation, read the row text and inspect every screenshot anchored to that same row, including any old-system comparison screenshot.
- `http://150.158.3.104:8091/` is the legacy-system reference only. It may be inspected to establish business behavior and layout, but legacy source code must never be modified. The sole implementation target is the new OA system on the `dev` worktree and its `8089` deployment.
- For each explicitly selected row, record: Excel row, screenshots examined, legacy reference path and observation, new-system root cause, changed files, focused tests, build result, version/commit, 8089 deployment, and Codex in-app-browser acceptance result.
- Do not start the next selected Excel row until the current one has either passed the required browser acceptance or has been explicitly recorded as blocked with concrete evidence and a next action.
- Never infer that a particular workbook, worksheet, or row is the current task solely from a prior handoff, ledger entry, browser tab, or local artifact. Resume Excel work only when it is within the active conversation goal or the user explicitly selects it.

## Daily Excel Acceptance Discipline

## Mandatory Screenshot-First Workflow

- For every Excel issue row, inspect the row text and every image anchored to that same row before code search, implementation, or completion judgment. This includes old-system comparison images, annotations, and rework screenshots.
- Save or otherwise retain a readable local copy of each inspected image and record which images were examined in the row ledger. If an image cannot be read, the row remains unfinished until it is rendered or inspected successfully.
- Only after the text-and-image review may the agent reproduce the behavior in the new system, locate the root cause, modify the new-system worktree, run focused checks, and perform Codex in-app-browser acceptance. Source review or a passing test alone never replaces screenshot review or browser acceptance.
- After fixing a row, repeat the same browser path and compare the observed result against the row text and screenshots. Record the result immediately before moving to the next row.

## Current-Session Excel Execution Rule

- For every current and future Excel issue, the agent must first read the issue text and inspect all screenshots embedded on that exact row. Screenshot annotations and old-system comparison screenshots are requirements, not optional context.
- Locate and change only the new OA system source in the active `dev` worktree. The legacy system is read-only evidence and must never be used as the implementation target.
- Work strictly one row at a time: reproduce in the new system, identify the root cause, implement, run focused regression and build checks, then use the Codex in-app browser to accept the exact reported path. Do not begin the next row before recording the browser result in the ledger.
- A row may be marked complete only when its screenshot requirements, browser result, changed files, tests, and residual risk have all been recorded. Code inspection, a unit test, a build, or deployment alone is insufficient.

## Excel State Continuity Rule

- During an explicitly active Excel batch, the row-by-row acceptance ledger records evidence and next actions for that batch. It does not replace the active conversation goal, the source-code parity plan, or the implementation roadmap.
- Before work on an explicitly selected Excel row, read its ledger entry and identify the required evidence, test-data identifier, and next unchecked action. Outside an active Excel batch, continue from the active conversation goal and the source-code parity plan.
- Update the ledger immediately after every material outcome: screenshot review, reproduction, code change, test run, browser acceptance or rejection, test-data creation, and test-data cleanup. No agent may move to another row while its own row has an unrecorded result.
- Parallel work is permitted only as one agent per distinct Excel row. Each agent must state its assigned row, read the ledger before acting, use a unique `CODEX-*` test-data prefix for that row, and must not edit another row's ledger entry. The project manager alone integrates outcomes, resolves shared-file conflicts, and advances the canonical next row.
- On an interrupted, resumed, or new session, first reconcile the ledger with `git status`, active browser page, and test-data inventory. If they disagree, record the discrepancy as pending and resolve it before claiming progress.

- Only when the active conversation explicitly starts an Excel issue batch, locate the selected workbook and worksheet, then continue from the row explicitly selected by the user or recorded as the next row for that batch. Do not automatically choose a workbook, batch, or row from the calendar date, handoff text, browser page, or old ledger state.
- For each row in an explicitly active batch, inspect its text and every embedded same-row screenshot before deciding whether the new system has an issue. A source-code review alone never closes a row.
- Use the Codex in-app browser for the final acceptance path on `http://150.158.3.104:8089/`. Reproduce the reported behavior first; if it fails, fix the new-system source, run focused regression/build/deployment checks, then repeat the same in-app-browser path before marking the row accepted.
- Update the row-by-row acceptance ledger immediately after each browser outcome. Record either `已验收` with the exact page and observed result, or `未通过/待修复` with the reproduced behavior and next action. Do not carry an unrecorded result into the next row.

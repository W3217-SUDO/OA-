# GitHub 技能连接器后端整改定位

## 1. 清单原文
- 独立新增需求，无工作簿、工作表或行号。
- 原始问题（逐字）：这个ai助手要做一个技能的连接器 跟codex一样仿照
- 补充说明（逐字）：然后技能可以去github上下载
- 返工意见：无。状态：本地实现，待用户验收。

## 2. 截图分析
- 原图由主会话逐图记录：AI助手新对话、底部技能选择、个人AI空间入口；后端不根据截图推断新增业务权限。
- 本后端子任务不涉及玩偶尺寸，前端另有责任人。

## 3. 旧系统实现
不适用：新增需求，旧系统不存在。

## 4. 新系统当前实现
### 前端
AI助手使用 WorkspaceSkill 和个人技能CRUD；连接器UI由C线程实现。
### 后端
`app/user_agent_skills.py::normalize_custom_skill` 限制名称64、描述500、指令6000字符；`core/documents.py::_user_agent_skill_store/_save_user_agent_skills` 按用户名哈希存储并审计；`core/permissions.py::_agent_skill_for_identity` 阻断非本人或停用技能。`areas/personal_agent/router.py` 已挂载AI空间路由，新增端点必须保留。
### 数据库
复用 SystemConfig.value 中 owner_username/skills，无迁移；来源保存在原source字段。不能改变权限或运行仓库代码。

## 5. 需求与当前实现差距
|编号|用户要求|当前差距|落点|
|---|---|---|---|
|D1|GitHub下载|只有手工上传|安全下载和SKILL.md解析|
|D2|技能连接器|没有预览与安装|预览摘要、确认后重取校验、个人库持久化|

## 6. 精确修改清单
- [ ] 生产连通性补证后局部整改（候选008a）：PM真实只读核验阿里云HTTPX直接raw间歇TLS失败，官方Contents API连续3次200且同SHA。`github_agent_skills.py`下载固定生成`https://api.github.com/repos/{owner}/{repo}/contents/{path}`，ref作为HTTPX独立params编码，Accept固定`application/vnd.github.raw+json`。用户URL白名单不变、无认证/自定义header、TLS校验与no redirect/trust_env=False、128KiB与20秒总限时保留；不是fallback或代理。测试新增特殊ref/path编码检查，既有固定目标断言更新。只在候选clone修改，不写真实业务库或服务器环境。
- [x] `app/github_agent_skills.py`：只接受固定GitHub HTTPS主机，blob/tree/raw/根仓库URL规范化为SKILL.md；固定raw下载、禁止重定向、超时/大小限制；YAML safe_load解析元数据，保留正文且超过6000明确拒绝。
- [x] `areas/personal_agent/router.py`：增加preview/install接口；要求认证，安装重取SHA256匹配，复用个人库、30个上限、同来源幂等，保留AI空间和旧CRUD。
- [x] `tests/regression/github_agent_skills_test.py`：纯函数和MockTransport隔离测试，无真实业务数据。
- [x] `app/user_agent_skills.py::normalize_custom_skill/custom_skill_public`：PM审查发现启停PATCH重新normalize会丢失sha256；保留GitHub来源合法SHA256并公开，防止启停后的同源安装误报版本冲突。补纯函数回归。
- 不涉及数据库结构迁移；既有自定义技能权限及会话边界保留。
- [x] 安全复核补充：下载增加20秒总限时，避免逐次读取超时被慢速流绕过；同来源幂等还核对已存名称、描述、正文，已编辑副本不得因保留原摘要冒充未修改的GitHub版本。
- CodeGraph status/explore均command not found；按规则使用rg补充定位。最新基线16882118。

## 7. 验证清单
原文GitHub下载映射到固定主机读取；连接器映射到认证preview/install。测试非法URL、编码路径、redirect、超限、frontmatter、网络失败、内容变更；公开小文件真实只读下载。生产构建由PM/C统一执行。浏览器及真实业务写测试不执行，用户验收预览/安装/刷新/选择/删除，保持待验收。定时、业务审批、附件不涉及。未创建测试业务数据。

## 8. 实施记录
2026-10-13 生产下载补证整改已完成：候选`/tmp/oa-release-candidate-20261013-FSJmPo`中只改`app/github_agent_skills.py`、`tests/regression/github_agent_skills_test.py`和本记录。官方Contents API为唯一下载目标，ref独立params编码，用户来源URL与摘要语义不变，保留全部限制与权限链。11项测试、相关ruff与py_compile通过，特殊`release+&=1` ref及含中文/#/&路径编码验证通过。候选函数本机真实GET成功（名称skill-installer、正文2881字符、SHA256与原文件一致）；同生产已有解释器、相同HTTPX参数远端只读GET HTTP200/3240字节/frontmatter真实、SHA256 `83b31cffb2552a923f4152f0338bea548274accc5489d151a95bced8e7bcfb74`。CodeGraph仍缺失；未写生产文件/环境/业务库，无数据库迁移，不安装技能或执行脚本。队列369阻断保持，未add/commit/push/部署，交D统一提交。

已完成M1安全下载解析、M2认证预览/安装端点，旧上传/创建/更新/删除及AI空间路由保留。安装按source幂等，重取内容与预览摘要不一致返回409；已有同来源不同摘要也返回409，不覆盖原技能。存储复用当前账号个人库，无迁移。

验证：`python -m unittest discover -s tests/regression -p github_agent_skills_test.py -v` 八项通过；其中安装端点测试使用AsyncMock存储，无数据库写入，覆盖当前身份归属、摘要变化阻断、同来源幂等及不同摘要不可覆盖，启停重新normalize后合法摘要仍保留。相关4个Python文件ruff通过，3个后端文件py_compile通过，git diff --check通过。`codegraph sync`仍command not found。

2026-10-13恢复复核：同命令现为十项通过，新增慢速响应总超时、修改后的同源技能阻断、跨账号404与停用409的真实选择函数隔离验证；ruff与py_compile通过。当前工作树再次只读下载上述公开skill-installer，2881字符与同SHA256；无数据库或线上业务写入。6000字符是当前个人技能存储上限，下载明确拒绝超限，不截断或冒称支持完整仓库脚本/引用文件。

真实只读下载 `https://github.com/openai/skills/blob/main/skills/.system/skill-installer/SKILL.md` 成功，正文2881字符，SHA256 `83b31cffb2552a923f4152f0338bea548274accc5489d151a95bced8e7bcfb74`。同仓库错误路径HTTP404准确422；anthropics/skills PDF正文超过6000准确422且未截断。未下载辅助脚本、未运行仓库代码、未向模型加载远端指令、未写业务数据。

边界：只安装SKILL.md声明式正文，不支持附属scripts/references自动执行，含斜线的分支名需改用提交SHA路径；根仓库链接默认main，失败不猜测遍历分支。真实用户技能安装持久化、会话选用与页面结果保持待用户验收。未提交、未部署；构建由PM整合。

会话链路源码核对：`personal_agent/service.py::_generate_response` 调用 `_agent_skill_for_identity(skill_id, identity, db)` 取当前用户技能；`_prompt_messages` 将 `skill.instruction` 放入模型system消息，并明确在系统权限与工作规则内有效。`custom_skill_agent`再次包装权限/审批不可覆盖边界；不是仅安装一个展示入口。本记录仅源码与隔离模拟验证，不冒称真实数据库或模型端到端验收。

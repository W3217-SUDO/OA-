# 技能市场后端返工定位
## 1. 清单原文
独立返工：`你去对应的技能网站啊 让用户可以选择技能下载啊`；前轮`这个ai助手要做一个技能的连接器 跟codex一样仿照`、`然后技能可以去github上下载`。状态：定位后实施，未发布。
## 2. 截图分析
PM已逐张核对唯一a45bbc85截图，记录在`/tmp/oa-skill-market-20261014-remediation.md`：技能弹窗只有URL输入、禁用预览、空自定义列表及手工表单，没有目录搜索/选择卡片。后端任务依据此记录，不推断旧系统权限。
## 3. 旧系统实现
不适用：明确新增技能目录需求；本次误判是上一轮把发现技能工作留给用户，而非旧站业务差异。
## 4. 新系统当前实现
前端SkillManager原只github URL预览安装；C负责市场列表与选择。后端github_agent_skills固定GitHub Contents API、正文6000、SHA检查；个人库复用SystemConfig owner_username/skills。数据库不增加表、不迁移；现有账号权限、审批和会话选择保留。
## 5. 需求与当前实现差距
目录发现缺失；官方长PDF技能超6000被拒。skills.sh公开CLI搜索端点本机真实HTTP200（pdf返回anthropics/skills/pdf等）；api.github.com官方OpenAI目录HTTP200。v1私有OIDC API不使用，不绕过安全挑战。固定skills.sh搜索返回真实skillId/source/id，固定GitHub repo默认分支+实际递归tree发现唯一SKILL.md，禁止猜路径及多名匹配。官方目录只列真实文件夹，不每项下载正文或伪造介绍/热度。
## 6. 精确修改清单
- [x] 实际DOCX选中发现官方description超过500，新增统一8000字符说明限额，完整保留说明；前端同步，不更改128KiB文件限额。
- [x] 默认branch/path作为稳定安装source，预览先锁commit读取并返回resolved_commit；安装重读branch/hash阻断远端变化，避免仓库无关提交产生重复副本。
- [x] app/skill_catalog.py：固定来源目录/search、真实路径发现、服务端重查preview、固定域/URL校验、1MiB JSON/20秒总限时/120秒有界公共TTL缓存、账号请求限额。
- [x] areas/personal_agent/router.py：认证GET catalog和POST catalog/preview；不得接受任意远端URL或客户端自报路径。
- [x] user_agent_skills.py/github_agent_skills.py/api_schemas/agents.py：统一64000正文常量，完整预览、不截断，原128KiB字节上限保留；旧个人技能兼容。
- [x] tests/regression/skill_catalog_test.py及github_agent_skills_test.py：真实调用链隔离MockTransport、安全失败和长正文回归，不写真实业务库。
## 7. 验证清单
来源真实查询、官方实际tree、选中到SKILL正文、伪造id/路径/redirect阻断、上游失败不假空列表、quota、跨账号原有个人库链、長技能上限。仅公开只读网络、纯隔离测试，不控制浏览器、不写业务数据。完整构建/source由PM统一；页面待用户验收。
## 8. 实施记录
CodeGraph status/sync不可用，按规则rg定位。尚未Git提交/推送/版本分配/部署；实际数据清理不涉及。

2026-10-14实际只读来源链：skills.sh pdf搜索20条真实结果；选中anthropics/skills/pdf，默认分支→提交dbd4588f9e1033efb41dad4bef2f7947c8993d44→递归tree→实际skills/pdf/SKILL.md→已有Contents raw API预览成功，正文7511字符，SHA256 9f78b8359fbd4943ad260a7a1e436e5a96503406d6c34e99f69223d647d85b9c。OpenAI真实目录44项，Anthropic19项；不是固定卡片或假热度。目录没有伪造description，完整说明在选中预览时读取；空skills.sh搜索明确采用推荐关键词skill，返回note说明，不声称热门。

隔离验证：`python -m unittest discover -s tests/regression -p '*skill*test.py' -v`最终26项通过（市场新测试9项）。包含认证401、固定host/redirect/超限/上游失败502、伪造选择409、同名/截断tree阻断、固定commit下实际路径、公共缓存TTL、账号quota429、长正文及长说明解析/schema/存储、说明8001字符拒绝、无关commit更新保持stable source。邻近旧个人库契约使用其自身隔离夹具，不访问真实业务库；本轮未创建任何真实数据。ruff、相关py_compile与diff-check通过。

配额为每API worker每账号30次/分钟，有界2048账号；公开JSON缓存64条、120秒、失败不缓存。GitHub匿名上游配额耗尽或树过大明确失败，不伪装空目录或绕过鉴权。只安装声明式正文，仓库scripts/references不执行；浏览器与真实个人技能持久化保持待用户验收。

最终实际选中完整预览：Anthropic PDF正文7511字符/说明437字符，DOCX正文5943字符/说明835字符（此前说明500限制是真实阻断）；DOCX SHA256 8017469ea95fb7d28225c62daf8e2f3492a7b516fc64c18c28977cbf8980b7fe。两者resolved_commit均为dbd4588f9e1033efb41dad4bef2f7947c8993d44，输出稳定URL分别为main/skills/pdf/SKILL.md、main/skills/docx/SKILL.md。resolved_commit只表示本次预览读取版本，默认分支可变化；安装依原接口重读内容并验证SHA，改变则409、不覆盖原编辑副本。含斜线默认分支当前旧URL解析仍不支持，明确提示高级固定提交安装；不猜测路径。

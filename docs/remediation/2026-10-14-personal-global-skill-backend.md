# 已确认个人/全局技能归属：后端精确实施设计

## 1. 清单原文
用户：`智能体中心安装的技能在个人空间目录里 智能体中心安装的技能在全局中心里`；澄清答复：`是，AI 助手个人技能，智能体中心全局技能`。
本轮明确范围：AI助手个人安装、管理员智能体中心全局安装。保留全部已安装个人技能，不迁移或共享；目录是实际已保存定义记录及可下载SKILL.md，本轮不新增OSS技能文件、不挪用户业务文件。
当前状态：在PM批准的新clone373基线实施，后端已完成必要隔离验证，未发布；不修改373已上线包或原主树。

## 2. 截图分析
PM逐张记录见`/tmp/oa-skill-scope-20261014-analysis.md`。图为案件详情文档树的AI空间，不能作为全局技能面板或人员字段修改依据。真实目录归属依据用户澄清和实际App路由，不把案件文件AI空间当全局技能仓库。

## 3. 旧系统实现
不适用：独立新增已确认归属规则。上一轮只有个人JSON技能库，管理员中心仅只读总览，并无全局安装或技能定义下载。

## 4. 当前源码与权限链
- `App.tsx`真实`agent-center`→`AgentAdminPage`；`case-agent-center`→`AgentCenterPage`，是不同菜单。后者现有“我的技能”仍是个人CRUD，是否改仅全局选择需PM决定，不能擅删原个人能力。
- `areas/agent_admin/router.py`已由main完整include，overview要求`_require_admin`。新子router可include在此模块，不需要编辑main复杂route slices。
- `core/documents.py::_user_agent_skill_store/_save_user_agent_skills`以当前username哈希key存owner_username/skills。现有`/agent/skills`创建、上传、更新、删除，以及Github安装均只写本人库。
- `core/permissions.py::_agent_skill_catalog_for_identity/_agent_skill_for_identity`是个人与案件runtime共用技能选用点，适合最小添加全局库；`custom_skill_agent`既有提示包装与runtime高层规则限制审批、数据范围不可覆盖。
- `/system/configs/{config_key}`generic PATCH已有注册key白名单未知key404；新全局key在`core/system.py::_validate_system_config`显式409，明确专用管理入口。generic GET原页面菜单能力可读取技能原始JSON，已仅对非真实管理员排除技能namespace，其他配置原样。
- 个人AI空间文件是`ai_generated_file`+FileAttachment+OSS实体链，与SystemConfig技能定义不同。本轮技能Tab使用当前本人已保存记录并生成真实MD响应，不将其伪称既有OSS文件。

## 5. 具体数据设计与接口契约
### 独立全局库
- `GLOBAL_SKILL_CONFIG_KEY=agent_global_skills_v1`，group可为智能体，value固定schema_version=1/scope=global/skills；key不以USER_SKILL_CONFIG_PREFIX开头，不被旧个人overview误当用户库。
- IDs固定`global-<uuidhex>`；个人现有`custom-*`不变。内置`SKILLS_BY_ID`不可被新增库覆盖。空库读取返回真实空items，不造预置记录。
- 管理员写入复用既有`_require_actual_system_admin`，store服务自身再次检查，不只依赖UI；页面菜单临时能力不能提升真实管理员角色。所有写入口要求事务、审计当前username、校验长度/来源/ID；更新保留id，来源/hash不能由请求伪造，启停保留原摘要。
- 写read使用SystemConfig行锁，已有行跨进程更新序列化。首次行创建并发通过已有unique key约束捕获冲突，rollback后409可重试，不静默丢失或覆盖。下载/preview网络在取写锁之前完成，避免长时间持数据库锁。
- 同来源安装检查sha256和name/description/instruction；hash或已编辑内容不同返回409，不覆盖旧版本；同源完全相同返回原global id。全局独立数量上限复用30，和本人限額互不占用。

### 管理与选用
- GET `/agent/global-skills`：认证身份；管理员返回全部global（含停用），普通用户只enabled，格式`{items,scope:'global',can_manage:boolean}`。仅已安装全局记录，不把builtins混入可编辑列表。
- POST/PATCH/DELETE `/agent/global-skills[/{skill_id}]`、POST `/agent/global-skills/upload`、POST `/agent/global-skills/github/install`：管理员专用，写请求不得接受caller自报owner/scope/id；复用373全局正文/说明限额与真实预览安装SHA机制。
- 原 `/agent/skills`个人写接口保持不变；对global-* ID更新/删除只在本人库找，404，不落入新全局库。
- 原runtime GET `/agent/skills`返回builtins+enabledglobal+本人personal，public记录补`scope=system/global/personal`；不把别人的个人库合并。personal可管理UI只显示自身scope个人，防global custom标记被旧编辑入口误操作。
- `_agent_skill_for_identity`先内置，再global-id查新库（停用409/不存在404），再本人custom-id（非本人404）。global指令采用同样“不覆盖系统权限、审批和数据边界”的包装，不新增工具或角色。
- GET `/agent/skills/personal`：仅本人现有custom定义，`{items,scope:'personal'}`；个人AI空间技能Tab使用此接口，不显示全局或他人技能。

### 查看与下载真实保存定义
- GET `/agent/skills/{id}/definition`和`/agent/global-skills/{id}/definition`返回`{id,name,scope,filename,content,definition_sha256,import_sha256?}`。前者仅本人custom，后者仅允许当前可读global，管理员可读停用。
- 同路径尾缀`/definition/download`返回真正UTF-8 `text/markdown`附件，Content-Disposition使用安全文件名；response字节由已保存name/description/category/quick_prompts和完整instruction序列化为标准YAML frontmatter+正文。下载可再通过新版SKILL格式上传，不丢正文。
- `definition_sha256`为实际重建并下载字节的SHA；`import_sha256`只有记录原来保存合法摘要才返回，用清楚名称标记来源。不能声称重建文件等于原GitHub字节，不为旧记录补编原raw hash。
- 没有原raw文件的旧个人记录照样能查看/下载当前保存定义；此行为不要求迁移旧库、不创建OSS对象或业务附件。

## 6. 精确实际修改清单
- PM追加批准：`areas/system/router.py::list_system_configs`只对技能namespace作原始JSON读过滤；非真实管理员排除新GLOBAL_SKILL_CONFIG_KEY及既有USER_SKILL_CONFIG_PREFIX，个人定义通过专用本人API读取。其他config/menu权限完全保留，真实管理员仍返回全部原字段。当前373 generic PATCH本来有注册key白名单else404，不是允许任意key；全局显式409只给明确专用入口提示。
- 新`app/global_agent_skills.py`：独立key/store/global CRUD幂等及提示边界，实际已安装定义序列化helper可放独立`app/skill_definitions.py`避免module循环。
- 新`areas/agent_admin/skills.py`子router：global管理/读取、个人only读取、两scope定义下载；include于`areas/agent_admin/router.py`，不触main。
- `core/permissions.py`两技能目录/选择函数合并新global库；保留原个人404/启停及admin最高权限。
- `core/system.py::_validate_system_config`禁止新全局key通过generic PATCH；管理员明确收到“请在智能体中心管理全局技能”提示，专用管理仍有全部权能。
- `user_agent_skills.py`仅必要scopepublic兼容及标准SKILL YAML上传/定义serializer复用；source/hash启停保留与正文64000/说明8000不弱化。
- 后端隔离unit/MockTransport回归：普通global写403，admin成功；个人global互相不覆盖；runtime合并/跨个人404/停用global409；generic保护；同source hash/编辑冲突；下载内容及定义hash真实性/长正文/合法中文filename/旧无raw摘要；并发首次冲突rollback。
- 前端C负责`SkillManager scope`和APIprefix以及AIspace技能Tab、AgentAdminPage全局管理；与B约定契约如上，不在Backend实现时跨界编辑前端。

## 7. 验证与边界
仅隔离模拟/纯unit，不执行生产或真实本地业务造数、OSS PUT或浏览器控制。数据库结构无需迁移，写入新全局SystemConfig仅在用户实际安装操作时产生。全部旧个人记录保留不动。
后端已在新的scope clone实现并完成必要隔离验证；正式source/build/版本/发布交PM。373已上线包和原dirty主树保持不动，本候选未提交、未部署，待用户最终页面验收。

## 8. 实施记录
已按PM批准在`/tmp/oa-skill-scope-20261014-jmLZpF/source`373/8a8ad978基线完成后端实现。新global_agent_skills、skill_definitions、agent_admin/skills子router；注册不触main；core.permissions只改两技能函数，core.system新key保护，system/router只技能namespace读过滤，user_agent_skills兼容scope与合法标准SKILL上传。

新增隔离测试覆盖6个普通/页面能力用户全局写入口403，未登录读取401，管理员CRUD、启用目录和停用定义保护，个人与全局及内置ID隔离，runtime全局指令不可越原权限，源码配置保护和实际通用配置GET技能过滤/管理员全字段保留。首次global唯一键创建冲突rollback409，同源及编辑版本保护，SHA变化安装无存储动作，已保存MD重建hash与原importhash分离、标准MD回上传字段一致、恶意历史ID下载安全filename。没有对真实业务库或OSS写入。

CodeGraph status/sync不存在；按规则rg定位真实App/权限/存储/生成文件链。聚焦及邻近skill回归、ruff和py_compile/diff-check结果在PM交付回执记录。无Git暂存、commit、push、版本或服务切换；完整构建/source交PM整合。所有页面保持待用户验收。

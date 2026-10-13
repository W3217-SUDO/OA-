# AI助手个人技能与智能体中心全局技能（前端）

## 原文与证据
用户确认：是，AI 助手个人技能，智能体中心全局技能。
本次无新截图。PM批准设计后提供独立373基线树实施；不会迁移/共享既有个人技能。

## 旧系统
不适用：新增作用域与个人技能定义目录。当前真实路由agent-center是AgentAdminPage；case-agent-center是AgentCenterPage。

## 当前链路与差距
SkillManager/SkillCatalog原来统一个人写入，AgentAdminPage仅overview无globalCRUD；PersonalAiSpace只有OSS文件，无本人技能记录入口。
后端由B提供global列表/权限/CRUD/upload/install、本人personal列表、definition及definition/download；不涉及前端数据库/OSS迁移。内置系统技能保持只读。

## 改动清单
- [x] SkillManager/SkillCatalog默认personal，global管理员管理写global路径，所有安装确认明确仅本人/全局，onSelect可选且刷新失败仅刷库不重装。
- [x] AgentAdminPage全局技能入口，仅overview授权且can_manage允许写，原系统技能与各账号个人库保留。
- [x] PersonalAiSpace最小Tabs包装，默认文件行为保留；新PersonalAiSpaceSkills独立加载本人records、完整definition、启停、MD真实API下载；不新增OSS传输。
- [x] CaseAgentCenter保留个人管理与enabledglobal选择，共用scopeLabel只改显示名称不改ID；其个人编辑列表过滤global/system，并将旧表单上限同步8k/64k以保留长个人定义可编辑。
- [x] 手机320/375/390/414单列、768与PC两列；44px控件、长内容wrap和滚动；实际最终产物与八宽度核验交PM，未进行真机或浏览器验收。

## 契约
GET /agent/global-skills -> items仅global，admin含disabled/普通enabled，can_manage。
GET /agent/skills/personal -> 仅本人custom；原GET /agent/skills聚合system/global/personal且scope字段。
GET /agent/skills/{id}/definition或/global-skills/{id}/definition -> id,name,scope,filename,content,definition_sha256,import_sha256?；尾缀/download返回当前保存定义UTF8 SKILL.md，不是原ZIP。CRUD写global admin403、本人记录隔离404，inactiveglobal不能选。

## 验证与状态
本任务不浏览器、不业务造数、Git/版本/部署由PM。codegraph未安装用rg补充；依赖安装/类型检查/隔离事件tests后回报，最终统一构建交PM。另源Office待正式新baseline融合，不覆盖其在线改动。
## 实施核验
- npm ci成功224packages，package/lock未变；npm run typecheck exit0；git diff --check通过。
- 既有`tests/architecture/caseAgentWorkspaceRuntime.test.mjs`运行`--test-name-pattern='skill market browses|GitHub URL install|personal AI skill directory|global skill management'`，pass4/fail0。
- 行为证据：市场和URLpersonal默认写路径不变，global确认只写global安装路径且管理无onSelect；global列表不提供personal编辑项，adminoverview拒绝或can_manage=false没有写入口；长正文/说明完整，取消零install、SHA确认、安装成功刷新失败不重装。
- 个人目录active=false（默认文件）不加载skills；active=true只读本人/personal，definition完整内容与当前/导入SHA分别标注；download使用真实API Blob响应与Content-Disposition，不本地拼原ZIP，沿用既有文件download的一秒URL回收以兼容Safari/iOS；启停PATCH本人id并刷新实际runtime.skills，避免返回AI对话时目录缓存遗漏。
- 个人AI空间原OSS文件/分页/来源会话完全保留，没有修改`PersonalAiSpaceFiles`；`AssistantPanel`仅补一个onSkillsChanged=workspace.refreshSkills回调，不改对话创建/发送/停止/确认。
- codegraph status/sync exit127不可用。无业务记录、无浏览器标签、无测试数据清理负担，Git/发布未执行。
- 文档归属修正：前端初用scope.md与B撞名，已改独占frontend.md，B独占backend.md。生产Office后续同PersonalAiSpace需PM基于正式新基线融合保全，不能以373模板覆盖。

## 精确前端文件
AgentAdminPage.tsx、AgentCenterPage.tsx、PersonalAgentCenterPage.tsx；personal-agent/AssistantPanel.tsx（仅回调）、AssistantWorkspaceTools.tsx（仅label）、MobileComposerOptions.tsx（仅label）、PersonalAiSpace.tsx、SkillCatalog.tsx、SkillManager.tsx、types.ts、workspace-context.css、personal-ai-space.css；新增PersonalAiSpaceSkills.tsx与skillScope.ts；既有architecture/caseAgentWorkspaceRuntime.test.mjs及本文档。
当前本地实现与隔离检查通过，等待PM统一构建/发布及用户验收，不宣称生产验收。

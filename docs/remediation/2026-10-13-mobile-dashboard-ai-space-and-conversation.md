# 手机工作台、AI空间和新建对话整改定位

## 1. 清单原文
- 独立问题，无工作簿、工作表或行号。
- 原始问题逐字：`手机布局下方没有对齐 ，新建对话前端让用户确认一下`
- 补充独立原文逐字：`没有查看文件的地方`；`这里应该有个ai空间`
- 四个原子需求：手机最新案件布局、新建对话确认、回答保存后查看文件、工作台AI空间入口。
- 返工意见：无；当前状态：候选代码完成，待统一发布及用户验收。

## 2. 截图分析
### 图1：codex-clipboard-e38a5fee-af9d-4d8b-bcb5-7b3e45c2c41f.png
- 手机工作台最新案件区域被红框标记，白底卡片文字紧贴边缘；存在案号、阶段、当事人和日期，长文本必须可读。
- 此截图不能单独证明底部导航遮挡：父滚动链已扣头部、底部导航及安全区，修改保留该链并补内容余量。
### 图2：codex-clipboard-502f5e72-0b1a-4a2a-841a-0013fc19bb70.png
- 手机AI对话顶部加号被红框标记，要求点击新建前确认；取消不创建、不改变已有对话、草稿或附件。
### 图3：codex-clipboard-82d2c05f-b7a2-4225-a3d0-3b4c781816dd.png
- AI回答下方只有浅灰已保存提示，无可点击文件入口；手机顶部个人空间原被隐藏，需要显式可达查看入口。
### 图4：codex-clipboard-e7b4fea2-5264-49d6-9030-ccf1022b94c2.png
- 工作台工作概况、助手对话旁边空白处被红框标记，用户要求AI空间按钮；应打开已有个人空间真实列表。
- 原截图由A/C逐图核对，定位与实施证据保留在树外`/tmp/oa-a-dashboard-remediation-20261013.md`、`/tmp/oa-c-chat-entries-20261013.md`。本候选不上传图片或临时证据。

## 3. 旧系统实现
不适用：本次为新系统呈现修正和明确新增交互，用户未要求旧站对照。

## 4. 新系统当前实现
### 前端
- `Dashboard.tsx`工作台视图原仅两个手机按钮；复用`PersonalAiSpace`组件新增入口及来源会话回跳。
- `DashboardOverview.tsx`读取`dashboardData.latest_cases`，`dashboard.css`手机行原左右padding为零、当事人nowrap；修正内距和折行，保留权限导航。
- `ConversationManager.tsx`顶栏和抽屉原直接创建；统一`Modal.confirm`，`useRef`防重复确认，确认后才调用原`onCreate`，失败留框和抽屉可重试。
- `AssistantPanel.tsx`保存结果原禁用按钮；保留已保存标签，并按`workspaceDocumentSaveTarget`分别打开个人空间或案件详情真实文档目录。兼容`ConversationMessage.tsx`、`PersonalAgentCenterPage.tsx`同语义入口同步修正；后者未证明为当前App现役路由。
### 后端
不修改。已有`/personal-agent/ai-space`、`/personal-agent/ai-space/files`真实列表/下载与会话接口继续使用；确认不增加权限或替代原创建函数。
### 数据库
不修改结构、不迁移、不写业务数据。现有个人空间按身份归属过滤，案件文档不混入个人空间。

## 5. 需求与当前实现差距
|编号|具体入口|用户要求|原行为与根因|修改点|
|---|---|---|---|---|
|D1|手机工作台最新案件|下方对齐|手机行无左右内距、长当事人nowrap|dashboard.css手机卡片内距、宽度约束及折行|
|D2|AI顶栏/抽屉新建|前端确认|两入口直接创建|ConversationManager确认、取消无动作、失败可重试|
|D3|已保存回答/手机AI|查看文件|已保存按钮禁用、手机个人空间入口隐藏|AssistantPanel和同类回答入口可达查看文件|
|D4|工作台视图工具栏|AI空间|仅工作概况/助手对话|Dashboard新增空间按钮及现有真实抽屉|

## 6. 精确修改清单
- [x] `Dashboard.tsx`新增个人空间、来源会话选择后切助手；`dashboard.css`手机三按钮、44px触摸高度、最新案件内距/折行。
- [x] `ConversationManager.tsx`两个人工新建入口统一确认；已有会话保留提示，空ID不承诺不存在的历史返回；单确认锁在afterClose释放。发送自动建会话保持原样。
- [x] `AssistantPanel.tsx`及`assistant-panel.css`新增手机查看文件入口；已存回答显示真实查看按钮。
- [x] `ConversationMessage.tsx`、`PersonalAgentCenterPage.tsx`同步个人/案件保存目标及查看入口；`personal-ai-space.css`动作折行、抽屉视口限宽和确认触摸高度。
- [x] 既有`tests/architecture/centerViews.test.mjs`、`caseAgentWorkspaceRuntime.test.mjs`补相应隔离React事件覆盖。
- 精确源码/既有测试共10文件，另本记录1文件；不纳入另一会话GitHub技能连接器/玩偶文件或旧环境改动。
- 影响：工作台和AI已有入口；后端、数据库迁移、定时、审批均不涉及。

## 7. 验证清单
|原文片段|真实入口与权威来源|实际差异|验证证据|状态|
|---|---|---|---|---|
|手机布局下方没有对齐|工作台latest_cases|卡片内距及长文自然折行|A源码CSS核对320/375/390/414/768/PC；统一产物及真机待验|待用户视觉验收|
|新建对话前端让用户确认一下|顶栏/抽屉原onCreate|确认前零创建、取消零创建、失败留框、重试|既有React事件回归包含双击锁/空ID/失败|隔离测试通过；待用户验收|
|没有查看文件的地方|已保存回答和手机AI入口|个人空间或案件文档分流|源码/API权限链复核，不写库|待用户验收|
|这里应该有个ai空间|工作台第三按钮|打开已有空间及来源会话|centerViews真实组件传参/成功回跳/失败不切面板|隔离测试通过；待用户验收|
- 未创建业务记录、附件、临时服务或浏览器标签，无业务清理需求。
- 本任务不执行浏览器或业务API/数据库测试。最终完整构建、source门禁与官方static由唯一正式发布owner整合两个候选后执行；候选分支hook不触发dev/main source，不能冒称source通过。

## 8. 实施记录
- 候选从真实GitHub dev `a5a133cc71698bde57f3bc348164c037c4b1f9a8`构造，完整保留前序1.1.369身份OSS工作，三方应用10文件无冲突。
- CodeGraph status/sync命令不存在，按规则用源码检索补证。
- 定向测试：`node --test tests/architecture/centerViews.test.mjs tests/architecture/caseAgentWorkspaceRuntime.test.mjs`在候选树全组28/28通过；`npm run typecheck`通过，diff-check通过。
- 首次全组运行发现原personal center终态测试未stub新增PersonalAiSpace组件，触发Node无document错误；仅补现有测试依赖stub、保留全部终态断言后全组通过。另真实回答文件目标按钮及个人空间传参均由既有React隔离回归覆盖。
- 无数据库迁移、生产数据写入、版本号变更；本记录不宣称已发布或已验收。
- 正式发布由已协调唯一owner执行；全部页面结果保持待用户验收。

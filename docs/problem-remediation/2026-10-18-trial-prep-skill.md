# 庭审准备技能接入案件智能体

## 原始需求

“这个skill 你下载下来，到时配进去 后面我们开庭案件 中那个地方 就可以用这个技能；这个地方要用到”

## 证据与分流

- 外部技能包：`/Users/taowei/Library/Containers/com.tencent.qq/Data/Downloads/庭审准备skill.rar`。
- 技能包只读检查：包含 `civil-trial-prep-v3/SKILL.md`、四个 references 模板和旧版 `civil-trial-prep/SKILL.md`；选用 v3 作为较新的定义。
- 截图：`codex-clipboard-a9f715e5-e976-4cc3-a471-265c88036249.png`。页面身份为 OA 工作台右侧“开庭排期”，每个排期项有“交接智能体”入口；没有旧系统对照标识。
- 分流结论：新增需求，旧系统代码不适用。

## 追踪关系

| 原文片段 | 子问题 | 代码/接口 | 验收 |
| --- | --- | --- | --- |
| 下载并配进去 | v3 技能纳入案件技能目录 | `apps/api-server/app/agent_skills.py` | 技能可选且可发送 |
| 开庭案件中那个地方 | 排期入口定位案件并预选技能 | `Dashboard.tsx`、`DashboardHearingSchedule.tsx`、`CaseCenterPage.tsx`、`useCaseAgentWorkspace.ts` | 点击后进入对应案件智能体 |
| 这个地方要用到 | 权限仍由案件空间校验 | 现有案件智能体 API/权限校验 | 不扩大案件访问范围 |

## 实施与验收记录

- 修改文件：`apps/api-server/app/agent_skills.py`、`apps/admin-web/src/Dashboard.tsx`、`apps/admin-web/src/DashboardHearingSchedule.tsx`、`apps/admin-web/src/legal/CaseCenterPage.tsx`、`apps/admin-web/src/legal/hooks/useCaseAgentWorkspace.ts`、`apps/admin-web/src/legal/services/assistantActions.tsx`、`apps/admin-web/src/App.tsx`。
- 后端定向回归：`agent_skill_registry_contract_test.py` 与 `case_agent_mvp_contract_test.py`，30 项通过。
- 前端单元测试：`npm test`，223 项通过；生产构建 `npm run build` 通过，Node 22。
- CodeGraph：本机未安装，`codegraph status` 返回 command not found；按规则使用源码调用链补充分析。
- 浏览器验收、Git 提交、部署和线上检查：待实施。

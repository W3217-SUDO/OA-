# 2026-10-10 案件智能体经办律师审批报错

## 1. 用户原文与范围
- 原文：智能体报错，修改前没有查询出来
- 用户回复 `1` 表示继续处理，不是验收通过；目标案件 `GDMS2401011`。
- 独立新系统 AI 功能问题，非 Excel 批次。本任务自动发布已获授权，由主会话统筹；D 子线程仅维护本文与功能清单，不提交或发布。

## 2. 截图证据
两张原图已由主会话从用户消息目视核对，确认预览 before 四项全空、批准时报四字段无权。以下记录引用主会话的原图核对结果，不是 D 子线程自己的视觉验收或修复后的页面验收。

### 图 1：codex-clipboard-de65475e-f014-4051-b956-276267006828.png
- 目标 `GDMS2401011` 的 AI 修改预览中，四个字段的“修改前”均为 `—`；“修改后”依次为 `case_lawyer=caozg`、`case_lawyer_name=曹志刚`、`handling_lawyers=[曹志刚]`、`handling_lawyer_usernames=[caozg]`。
- 预览未展示原值，不代表数据库原值为空，也不证明曹志刚账号当前有效。

### 图 2：codex-clipboard-c5c3a198-9506-491e-9a4c-0d9c1f905437.png
- 审批报错：`智能体无权修改字段`，涉及全部四字段：`case_lawyer`、`case_lawyer_name`、`handling_lawyers`、`handling_lawyer_usernames`。
- 与图 1 对应同一人员变更：模型提出变更不等于服务端可执行；不能通过取消权限或字段校验来消除错误。

## 3. 旧系统实现
不适用：旧系统没有对应 AI 操作审批功能。以用户原文、新系统案件人员模型和现有审批权限为依据；不修改或部署旧系统。

## 4. 新系统链路
- 前端：AI 待审批操作的字段前后对照与批准动作；既有 `apps/admin-web/src/legal/services/assistantActions.tsx::decideCaseAgentAction` 调用案件空间 decision 接口。
- 后端：`CaseAgentRuntime` 生成待审批操作，经 `_action_preview` 保存前后值；`apps/api-server/app/areas/legal/case_space.py::decide_case_agent_action` 校验可见范围、操作能力及过期快照，再调用 `apps/api-server/app/core/documents.py::_execute_case_agent_action`；人员校验与团队投影现独立在 `apps/api-server/app/core/case_agent_personnel.py::_case_agent_handling_lawyer_data`。
- 数据：`BusinessRecord(module="case").data` 保存人员数组与 `case_team_usernames`；稳定账号由 `User.username` 解析，既有 `_resolve_active_case_people` 拒绝不存在、停用或姓名不唯一的人员。审批审计为 `BusinessRecord(module="agent_action")`，业务操作写 `WorkflowEvent`。
- CodeGraph：编辑前 `status` 显示索引最新；已 `explore` 上述运行时、审批、执行、独立人员模块、团队投影与草稿提成函数，编辑后 `sync`。确认依赖为运行时预览 -> decision 权限/快照检查 -> 执行器 -> 人员模块 -> 案件团队及提成服务；图谱模糊同名命中不计作实际依赖或业务验收。

## 5. 需求与当前实现差距
| 编号 | 用户要求 | 已确认根因或缺口 | 源码落点 |
|---|---|---|---|
| D1 | 修改前应读到现有经办人员 | 原 `case.update` 预览只取案件顶层，而人员值在嵌套 `data`；`source.get` 因而得到空值 | `case_agent.py::_action_preview` |
| D2 | 合法经办律师变更可审批 | 原 `AGENT_CASE_UPDATE_FIELDS` 仅含 `title/customer/status/description`，四个人员字段全部被拒绝 | `core/constants.py`、`core/documents.py::_execute_case_agent_action` |
| D3 | 预览与批准使用同一原值口径 | 原 decision 的 `case.update` 当前值仅含 `title/status/description`；预览读到人员真值后会误报变化，旧空值预览又可能漏检人员变化。现已复用 `_action_preview` 校验；既有回归通过，修复后页面待用户验收 | `areas/legal/case_space.py::decide_case_agent_action` |

## 6. 实现映射与待办
以下六项源码已实现；C 的既有隔离回归已全部通过，覆盖边界见第 7 节，不据此推定新人员 helper 的专门覆盖。最终集成构建、发布与用户验收另行记录。

| 要求 | 当前实现映射 | 残余验证与用户验收 |
|---|---|---|
| 正确预览原值 | `case_agent.py::_case_agent_case_source/_action_preview` 合并顶层与 `data`，以规范数组投影兼容单值；模型提示只输出规范字段、核实真实账号 | 非空原值必须真实显示，旧空值或缺失原值的待审批操作须重新生成 |
| 合法人员与四字段校验 | `AGENT_CASE_PERSONNEL_UPDATE_FIELDS` 与 `core/case_agent_personnel.py::_case_agent_handling_lawyer_data` 走既有启用账号解析，校验非空字符串、姓名/账号有序对应及别名首位一致性 | 不存在、停用、重名、空列表、伪账号及不一致输入必须明确拒绝且无部分写入 |
| 不绕过权限 | decision 保留 `_ensure_record_module`、`_require_case_agent_action_access`，非人员未知字段仍拒绝 | 无权账号不得通过 AI 提升能力 |
| 过期拒绝 | decision 复用 `_action_preview(action, context)`，逐字段检查原值存在且与当前值相等 | 真实变化或缺失快照返回 409，未变化不能误拒绝，不得跳过校验 |
| 规范团队持久化 | 人员模块调用 `_case_team_payload` 保存 `handling_lawyers/handling_lawyer_usernames/case_team_usernames`，保留助理数组并同步已存在的兼容字段 | 两种案件更新类型均须保持姓名/账号对应、既有助理及兼容字段一致，刷新回读团队及权限投影 |
| 草稿提成刷新 | 两种案件更新类型在人员确有变化时调用 `_case_commission_personnel_changed/_recalculate_case_draft_commissions`，且位于阶段冲突返回之前 | 仅重算自动模式草稿代理费，不改人工及非草稿提成，核对异常与混合阶段变更路径 |

- 数据库：无结构迁移、无历史数据补丁，本次整改不回写 `GDMS2401011` 等既有业务记录；实际审批执行仍须经现有事务、权限与审计链路。
- 人员资格口径：与人工员工 picker 一致，复用 `_resolve_active_case_people`，只校验 `User.is_active` 及账号或唯一姓名匹配；不增加 HR 在职、岗位或员工档案条件。模型提示相应表述为“目标账号必须启用，先核对当前授权人员信息中的 username”。
- 风险：预览修正必须同步审批快照；旧 pending 操作不能因修复自动批准。团队别名、助理保留和提成异常分支不能只凭白名单修正宣称完成。

## 7. 验证与验收状态
- 已核对：主会话目视阅读用户两张原图；D 核对用户原文、CodeGraph 依赖及源码差异。原问题截图不等于修复后验收。
- C 最终结果（据主会话转交的 C 汇报）：既有隔离回归 `47/47` 通过，分为 MVP 21、多助理 3、员工绑定 9、开庭人员变更检测 7、代理费草稿重算 7。报告：[C 隔离回归报告](C:/Users/Administrator/AppData/Local/Temp/oa-ai-lawyer-existing-regression-7a581842dfd442c489cc8fbc201505d4.json)；D 已读取摘要，确认 `total=5 / passed=5 / failed=0`，用例分项数量依据 C 最终汇报。
- C 检查结果：菜单覆盖 `295 nodes / 248 leaves / 0 uncovered`；5 个改动 Python 文件（`case_agent.py`、`core/constants.py`、`core/documents.py`、`areas/legal/case_space.py`、`core/case_agent_personnel.py`）AST 与 compile 通过；diff 检查通过。未新增测试脚本，无真实数据写入。
- 覆盖边界：上述 47 项是既有回归，不声称为新 `_case_agent_handling_lawyer_data` 的专门测试或完整 AI 审批端到端覆盖。此前 B 30 项通过、A 33/34（1 项旧源码文本断言待核对）的结果保留为历史阶段报告，不与 C 重复累计；主会话负责最终集成复核。
- API 冒烟：未运行 `scripts/smoke-api.py`，因其含批量写入及历史 `SMOKE` 清理，避免触及真实数据。部署后仅执行 operational smoke，核对 API `/health` 与目标页面 HTTP 200；目前尚未执行，不替代业务验收。
- 残余验证：最终集成与前端生产构建结果待主会话汇总；新 helper 的人员/顺序/别名校验、失败原子性及实际批准后团队与提成刷新不能由既有回归自动推定，修复后页面待用户验收。
- 文档 UTF-8、必要原文/字段/文件名及差异空白检查通过；不替代业务测试。D 未新增测试脚本、业务数据或浏览器会话。

## 8. 交接与发布
- 本任务自动发布已获授权，由主会话统筹；其他修复仍在发布队列中，本问题不预定或硬编码下一版本。D 文档现已交付，不提交、不发布，也不等待发布。
- 发布版本、提交、运行包与服务激活结果以服务器 `queue.tsv` 和 `runtime-manifest` 为权威回执；主会话收到真实回执后补录，未知前不写“已上线”或“服务器已解决”。
- 本轮证据状态：实现已落地、既有隔离回归已验证、待用户验收；最终集成构建及运行回执由主会话负责汇总。用户验收须确认原值显示、合法人员批准及刷新结果；未经用户确认不标记已验收。

# 案件律师助理空值展示整改定位

## 1. 清单原文
- 工作簿/工作表/行号：不涉及，直接独立问题。
- 原始问题（逐字）：这个姓名待维护不对啊
- 补充说明/返工意见：无。
- 当前状态：根因已核实，未发布，待用户验收。

## 2. 截图分析
### 图 1：codex-clipboard-2cf39891-3cca-4127-bf04-4476a3ff9fcd.png
- 入口：案件中心 → 民事案件详情 → 案件信息；截图域 huzhilawfirm.com。
- 对象：SHNONE2600001，合同 GDHT2410184；标注为律师助理值“姓名待维护”。
- 功能：只读人员展示。返回案件列表、案件智能体、操作及下方文档入口未被用户标注，本次不修改。
- 用户图仅有一张，无其他图关系。该图由主会话读取，B 依据图中可见字段追踪源码。

## 3. 旧系统实现
- 原有案件助理人员姓名/账号分别来自 Legal_Case.CaseAssistantName/CaseAssistant；本地旧源码未提供，未进行旧页面操作。
- importer 的逐字段映射以及既有 8.27-row3-read-confirmation.md 用户要求“如果该案子没有填某一个人员，那就横杠或者空白，不要写个姓名待维护”作为空态依据。
- 本次无编辑、状态流转或下游写入，不涉及按钮校验。

## 4. 新系统当前实现
### 前端
- caseAssistantDisplay.ts::caseAssistantDisplayValues 按候选人数取最长投影，将 assistant_display_name='—' 计为一名人员。
- legal/CaseCenterPage.tsx::caseAssistantDisplayNames → casePersonDisplayNames → casePersonDisplayName('—')；最后按非中文未解析人员返回姓名待维护。
- 列表、导出、民事详情 CaseDetailHeader 及顾问详情共用该助理 helper；手机复用同样展示链。
### 后端
- core/formatters.py::_case_assistant_display 对空助理返回 ('—', False)，_apply_record_person_displays 仅在返回副本投影，不修改数据库。
- 本次后端及接口、权限不改；新建/编辑仍由 core/cases.py::_resolve_active_case_people 和 _case_team_payload 校验并维护账号关系。
### 数据库
- C 只读核对正式 1.1.371：business_records 主键 279523、serial_no SHNONE2600001，assistant=''、assistants=[]、assistant_username=''、assistant_usernames=[]；legacy_record.CaseAssistant/CaseAssistantName 均 null。
- 运行 formatter 只读确认 assistant_display_name='—'、assistant_username_display_name='—'、missing=false，列表投影为空数组。
- 没有实际助理人员可映射，不能补造姓名；本次无数据库、角色、人员或迁移修改。

## 5. 新旧差异和根因
|编号|具体页面/数据/功能|旧系统/已有要求|新系统行为|证据|根因|
|---|---|---|---|---|---|
|D1|空助理详情及共享入口|空态横杠/空白|姓名待维护|截图、C 精确行只读核对、371 formatter、共享 helper|后端空态横杠被前端候选计为人员，二次解析为未知姓名|

## 6. 精确修改清单
- [x] M1 caseAssistantDisplay.ts::populatedValues 过滤明确空态横杠“—”，不把空态计入人数；保留未知非空账号和真实姓名原行为。
- [x] M2 已有 caseAssistantDisplay.test.mjs 补实际生产空字段+派生横杠、空态与真实姓名/多助理混合、未知账号行为；更新拆分后真实源码路径并核对共享入口。
- 后端、数据库：不涉及，空态生成正确；禁止修改已有业务数据。
- 风险：只过滤明确空态，不将真实缺名账号或姓名待维护占位静默抹除，保持有人员场景及多助理顺序。

## 7. 验证清单
|原文片段|真实入口/来源|代码差异|应/不应结果|证据|状态|
|---|---|---|---|---|---|
|姓名待维护不对|民事详情，生产279523空助理|M1|—，无伪姓名；真实姓名及未知账号原行为保留|Node22 既有用例及实际 page 展示链执行|通过（仍待用户页面验收）|
- Node22.23.3 既有 caseAssistantDisplay.test.mjs 通过；执行真实 page helper 转译链确认空态为 —、已解析中英多人保留、未知账号仍提示。TSC 和 Vite 生产构建通过（6.33 秒，既有 chunk warning）；真实用户页面验收待完成。
- API/权限成功失败/数据库持久化/定时/计数/点击：不涉及修改。C 已只读确认原值与投影，不创建数据。
- 手机：共用同一只读 helper，无样式、布局、导航或点击区域变化；320/375/390/414/768/991/992px 不改变原断点、长姓名换行或触摸区规则。生产 CaseCenterPage 资产含空态过滤；本次仅将错误长占位收敛为横杠，未执行真机/DOM布局验收。
- CodeGraph status 与改后 sync 命令均不存在（127），按规则直接源码补证，没有图谱结论。
- 测试数据/临时进程：0 数据写入，0 浏览器标签，未启动测试服务。

## 8. 实施记录
- 实际提交：尚未提交；隔离 clone dev 基线 5e5dec8ad5fa239840a2fe70598bc402c54a9df9 / 1.1.371。
- 范围：不带主工作树已有 AI 改动，不改后端/数据库，不发布旧系统。
- 测试/构建结果：Node22 定向、TSC/Vite 6.33 秒、git diff --check 通过。构建日志位于树外 /tmp/oa-assistant-name-20261014/candidate-build.log。已有测试的 wrapper/旧顾问 inline markup 断言在拆分基线失效，已定位到 legal/CaseCenterPage.tsx 与实际 CaseDetailHeader，不削弱人员展示要求。
- 发布前截图及原文：本轮单张直接问题，无 Excel 状态。
- 发布状态：未发布，待用户验收。

- 横向审计：普通案件列、特殊结算/退费列、原始档案列、详情及导出均传入同一助理展示函数。C 初次观察开庭律师占位为人员选项加载中的瞬时状态，加载后恢复范文玲，不属于本次空助理根因，不修改。

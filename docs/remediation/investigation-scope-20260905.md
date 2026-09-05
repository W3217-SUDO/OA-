# 我的调查任务基本信息修改对齐

## 1. 清单原文
独立问题原文：“这个按钮没有跟旧的系统同步啊”。补充原文：“这个节目都没有对齐”。不涉及Excel。当前基线05289ad；由根任务统一提交集成、GitHub推送、发布。

## 2. 截图分析
旧截图a9f90282：我的调查任务→修改→基本信息修改，单列水平表单；权利人只读、合同下拉、权利类型、线索是否客户审核、授权起止日期、授权范围全国/区域、区域联动、备注；确认/取消。
新截图c68ef9bc：同入口打开通用修改调查记录，两列标题/事项、权利人自由输入、不可用负责人、调查区域文本、权利类型、说明；遗漏合同、客户审核、授权期限和授权范围。

## 3. 旧系统实现
以GD.CRM.WEB/Areas/CIT/Views/Investigation/PartialView/Edit.cshtml为准（VIP副本缺合同）。WEB:78–81合同GetContractListByCustomerNo(Indicter)。共用CIT.Investigation.js提交CreateUpdate；R必须授权区域，起止日期有序；范围变化R显示省市多选，N隐藏。省市选择Province展示区域，City存选择城市。根任务反编译InvestigationScopeTypeService证实仅N全国/R区域。

## 4. 新系统当前实现
InvestigationCenterPage.openEdit/saveEdit→EditRecordModal→PATCH investigations/records/{id}。通用弹窗不读写所缺字段；API白名单虽含authorization_scope但没有类型联动校验。legacy_sync._sync_legacy_investigation写1/0与旧N/R不符。
数据使用business_records.data及现有CIT调查投影，不迁移、不补历史数据。保持主记录权限与任务/线索其他入口。

## 5. 差异和根因
将主调查“基本信息修改”错误复用通用记录编辑，既造成表单错位，也遗漏完整字段闭环。授权范围应为枚举与区域联动，不能由调查区域自由文本替代。VibeHub已查级联选择器 https://vibe-hub.org/cascader ，只辅助表达。

## 6. 精确修改清单
- 补充：API无现成省市验证器，复用前端现有省市数据生成同源investigation_regions.json用于后端隶属校验；主任务下游investigationTaskScopeGroups优先结构化路径精确限制城市，整省在旧City投影展开所有城市并用逗号分隔。合同列表沿用旧有效同客户范围，不加审批状态条件。异步编辑加载加防竞态与加载提示。
- 必要继承：新子任务将结构化授权类型和区域一并继承，避免第二代子任务又回退到含省名文本导致扩大到整省；不回写既有任务。
- [x] EditRecordModal：仅investigation主记录使用旧字段顺序、横向单列表单；其他module保留通用编辑。省市多选、全国隐藏区域。
- [x] InvestigationCenterPage：加载同权利人可见合同，字段回填，日期格式化，提交scope及关联字段，成功回读，失败可见。
- [x] investigation/router.py：主记录编辑验证合同权限/归属、权利类型、布尔、期限、全国或区域；维护合同关联字段，不允许借此改负责人或状态。
- [x] legacy_sync.py：调查投影N/R，保存授权字段；不批量改旧行。

## 7. 验证清单
直接问题不运行浏览器或业务测试。执行Python编译、类型检查及生产build。用户验收旧字段齐全、全国/区域联动、省市多选、合同回显、保存刷新、错误不成功；不影响子任务/线索编辑。

## 8. 实施记录
技能已显式读。CodeGraph未初始化，以直接源码链路核对。Python编译及tsc --noEmit通过；npm run build（tsc -b && vite build）通过，5817模块，10.79秒，仅已有chunk大小警告。git diff --check通过；无业务测试/数据库写入/测试数据。主记录表单实现完成，根任务统一集成推送GitHub及发布，待用户验收。

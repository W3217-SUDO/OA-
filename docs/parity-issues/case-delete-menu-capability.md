# [待核实] 公司案件删除仍有独立角色限制

## 基本信息与前端位置
- 发现日期：2026-09-12；来源：主动审计。
- 用户原文：“所有的页面都是的，只要客户可以看到这个菜单，所有的权限就要开放”。
- 菜单：案件中心 -> 公司案件；列表底部“删除案件”和确认弹窗。
- 前端：`apps/admin-web/src/legal/CaseCenterPage.tsx` 的 `selectedCaseCapability.can_delete_case`；`legal/services/workflowActions.tsx` 的 `deleteCompanyCase`。
- 接口：`DELETE /cases/{case_id}`。

## 新旧对比与证据
- 新系统 `core/permissions.py:_case_detail_action_capabilities` 仍用 `identity.role in {admin, manager}` 控制 `can_delete_case`。
- `areas/legal/router.py:delete_case` 同样先按角色返回 403，然后才检查可见范围与案件状态。
- 与当前用户菜单授权要求存在静态差异；不是由页面截图实际复现的结论。
- 旧系统删除行为、菜单授权和关联数据保护尚未在本轮核对，不能宣称已经完成新旧对比。

## 风险与下一步
- 本轮补充旧证据：`CivilDisputeCase/List.cshtml:209-214` 按页面 PageId 渲染删除按钮；`CaseController.CaseDelete:1071` 接受编号列表并交给服务。Web 层未见该方法额外的 admin/manager 判断，但服务层授权仍待核实。
- 新前端 `CaseCenterPage.tsx:canDeleteSelectedCompanyCase` 也有 `profile.role` 限制；因此需同时核对页面、能力返回及删除接口三层，不能只改一层。
- 另已确认多选被 `.find()` 缩减为第一条，见 [case-delete-selection-truncation.md](./case-delete-selection-truncation.md)。
- 删除路径会同时删除案件任务、附件、费用、排期和工作流记录；不能为了去掉角色限制而跳过关联与生命周期保护。
- 先定位旧系统公司案件删除控制器、前端调用和关联保护，再核对 `_ensure_record_module` 是否足以验证菜单访问及数据范围。
- 核对已归档、已合并、归档审批中以及有财务关联的行为；仅在隔离环境使用本轮自建数据验证。
- 状态：已定位候选，未修改、未验收、未部署。

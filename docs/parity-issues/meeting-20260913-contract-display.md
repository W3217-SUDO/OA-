# M02 案件头部只显示建案合同：原整改建议撤回

## 1. 清单原文
来源为会议原文及用户后续澄清，完整原文见 `meeting-20260913-source.md`。用户确认：案件合同编号只显示建案时的合同；新建案件费用可以选择其他合同，费用归集到该笔费用选择的合同。状态：原“展示不完整”判断撤回，不是已修改/已验收。

## 2. 截图分析
本轮未提供截图，无实际多个合同案件的数据核对。

## 3. 旧系统实现
W/Areas/FCM/Views/Contract/ContractObjects.cshtml:47-106遍历合同标的，按CaseId/CaseNo跳案件，按ContractId/BatchNo读日志。D中BizContractObject.cs含ContractId、CaseId、CaseFeeId。不能由这两个文件单独认定旧详情已展示全部反向合同；多对多为会议明确的目标。

## 4. 新系统当前实现
- 前端合同中心 -> 合同详情 -> 合同标的：`src/contract/ContractDetailView.tsx:327` 展示标的列表。
- 后端 `app/areas/contract/router.py:755-826` 支持 `/contracts/{id}/objects` 查询/创建及object-cases候选；只按“当前合同+案件+费用类型”查重复，没有全局禁止同案件关联另一合同。
- 数据库 `app/models.py:1565`：`contract_objects` 有独立主键以及contract_record_id、case_record_id、fee_type、amount，可表达多个合同关联同一案件。无需凭主合同JSON字段再造一套孤立关系表。
- 案件中心 -> 民事案件详情 -> 案件信息“合同号”：`src/legal/CaseDetail/CaseDetailHeader.tsx:49` 只渲染单个 `viewingCase.data.contract_no`，点击也只传单个合同id/编号。
- `app/areas/legal/router.py:3355-3371` 的归档上下文已合并主合同JSON引用及ContractObject反向关联，但普通案件头部未复用这层集合。

## 5. 定位纠正
此前把多对多关系推导为案件头部应显示全部合同，超出了用户实际规则。只显示建案时的一个合同本身不是缺陷。费用所选合同属于逐笔费用，不应反向更新案件合同号。底层ContractObject存在也不能推翻费用创建时明确保存的合同归属。

## 6. 整改范围
撤回全部“案件头部改成多合同集合”的前后端修改建议，本项移出整改清单。费用选合同、保存、归集及下游申请校验转入FIN-02重新定位。不得因为本次澄清创建额外关系表或批量改写历史合同归属。

## 7. 后续验证场景（归入FIN-02，本轮不运行）
- [ ] 案件从合同A创建，头部显示A。
- [ ] 同一案件新增费用1选A、费用2选B，保存回读后分别归集A/B。
- [ ] 新增费用2后案件头部仍为A，不增加B、不替换为B。
- [ ] A合同不重复归集费用2，B合同可读取费用2，后续申请不因案件头部为A而错误阻断。

## 8. 实施记录
只读源码定位；未修改业务代码、未运行测试、未写数据库、未提交或发布。

# M01 线索转案件允许无合同：已确认与会议要求冲突

## 1. 清单原文
- 来源：会议纪要，非Excel行；全文及证据根路径见 `meeting-20260913-source.md`。
- 原文：“案件必须依附于合同存在”。补充：“线索经审核后进入取证环节，最终生成案件，该链路目前已测试通过。”
- 状态：源码差异已确认，待确认整改范围；未运行业务复现。

## 2. 截图分析
本轮无截图、故障记录ID或浏览器操作；不复用前轮截图当本轮证据。

## 3. 旧系统实现
旧W/Areas/FCM/Views/Contract/ContractObjects.cshtml:53、57、72按合同标的CaseId/CaseNo打开案件，D/Dchien.Legal.BizModel/Dchien/Legal/BizModel/FCM/Contract/BizContractObject.cs同时保存ContractId、CaseId、CaseFeeId。此证据证明合同/案件/费用关系的存在，不能证明旧系统每个转案入口都强制非空合同。本项阻断要求的直接依据为当前会议原文。

## 4. 新系统当前实现
- 前端：案件中心 -> 新建案件，`src/legal/CaseCreateWizard.tsx:135` 的合同号 `contract_record_id` 为必填单选；调查大厅 -> 线索取证后 -> 批量转案件为另一路径，`src/investigation/BatchCaseConversion.tsx`、`InvestigationCenterPage.tsx`。
- 后端：`app/areas/investigation/router.py:1545` 的 `batch_create_cases_from_clues` 调用 `app/core/contracts.py:655` 的 `_resolve_clue_source_contract`。后者遇不到同客户合同或多合同歧义时返回 `(None, error)`；前者:1567取出 `contract_error` 后未阻断，只在contract存在且状态不允许时拒绝。
- 持久化：:1612将新案件写入 `BusinessRecord(module=case)`，`data.contract_id=None`、`contract_no=""`；数据库JSON并不保证必有合同。普通新建接口 `legal/router.py:create_case` 则按有效合同创建。
- 历史兼容：`investigation_87_contract_test.py:129` 明确断言无来源合同仍生成案件。因此这是已编码的旧行为，与最新会议约束冲突，不是偶发前端显示问题。

## 5. 新旧差异和根因
正常案件创建和线索转案对“必须有关联合同”的约束不一致；转案忽略解析失败原因，允许无法确定合同的案件落库。无合同、多合同歧义、来源任务缺失会落入同一分支。影响案件归属、合同费用候选、后续财务按合同查询。没有真实数据，不能声称已经确认线上漏关联数量。

## 6. 精确修改清单（待确认，不执行）
- [ ] `batch_create_cases_from_clues`：消费contract_error，未解析唯一有效同客户合同时逐条拒绝转案；保留错误文本，不产生半成品案件。
- [ ] `BatchCaseConversion.tsx/InvestigationCenterPage.tsx`：沿已有合同解析/补绑入口展示阻断原因与修复入口，不让用户以为转案完成。
- [ ] 调整 `investigation_87_contract_test.py` 中旧无合同成功断言，补无合同、多合同歧义、合同不可见/无效、混合批次场景。
- 数据库：现有字段可表达正常关系，本项无需直接新增表；历史无合同案件只出只读清单，未经单独授权不回填、不删数据。需确认历史例外是否只允许查看、不允许继续创建。

## 7. 验证清单（本轮不运行）
- [ ] 同一有效合同下转案成功，案件/线索/任务关系回读一致。
- [ ] 无合同和歧义合同无新案件，源线索状态不被误改。
- [ ] 混合批次分别报告成功/失败，旧迁移记录与普通记录不混淆。
- [ ] 对应用户菜单与真实角色路径、前端失败反馈、构建及自建测试数据清理。

## 8. 实施记录
仅定位文档；未改业务代码、未写数据库、未测试、未提交或部署。后续用户确认后统一整改。

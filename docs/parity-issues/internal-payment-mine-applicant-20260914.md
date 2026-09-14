# 内部费用我的请款单申请人整改

## 1. 清单原文
独立问题，非 Excel。原文：
> 在案件里根据代理费新建的提成正常进入了案件里面的内部结算，但是在财务中心，内部费用，我的请款单里看不见

状态：返工，待用户验收。

## 2. 截图分析
- fd3834f8-a767-43c4-9faa-951dd133c904：财务中心 / 内部费用 / 我的请款单，登录范文，未设置筛选，列表为空；查询、刷新入口可见。
- 0ac69690-1a2b-4e38-9e4c-041837de668e：SHMS2600445 内部结算有四笔费用，20+5+5+5，已申请付款金额等于费用金额，待审批；收款人为测试人员与范文玲。新增内部费用、申请付款按钮可见，编辑等按钮禁用。

## 3. 旧系统实现
已读 GD.CRM.WEB/Areas/FAM/Controllers/InternalFeeController.cs：InternalFeeObjectsCreate 按案件创建 BizPaymentBasic 与 BizPaymentObject，付款对象与申请单分别存储；PaymentList 按当前 UserId 获取个人请款，支付对象不是申请人的替代字段。本次未操作旧系统页面。

## 4. 新系统当前实现
- 创建入口：areas/legal/router.py::create_case_commissions，owner/payee 为收款人，handler 为操作人，未写 applicant。
- 列表：finance/FinanceCenterPage.tsx::originalFinanceRows 使用 applicant 或 owner 匹配本人；queriesActions.tsx 先取全财务前100条再过滤，亦可遗漏较早申请。
- 数据库：business_records，案件 case_no 与 source_fee_id 关联，payment_application_no 关联申请，付款身份与申请身份不同。
- 只读生产证据：47681–47684，applicant 全为空，handler/payment_applied_by 全为 fwlll；owner 为 csry 或 fwl；同申请号，合计35元。没有缺失费用，错误为申请人投影和筛选。
- 最新基线 v1.1.126 包含待结算、待归档、待审核生命周期，本次必须保留。

## 5. 新旧差异和根因
“我的请款单”将收款人误当申请人。历史记录已有 payment_applied_by，可无数据迁移兼容。个人费用明细的 mine 范围本来按收款人，应保持，不能直接替换为申请人。
VibeHub 已查询 data scope，无可靠匹配，不补充词条。

## 6. 精确修改清单
- 新增提成写入 applicant、application_date。
- core/system.py::_record_dict 对已有内部费用按 applicant、payment_applied_by、commission_created_by、handler、owner 依序投影申请人。
- core/permissions.py：仅内部费用按同一申请人表达式补充本人读范围；不改变收款人归属。
- internal-fees 增加 applications 范围，在分页前按申请人过滤；原 mine 仍为收款人。
- queriesActions.tsx：我的内部请款使用 applications 范围并完整读取分页，避免前100条截断；展示继续使用既有表格和筛选。
- 不涉及数据库迁移和业务数据改写。

## 7. 验证清单
按独立问题规则仅生产构建与部署运行健康检查，不执行业务测试、不创建测试数据。
用户验收：原申请人在我的请款单可见既有四笔；新建提成可见；申请人与收款人分别正确；待结算/待归档流转保持；其他人员不可因本修复读取无关申请。

## 8. 实施记录
入口矩阵：旧记录读取、新增提成、个人列表、个人费用明细、记录详情权限。生产数据假设已只读确认，无需回填。
修改提交：190b2f06ca1744b71ec73d257459b72e0eefe1eb。
生产构建通过，5836个模块；未创建测试数据，生产只读检查脚本已清理。
发布版本：v1.1.127，无数据库迁移或数据补丁，回滚点v1.1.126。激活结果以服务器queue.tsv与ledger.tsv为准；页面待用户验收。

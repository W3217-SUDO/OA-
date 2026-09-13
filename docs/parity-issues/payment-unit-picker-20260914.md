# 合同付款前端二次返工

## 原文和截图
- 用户：“怎么跟旧的系统不一样呢”“前端页面那你也要对齐啊”。
- 新系统截图 f19d89f3：收款单位下拉、主页面直接新增按钮、大表单弹窗；与旧选择流程不同。
- 旧系统截图 9360b857：申请付款主页面紧凑横向字段，点击收款单位打开“选择付款单位”；收款单位查询、类型（默认官费）、查询/选择/新增、复选框单选列表、类型/收款单位/开户行/账号、每页10条、跳页和取消。
- 状态：返工中。截图中的4597是旧数据数量，不能硬编码到新页面。

## 旧系统完整入口
旧系统归档源码/SH.CRM.WEB：
- Scripts/FAM/AP/FAM.AP.Payment.js 619-757、1199：lblPaymentType -> PaymentType.Open -> List；Select只允许一个单位；Selected按ID回填单位/银行/账号并清空所选费用。新增成功关闭新增窗口，刷新选择列表，不自动替用户确认单位。
- Areas/FAM/Controllers/PaymentTypeController.cs：默认官费、第一页、10条；按ID倒序筛选分页。
- Areas/FAM/Views/PaymentType/List.cshtml：60%宽列表窗口、顶部查询/选择/新增、五列与底部分页/取消。
- Areas/FAM/Views/AP/Payment/Create.cshtml：四步横条，合同与客户信息三列两行；交款人、收款单位、开户行、账号、备注采用左标签右输入。

## 新系统和根因
ContractModals.tsx::ContractPaymentModal沿用旧的新建弹窗结构，仅换了外部容器；PaymentTypeCreateModal被当作主要入口。缺少真实列表选择、查询、分页及选择确认。上次属于交互链和前端对照遗漏，不是部署版本问题。
contract/payment-candidates读取SystemParameter/payment_type真实单位，_active_payment_type_rows还会隐藏银行/账号为空的旧记录；旧截图明确存在这种单位。候选显示与最终付款必填检查必须分开。

## 改动清单
- 新增ContractPaymentUnitPicker.tsx：独立选择模态框，默认官费、10条，按真实ID过滤排序分页，单项勾选，显式确认才回填；新增后留在选择列表。
- ContractModals.tsx：收款单位链接与只读名称打开选择框；移除主页面下拉和新增按钮，横排紧凑表单、只读申请日期、四段步骤条；费用选择列放回原表的本次支付后。
- financeActions.tsx：新增单位仅更新列表，不静默修改当前付款单位；更换单位清空选中费用和金额。
- core/finance.py与contract/router.py：仅合同候选允许返回银行/账号为空但有名称的启用单位；其他调用默认规则及最终付款校验不变。无需新路由或数据库迁移。
- 不修改真实单位资料、合同或财务记录；未申请单编号仍在真实提交后生成，未伪造编号。

## 检查与状态
CodeGraph已读取状态与入口关系；缺少的旧前端/控制器通过定向源码读取补齐。VibeHub查询modal dialog确认术语，未上传业务信息。
按直接问题规则执行本地构建、Python编译/应用加载和部署健康检查，不进行浏览器或业务测试。用户验收重点是点击收款单位、筛选翻页、取消不改值、选择后正确回填、新增后返回选择列表、页面布局。发布结果以版本回执和服务器队列为准，未获用户确认前不标记通过。

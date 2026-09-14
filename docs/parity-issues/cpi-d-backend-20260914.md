# CPI-D 发票数据契约实施记录

## 1. 清单原文与范围
- 用户原文：“这不能光对齐这一个后续的页面都要对齐 逻辑也要对齐了”。本轮用户已确认九项统一实施。
- D 支撑 CPI-01/02/03/04/06/08；只拥有 finance/router.py、core/finance.py、models_shared.py 和独立测试。本记录独立于 A/B 的原 CPI 文档，避免共同写入。
- 不涉及 Excel 行。本轮禁止浏览器、业务数据库、提交、推送、版本及部署；由主会话集成发布。

## 2. 图片证据
- 原 CPI 文档引用的两张付款单位图片不是本任务发票缺陷证据。发票差异来自已确认的源码审计；本轮无新增发票截图，不宣称页面验收。

## 3. 本轮重读旧实现
- 归档 SH.CRM.WEB/Areas/FAM/Controllers/InvoiceController.cs::InvoiceDetailCreate，76-118：同客户多合同费用查询，客户税号、开户行/账号、电话，联系地址优先注册地址。
- 同文件 InvoiceCreateUpdate，128-200：InvoiceServices 金额合计及逐 InvoiceObject 高开来源。
- Scripts/FAM/Invoice/FAM.Invoice.js，155-320：数量乘单价、服务项合计，服务名必填，税率/税额独立录入；未找到税额计算公式，不猜测含税/未税算法。
- Areas/FAM/Views/Invoice/InvoiceDetailCreate.cshtml，258-298：服务多行数量、单价、金额、税率、税额。
- 同级 SH.CRM.Service.Decompiled/Dchien.Legal.Service/Dchien/Legal/Service/FAM/Invoice/InvoiceService.cs::InvoiceCreateUpdate，37-155：逐条保存 InvoiceServices / InvoiceObjects，编辑替换明细并调整占用。本轮不复制旧空引用错误或加回合同审批前提。
- 已重读 finance-center-fc09/10/11-remediation.md：同客户合票、高开、部分占用必须保留。

## 4. 新实现与根因
- InvoiceApplicationInput.service_items 是未校验字典；model_dump 默认空列表会覆盖编辑原服务项。
- _validate_invoice_source_links 自动顺序分配但没有逐费金额输入；显式单合同限定须保留，仅混合来源不传单合同摘要。
- 通用 record GET 不补 invoice_objects，无法完整展示合同外部号和逐费到账/已开金额；客户参考分页有截断风险。
- 数据为 BusinessRecord.data 中 service_items、case_fee_ids、case_fee_allocations；无新表或迁移。

## 5. 精确实施清单
- [x] models_shared.py：统一数量、单价、金额与总额校验，保留服务扩展字段；新增 case_fee_allocations[{fee_id, amount}]，严格校验集合及总额。保留 model_fields_set，避免规范化误把未传列表变成已传空列表。
- [x] core/finance.py：显式分配与高开计算；复用既有金额投影，补授权范围内的费用/合同详情与客户资料。重复余额校验不依赖申请人能否看到其他占用发票；只读取关联费用的占用记录。
- [x] finance/router.py：保存编辑保留未传的多服务项及分配；末尾追加两个 GET，保持中部路由顺序以兼容 main 硬编码 slice。main 由 C 负责。
- [x] 独立隔离测试：数值校验、多来源、部分/高开分配、编辑回读、详情及候选授权与金额字段控制。
- 前端由 A/B 负责；合同路由/main/总交接由其他线程负责，不修改。

## 6. API 契约
- GET /finance/invoices/{invoice_id} 返回普通 record，data.service_items 全部原服务项；data.invoice_objects 每费用一行。
- invoice_objects 最终与 B 对齐：fee_id/fee_no/fee_type/fee_amount(原额)、allocation_amount/amount/invoice_amount(均为本次)、over_amount、available_before；contract_id/contract_record_id/contract_no/external_contract_no、case_id/case_record_id/case_no/case_title/customer/case_stage；received_amount/cashed_amount、issued_amount/invoiced_amount、remaining_invoice_amount。issued/invoiced 沿用 FC11 有效申请累计占用语义，不将其另算为仅已开票终态。
- 缺失或无权来源标 missing_or_forbidden，缺逐费分配标 allocation_missing；无明细的多费历史票不按总额猜分配。历史无 service_items 返回 []，不凭空构造服务行。金额字段权限隐藏为 null；无费用金额或到账金额来源也保留 null。
- GET /finance/invoice-context 参数：customer(精确客户名)、customer_no、customer_id、contract_ids(逗号分隔最多100)、invoice_id(仅本人/经理可编辑单)、keyword、page(默认1)、page_size(默认50/最大100)。必须指定客户、合同或编辑发票，空范围422；客户歧义409。
- context 返回 items(普通fee record，data含增强字段)、total/page/page_size、selected_items(当前编辑单完整已选费用)、customer_record、customer_defaults、customer_missing_or_forbidden。编辑 invoice_id 会排除本单占用后计算候选余额；不反写客户档案。
- 内存边界：SQL 在 finance 模块、客户精确值、权限及可选合同范围内按 id 游标每批 LIMIT 100；每批只读对应IDs再 hydration，保留当前返回页并累计有效候选 total。不是先加载全公司再 Python 分页。精确余额总数需扫描该客户匹配ID批次，不宣称为数据库端余额聚合或线上性能压测通过。
- helper `_invoice_fee_details(identity, db, ids=...)` 强制显式IDs，超过100拆批；SQL费用查询也带ID条件；关联发票、到账、退款按费用ID/案件关联预筛选后精确匹配。单页只选一条费用不代表该案只有一条费用：按全案费用计数阻断歧义的旧仅案号到账映射。
- C 消费同一 helper，最终检查其合同候选已把 remaining_invoice_amount 映射成 invoiceable_amount；提供 case_stage/case_title/case_type/court_name/hearing_lawyer/investigator/assistant/payer/payment_mode/received_date，有原来源才填值。D 不修改合同router/main。
- service_items：service_name、quantity、unit_price、amount、tax_rate(百分数)、tax_amount；金额=数量乘单价四舍五入到分，服务金额合计=amount。税额是旧页面独立输入，不推导未知公式。

## 7. 验证与状态
- `python -m unittest cpi_d_invoice_contract_test finance_invoice_row29_contract_test -q`：14/14 通过(本任务11项、已有FC09-11三项)，8.596秒。全部使用显式 sqlite+aiosqlite:///:memory:，不启动应用 lifespan、不使用业务 SessionLocal；dispose 后数据随内存引擎释放。
- 新测试覆盖服务数值及合计、扩展字段保留、分配集合/总额、多合同多服务编辑回读、HTTP路由、专用状态阻断、跨客户失败不创建发票、缺失来源、金额隐藏、未知金额不转0、逐费到账与歧义案号不误分配。空context拒绝；112条目标客户费用分页，另一客户110条未进入hydration，每批<=100。
- 首轮发现2个失败：模型赋值改变 fields_set(已修复)，隔离HTTP测试写错API前缀(改用settings.api_prefix)。复跑全部通过。
- `python -m py_compile app/models_shared.py app/core/finance.py app/areas/finance/router.py cpi_d_invoice_contract_test.py`、限定三个业务文件的 `git diff --check` 均通过。
- 精确文件：apps/api-server/app/models_shared.py；apps/api-server/app/core/finance.py；apps/api-server/app/areas/finance/router.py；apps/api-server/cpi_d_invoice_contract_test.py；本独立记录。无前端修改、无业务数据、无浏览器标签、无提交/推送/版本修改/发布。
- 主会话负责全量构建、菜单/API审计、main正式挂载和统一部署，本轮不以隔离router HTTP证明main集成完成。
- CodeGraph status 为最新；explore InvoiceApplicationInput 得到模型和调用面，_validate_invoice_source_links 得到具体函数，其他未覆盖投影通过 rg/定向读取补足。实施中已sync，交付前再次sync。
- VibeHub已解析脱敏短语data contract，得到“契约测试” https://vibe-hub.org/contract-testing；仅用于说明请求/响应约定测试，不作为业务证据。
- 线上资料完整性、真实角色页面、PostgreSQL 并发与统一部署仍未证明，留主会话及用户验收。

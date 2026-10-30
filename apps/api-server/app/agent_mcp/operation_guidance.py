"""基于原处理函数的操作说明，不推断业务规则或改变安全分类。"""

from copy import deepcopy
import inspect
import re

from fastapi.routing import APIRoute

from app.config import settings
from app.agent_mcp.parameter_guidance import SEMANTIC_GUIDANCE_MARKER, STRUCTURAL_GUIDANCE_MARKER


_CASE_DATES = (
    "source_from/source_to 仅筛选案件 data.source_date/source_at，不是线索提交时间；"
    "按线索提交时间统计不能使用这两个字段替代。"
)

# 键同时绑定方法、路径及处理函数，避免同名函数或路由别名套用业务说明。
_GUIDANCE = {
    ("GET", "/agent/system-skills/{skill_id}/resources", "read_system_skill_resource"): {
        "title": "读取系统技能参考资料",
        "purpose": "按当前选中系统技能的资料目录，读取固定上游版本的完整原文参考资料，不执行脚本。",
        "usage": ["path.skill_id 使用选中系统技能 ID；query.path 使用技能指令中列出的准确相对路径。",
                  "query.offset 从0开始，query.limit 最大16000字符；有 next_offset 时继续按返回偏移读取。"],
        "prerequisites": ["先读取本轮启用技能的 SKILL.md 原文，确定任务适用的参考资料。"],
        "limitations": ["仅允许已注册且未注销的系统技能；不读取服务器任意文件、业务附件或执行上游脚本。"],
        "search_terms": ["技能原文", "skill参考资料", "SKILL.md", "读取系统技能参考资料"],
    },
    ("POST", "/documents/court-service/intake", "intake_court_service"): {
        "title": "一键法院收文",
        "purpose": "收文助手首选，两步：先预览（下载文书、匹配唯一案件、列出将入库和回填的内容），用户确认后再入库（官方收文挂案件、回填法院案号和开庭时间法庭；缴费通知生成待确认官方费用草稿）。",
        "usage": ["第一次只填 body.link（短信或链接），返回 status=待确认入库 时把 case 和 plan 列给用户并询问是否入库。",
                  "用户确认后带 body.link、body.case_id（返回的 case.case_id）和 body.confirm=true 再调用一次才写入；用户不确认就不再调用。",
                  "返回 status=需要选择案件 时把 match.candidates 列给用户选，选定后带 case_id 预览再确认；status=系统内未登记该案 时停止并建议先建案。",
                  "返回 fees 中 status=待确认 的费用，向律师确认是否提交缴纳和设提醒，确认后调用“确认收文费用”。"],
        "prerequisites": ["用户发来送达链接即授权下载与收文；重复调用不会重复入库或重复建费用单。"],
        "limitations": ["只在唯一匹配时写入；不新建案件、不改案件阶段；开庭信息冲突或审级不明时只报告不回填。"],
        "search_terms": ["一键收文", "法院收文", "收文", "送达链接", "法院短信", "签收法院文书", "zxfw", "传票", "收文助手"],
    },
    ("POST", "/documents/court-service/fees/{fee_id}/confirm", "confirm_court_intake_fee"): {
        "title": "确认收文费用",
        "purpose": "律师确认后，把一键收文生成的官方费用草稿提交缴纳（自动匹配收款单位），并按最后缴费期限建提醒任务。",
        "usage": ["path.fee_id 填一键收文返回的 fees[].fee_id；body.remind 是否建提醒（默认是），body.remind_owner 提醒负责人账号（默认当前用户）。"],
        "prerequisites": ["必须先得到律师/用户明确同意提交缴纳。"],
        "limitations": ["只处理法院收文生成的费用单；已提交的不会重复提交，同名提醒不会重复建。"],
        "search_terms": ["确认收文费用", "提交缴纳", "诉讼费缴纳", "缴费提醒"],
    },
    ("POST", "/documents/court-service/fetch", "fetch_court_service_documents"): {
        "title": "下载法院送达文书",
        "purpose": "按法院短信里的送达链接，从人民法院在线服务下载全部文书，保存为当前用户的未关联附件并识别收文要素（案号、法院、当事人、开庭、缴费等）。",
        "usage": ["body.link 填短信里完整的 https://zxfw.court.gov.cn/... 链接，连同短信正文粘贴也可以。",
                  "返回的 documents[].attachment_id 作为“上传官方收文”的 files.file；fields 为识别结果，需人工核对项要复核。"],
        "prerequisites": ["用户发来送达链接即授权下载；先加载“法院收文”技能，按技能匹配案件后再收文入库。"],
        "limitations": ["链接不完整或过期时法院接口会拒绝；同一文书重复送达时复用已下载附件，不重复保存。",
                        "扫描件可能没有正文，识别结果为空时不得按文件名猜测要素。"],
        "search_terms": ["法院送达", "收文", "签收法院文书", "下载法院文书", "送达链接", "zxfw", "传票", "法院短信"],
    },
    ("POST", "/documents/official/upload", "upload_official_document"): {
        "title": "上传官方收文",
        "purpose": "把法院等机关送达的文书作为官方收文入库：挂到案件、进入收文列表；案件未登记法院案号时回填。",
        "usage": ["files.file 填已有附件 ID（如“下载法院送达文书”返回的 attachment_id）。",
                  "body.case_id 填已唯一匹配的案件 ID，body.court_case_no 填文书官方案号，body.document_date 填落款日期，body.remark 填文书类型。",
                  "不传 case_id 时，文件名必须是“系统案号_法院案号”且与案件登记的法院案号一致。"],
        "prerequisites": ["先按官方案号或当事人匹配到唯一案件；多个候选必须让用户选择。"],
        "limitations": ["已登记的法院案号不覆盖；单个文件不超过 20MB。"],
        "search_terms": ["官方收文", "收文入库", "上传收文", "法院文书上传", "收文"],
    },
    ("POST", "/cases", "create_case"): {
        "title": "从合同新建案件",
        "purpose": "从有效合同新建案件，客户、部门和合同编号以合同资料为准；参数齐全后直接执行，变更留痕可还原。",
        "usage": ["body 使用 CaseCreateInput；先向用户收集齐必填信息再提交，缺什么就问什么，不要用默认值或猜测补空。"],
        "prerequisites": [
            "所有案件类型都要：合同记录、案件名称、案件类型、经办律师。",
            "法律顾问案件还要：顾问类型、顾问期限（开始日期和结束日期，结束不早于开始）。",
            "民事、刑事、行政、仲裁案件还要：案由或罪名、客户诉讼地位；这些案件不能填顾问类型和顾问期限。",
            "提交时如果返回“缺少或不合规的信息”，把清单原样告诉用户并等待补充，不要重复提交同样内容。",
        ],
        "limitations": ["新建案件阶段只能是待分配；客户资料缺组织类型或证件号时需先补齐客户资料。"],
        "search_terms": ["新建案件", "创建案件", "法律顾问案件", "立案"],
    },
    ("POST", "/cases/search", "search_ordinary_cases"): {
        "title": "检索普通案件",
        "purpose": "按原案件权限和筛选条件分页查询普通案件，返回匹配总数和阶段分布。",
        "usage": ["body 使用 CounselCaseSearchInput；handling_lawyer 筛选案件经办律师姓名，page/page_size 控制明细分页。"],
        "prerequisites": ["人员条件取自实际人员选项或可见案件字段；先明确查询范围及日期口径。"],
        "limitations": [_CASE_DATES, "phase_counts 在阶段筛选前聚合，total 在阶段筛选后计数，不能混用。"],
        "search_terms": ["案件检索", "普通案件", "经办案件", "承办案件", "主办案件"],
    },
    ("POST", "/cases/counsel/search", "search_counsel_cases"): {
        "title": "检索法律顾问案件",
        "purpose": "在原可见范围和筛选条件下分页查询法律顾问案件，返回总数和页数。",
        "usage": ["body 使用 CounselCaseSearchInput；page/page_size 控制明细分页。"],
        "prerequisites": ["先明确法律顾问案件范围及人员、日期条件。"],
        "limitations": [_CASE_DATES, "items 仅是当前页，不可据其条数宣称全量总数。"],
        "search_terms": ["法律顾问案件", "顾问案件查询"],
    },
    ("POST", "/cases/statistics", "case_statistics"): {
        "title": "案件全量统计",
        "purpose": "统计当前账号可见且匹配条件的全部案件，返回总数、阶段分布和案件类型分布。",
        "usage": ["body 使用原案件检索模型；统计忽略 page/page_size，不以当前页明细数量代替总数。"],
        "prerequisites": ["先明确案件范围 scope、案件类型、人员及日期口径，再按原检索模型填写条件。"],
        "limitations": [_CASE_DATES, "默认普通列表排除法律顾问；global 或明确案件类型按原检索权限和规则执行。"],
        "search_terms": ["案件统计", "多少件", "案件数量", "阶段分布", "案件类型分布"],
    },
    ("POST", "/customers", "create_customer"): {
        "title": "新建客户",
        "purpose": "新建一个客户档案；参数齐全后直接执行，变更留痕可还原。",
        "usage": ["body 使用 CustomerCreateInput；先向用户收集齐必填信息再提交，缺什么就问什么，不要用默认值或猜测补空。"],
        "prerequisites": [
            "必填：客户名称（不能与已有客户重名）、组织类型（公司企业/事业单位/机关团体/个人/个体工商户/其他）。",
            "证件号必填：组织类型是个人时填身份证号，其他类型填统一社会信用代码，都是 18 位，不能和其他客户重复。",
            "客户类型要从 GET /customers/reference-options 返回的启用类型里选；不填时按“客户”。",
            "提交时如果返回“缺少或不合规的信息”，把清单原样告诉用户并等待补充，不要重复提交同样内容。",
        ],
        "limitations": ["提交前先用客户列表确认没有同名客户；已有客户不要重复新建。"],
        "search_terms": ["新建客户", "创建客户", "客户建档"],
    },
    ("GET", "/customers", "list_customers"): {
        "title": "查询客户列表",
        "purpose": "按客户页面范围、客户名称、客户类型和负责人查询客户业务记录。",
        "usage": ["query.scope 选择原客户页面范围；customer_name 筛选名称，manager 筛选负责人，page/page_size 分页。"],
        "prerequisites": ["先 GET /customers/reference-options 获取当前启用的 customer_types，再填写 customer_type。"],
        "limitations": ["客户来自客户业务记录，不是 /law-firms 的律所档案；范围仍受菜单及数据权限限制。"],
        "search_terms": ["客户", "客户列表", "客户负责人"],
    },
    ("GET", "/law-firms", "list_law_firms"): {
        "title": "查询律所档案列表",
        "purpose": "查询律所档案，可按编号、名称、电话、邮箱或律所类型关键词筛选。",
        "usage": ["query.keyword 填搜索词；include_inactive 默认 false，仅返回启用档案；page/page_size 分页。"],
        "prerequisites": ["原接口要求管理员身份；从返回项取得 law_firm_id 后再读取详情或联系人。"],
        "limitations": ["律所使用 LawFirm 档案，不是客户列表；客户 ID 不能直接作为 law_firm_id。"],
        "search_terms": ["律所", "律师事务所", "律所档案"],
    },
    ("GET", "/law-firms/{law_firm_id}", "get_law_firm"): {
        "title": "查看律所档案详情",
        "purpose": "读取指定律所档案、执照信息及联系人。",
        "usage": ["path.law_firm_id 使用律所列表返回的真实 ID。"],
        "prerequisites": ["先查询 /law-firms 核对目标；原接口要求管理员身份。"],
        "limitations": ["只读取律所，不查询客户详情，不能混用客户 ID。"],
        "search_terms": ["律所详情", "律所联系人", "律所执照"],
    },
    ("GET", "/finance/incoming-payments", "list_incoming_payments"): {
        "title": "查询银行回款到账",
        "purpose": "查询银行收入回款及认领、分配状态，返回当前筛选结果及汇总。",
        "usage": ["query 可按 payment_status、keyword、bank_source、view、filters 筛选，并用 page/page_size 分页。"],
        "prerequisites": ["先明确财务中心 finance_scope 和回款查询视图；筛选字段及枚举以原参数定义为准。"],
        "limitations": ["这是回款收入，不是对外付款支出，也不是开票申请；金额按当前账号字段权限展示。"],
        "search_terms": ["回款", "到账", "收入", "银行回款", "认领"],
    },
    ("POST", "/finance/incoming-payments", "create_incoming_payment"): {
        "title": "登记银行回款到账",
        "purpose": "登记银行收入到账记录；默认待认领，claim 为真时按原校验自动认领到客户。",
        "usage": ["body 填实际到账日期、金额、付款人及银行流水等信息；合同号和案号使用实际查询结果。"],
        "prerequisites": ["原接口要求管理员或部门负责人；客户从 /finance/customer-options 查询，并核对关联案件与合同。"],
        "limitations": ["写入回款记录，不执行对外付款或开票；重复银行流水号及关联不一致会被原接口拒绝。"],
        "search_terms": ["登记回款", "登记到账", "录一笔收入", "新增回款"],
    },
    ("GET", "/finance/customer-options", "list_finance_customer_options"): {
        "title": "查询回款登记客户选项",
        "purpose": "按关键词查询回款登记可选的未回收系统客户，返回 ID、名称和编号。",
        "usage": ["query.keyword 按客户名称或编号搜索，原接口最多返回 50 项。"],
        "prerequisites": ["原接口要求管理员或部门负责人。"],
        "limitations": ["查询客户业务记录，不返回诉讼当事人或律所档案。"],
        "search_terms": ["回款客户", "到账客户选项"],
    },
    ("POST", "/finance/incoming-payments/{payment_id}/claim", "claim_incoming_payment"): {
        "title": "认领银行回款",
        "purpose": "把银行到账认领到可见客户，记录认领人并转为待分配。",
        "usage": ["path.payment_id 使用到账记录 ID，body.customer 使用真实客户名称。"],
        "prerequisites": ["先查询到账记录和可见客户，核对财务中心、状态及已分配金额。"],
        "limitations": ["仅待认领或待分配且尚未发生分配的到账可认领；不执行付款或开票。"],
        "search_terms": ["认领回款", "认领到账"],
    },
    ("POST", "/finance/incoming-payments/{payment_id}/allocate", "allocate_incoming_payment"): {
        "title": "分配银行回款",
        "purpose": "把已认领银行到账分配至真实费用及应收计划，更新回款分配和相关收款数据。",
        "usage": ["path.payment_id 使用回款 ID；body.allocations 根据原候选及真实余额填写，不猜费用或应收计划 ID。"],
        "prerequisites": ["先查询到账详情及该到账的 allocation-candidates，核对认领客户、费用关联及财务中心。"],
        "limitations": ["须已认领且状态为待分配或部分分配；分配金额不能超过未分配余额，具体费用及退款分支校验由原处理函数执行。", "分配回款不等于对外付款或开票。"],
        "search_terms": ["分配回款", "分派回款", "分配到账"],
    },
    ("GET", "/finance/payment-packages", "list_internal_payment_packages"): {
        "title": "查询付款包列表",
        "purpose": "按付款包范围、状态、编号、收款人及付款日期查询付款包业务记录。",
        "usage": ["query.package_scope 使用原模式枚举，status 使用原状态筛选；指定 page_size 时分页。"],
        "prerequisites": ["先明确普通或内部付款包及所需状态；不凭状态名称推断已实际支付。"],
        "limitations": ["只查询付款支出侧记录，不查询银行回款收入，也不创建或核销付款包。"],
        "search_terms": ["付款", "支出", "付款包", "付款记录"],
    },
    ("POST", "/finance/fees", "create_finance_fee"): {
        "title": "新增费用草稿",
        "purpose": "登记财务费用草稿，保存费用分类、关联案件合同、经办人和金额。",
        "usage": ["body 使用原 FinanceFeeInput；费用分类、经办人及案件合同取自真实查询结果。"],
        "prerequisites": ["先查案件、关联合同和费用主数据；草稿保存后如需提交，先查询该费用 readiness。"],
        "limitations": ["新增费用不是付款、回款或开票；本步骤仅保存草稿，不代表审批通过或支付完成。", "不推断合同金额门槛、费用比例或编号。"],
        "search_terms": ["新增费用", "登记费用", "录一笔费用", "费用草稿", "经办"],
    },
    ("GET", "/finance/fees/{fee_id}/readiness", "finance_fee_readiness"): {
        "title": "检查费用提交准备情况",
        "purpose": "读取指定财务费用的原业务准备检查结果。",
        "usage": ["path.fee_id 使用真实财务费用记录 ID。"],
        "prerequisites": ["先查询费用并核对目标及当前状态。"],
        "limitations": ["只检查，不提交、审批、付款或开票。"],
        "search_terms": ["费用准备检查", "费用提交条件"],
    },
    ("POST", "/finance/invoices", "create_invoice_application"): {
        "title": "新增开票申请草稿",
        "purpose": "根据真实案件费用及分配来源创建发票申请草稿。",
        "usage": ["body 使用 InvoiceApplicationInput，来源费用和分配信息须与实际查询结果一致。"],
        "prerequisites": ["先查询来源案件费用及关联合同；专用发票需注册地址、注册电话、开户银行和银行账号。"],
        "limitations": ["创建申请草稿不等于已经开票，不执行付款或回款；归档或终止合同被阻断，平台合同与律所合同不能合并开票。"],
        "search_terms": ["开票申请", "发票申请", "新增发票"],
    },
    # 2026-10-30 按操作手册对齐（docs/业务工具/02 G1–G12）。
    ("POST", "/contracts", "create_contract_draft"): {
        "title": "新建合同草稿（可同时挂合同附件）",
        "purpose": "新建合同草稿（页面“合同新建”第一步）。合同类别、收费模式、合同主体、外部合同号、金额、签订日期可用具名参数，也可放 data（data.type=合同类别），服务器归并。",
        "usage": ["customer 填客户档案名称；attachment_ids 填本人已上传、未关联业务的附件 ID，保存后自动挂为“合同附件”。",
                  "随后用 POST /contracts/{contract_id}/submit 选审批人提交审批。"],
        "prerequisites": ["客户档案已存在；合同名称不与未删除、未归档合同重名。"],
        "limitations": ["只建草稿，不提交审批；普通账号的负责人、部门由服务器改为本人。"],
        "search_terms": ["新建合同", "合同新建", "合同草稿"],
    },
    ("POST", "/contracts/{contract_id}/submit", "submit_contract"): {
        "title": "提交合同审批",
        "purpose": "合同草稿选审批人提交审批（页面“提交审核”），可同步申请用印。",
        "usage": ["approvers 只能取 GET /contracts/approver-settings 返回 selected=true 的 username。"],
        "prerequisites": ["合同须至少已有一份“合同附件”。", "审批人须在合同审批人名单（管理员在审批人设置里勾选，且有员工档案）。"],
        "limitations": ["提交后进入审批中，审批结论须审批人在 OA 网页确认。"],
        "search_terms": ["提交合同", "合同审批", "提交审核"],
    },
    ("POST", "/contracts/{contract_id}/investigation", "create_contract_investigation"): {
        "title": "按合同新建调查任务",
        "purpose": "案源人/品牌管理人在合同下发布调查任务（页面“新建调查任务”）。",
        "usage": ["授权范围用 authorization_range（旧名 region），授权区域用 authorization_area（旧名 authorization_scope），两套名字等价。"],
        "prerequisites": ["合同不能是草稿。", "管理员须已在人员管理配置“调查任务分配人员”；owner 留空或填该调查主管。"],
        "limitations": ["只建父调查任务，子任务由调查主管在“待我分配的调查任务”新增。"],
        "search_terms": ["新建调查任务", "发布调查任务", "调查任务"],
    },
    ("POST", "/investigations/records", "create_investigation_record"): {
        "title": "新建调查线索/调查任务记录",
        "purpose": "module=clue 时新建调查线索（页面“新增线索”，保存为草稿）；线索字段可用具名参数（sales_channel、product、shop_name…）或放 data。",
        "usage": ["线索：serial_no、title 传空字符串，source_task_id 填本人负责的调查任务/子任务 ID；attachment_ids 挂“调查线索附件”。",
                  "暂存后用 POST /investigations/clues/{clue_id}/submit 提交审批。"],
        "prerequisites": ["只能在本人负责的调查任务下建线索；需有线索录入岗位权限。"],
        "limitations": ["一条线索只对应一个品牌、一个侵权产品；公证、证据须走线索专用入口。"],
        "search_terms": ["新增线索", "调查线索", "线索录入"],
    },
    ("POST", "/cases/create-complete", "create_case_complete"): {
        "title": "建案一步到位（新建+当事人+司法机关/完成）",
        "purpose": "一次完成新建案件页面的三步：新建案件 → 当事人 → 法律顾问“完成”/其他案件司法机关信息并完成。完成后案件进入“待立案审批”。",
        "usage": ["litigants 的 *_identities 每项须有名称、组织类型、证件号；非顾问案件至少一名被告。",
                  "judicial 填一审法院等已知信息（可空）。"],
        "prerequisites": ["合同可建案（GET /cases/eligible-contracts）；当前账号有该案件类型的新建权限。"],
        "limitations": ["中途失败时已建案件保留在对应步骤并返回 case_id，勿重复新建；立案审批须案件主管在网页确认。"],
        "search_terms": ["新建案件", "建案", "一步建案", "从合同新建案件"],
    },
    ("PUT", "/cases/{case_id}/judicial", "update_case_judicial"): {
        "title": "新建案件第三步：司法机关信息并完成",
        "purpose": "只用于建案流程中（当事人已填后）写司法机关/法院信息并完成新建。",
        "usage": ["建案后改法院信息请用 PUT /cases/{case_id}/court-info。"],
        "prerequisites": ["案件处于“当事人已填”步骤（先 PUT /cases/{case_id}/litigants）；法律顾问案件不用此步。"],
        "limitations": ["已完成新建的案件调用会被拒绝并提示改用 court-info。"],
        "search_terms": ["司法机关", "建案法院信息"],
    },
    ("PUT", "/cases/{case_id}/court-info", "update_case_court_info"): {
        "title": "修改法院信息（建案后）",
        "purpose": "页面“修改法院信息”：维护一审/二审/再审法院、案号、法庭、法官、书记员、立案/开庭/判决日期，是付款“法院要素”的入口。",
        "usage": ["字段按审级加前缀：first_court_*、second_court_*、retrial_court_*；开庭日期时间格式 YYYY-MM-DD HH:mm:ss。"],
        "prerequisites": ["案件已完成新建；当前账号有法院信息维护权限。"],
        "limitations": ["归档锁定或已合并的案件不能修改。"],
        "search_terms": ["修改法院信息", "法院要素", "开庭时间", "法院案号"],
    },
    ("POST", "/cases/batch-update", "batch_update_cases"): {
        "title": "批量修改案件人员与阶段",
        "purpose": "页面“批量更改”：开庭律师、经办律师、律师助理、案源人、案件阶段、诉讼标的；也是付款“人员要素”的入口（单案传一个 case_id）。",
        "usage": ["case_ids 或 case_nos 指定案件；只传要改的字段。"],
        "prerequisites": ["案件已完成新建且已通过案件主管的立案审批。"],
        "limitations": ["归档中的案件不能修改。"],
        "search_terms": ["批量更改", "人员要素", "修改经办律师", "修改案件阶段"],
    },
}


def get_operation_guidance(route: APIRoute, method: str) -> dict:
    """返回稳定英文键；没有处理函数证据时只提供原路由事实。"""
    path = route.path.removeprefix(settings.api_prefix)
    key = (method.upper(), path, route.endpoint.__name__)
    original = "\n".join(dict.fromkeys(filter(None, (
        route.summary, route.description, inspect.getdoc(route.endpoint),
    ))))
    corrupted = bool(re.search(r"[\ufffd\ue000-\uf8ff]|锟斤拷|烫烫|屯屯|[ÃÂ][\x80-\xff]", original))
    guidance = {
        "documentation_status": "route_documented" if original and not corrupted else "unknown",
        "documentation_gaps": ["尚未逐项核实该端点的业务前置条件、状态流转及参数来源；原路由说明不等于完整业务核验。"],
        "purpose": original.strip() if original and not corrupted else (
            f"原接口 {method.upper()} {route.path}，处理函数 {route.endpoint.__name__}；未提供可核实的专项用途说明。"
        ),
        "usage": ["按 inputSchema 的 path/query/body/files 分组填写；类型、必填项和约束使用原接口定义。"],
        "prerequisites": [],
        "limitations": ["未提供专项业务前置条件或参数取值来源时，须查询对应业务资料，不能推断审批规则、金额规则或关联编号。"],
        "search_terms": [],
    }
    if key in _GUIDANCE:
        guidance.update(deepcopy(_GUIDANCE[key]))
        guidance["documentation_status"] = "source_verified"
        guidance["documentation_gaps"] = ["仅核实本说明列明的用途和边界；参数逐字段覆盖另见 parameter_documentation，不代表全流程验收。"]
    return guidance


def parameter_documentation(schema: dict) -> dict:
    """按实际字段出现位置统计说明覆盖；结构约束说明不算业务核证。"""
    counts = {"total": 0, "source_verified": 0, "documented": 0, "unknown": 0}
    gaps = []

    def visit(node, path=()):
        if not isinstance(node, dict):
            return
        for name, value in node.get("properties", {}).items():
            field_path = (*path, name)
            if path and isinstance(value, dict):
                description = value.get("description", "")
                original, marker, semantic = description.partition(SEMANTIC_GUIDANCE_MARKER)
                semantic = semantic.partition(STRUCTURAL_GUIDANCE_MARKER)[0] if marker else ""
                # 结构约束不算业务说明，只有带明确源码证据的语义段计为已核实。
                if "证据：" in semantic:
                    status = "source_verified"
                elif original.strip():
                    status = "documented"
                else:
                    status = "unknown"
                counts["total"] += 1
                counts[status] += 1
                if status == "unknown":
                    gaps.append({"field": ".".join(field_path), "documentation_status": status})
            visit(value, field_path)
        for keyword in ("anyOf", "oneOf", "allOf"):
            for branch in node.get(keyword, []):
                visit(branch, path)
        visit(node.get("items"), (*path, "[]"))
        for name, definition in node.get("$defs", {}).items():
            visit(definition, ("$defs", name))

    visit(schema)
    return {**counts, "gaps": gaps}

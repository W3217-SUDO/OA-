"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.dependencies import (
    CaseFileTypeFeeTypeRelation, CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation, LegacyCaseTaskHistoryFile, LegacyCaseTaskHistoryMessage,
    LegacyCaseTaskHistoryNode, LegacyCaseTaskHistoryNodeParticipant, LegacyCaseTaskHistoryNotification, LegacyCaseTaskHistoryReadReceipt, Path,
    ZoneInfo, asyncio, create_case_agent_runtime, date, logging,
    re, settings, timedelta,
)


logger = logging.getLogger("app.main")


case_agent_runtime = create_case_agent_runtime(
    runtime_backend=settings.agent_runtime_backend,
    enabled=settings.langgraph_enabled,
    database_url=settings.database_url,
    checkpoint_url=settings.langgraph_checkpoint_url,
    api_base_url=settings.langgraph_api_base_url,
    api_key=settings.langgraph_api_key,
    model_provider=settings.langgraph_model_provider,
    model=settings.langgraph_model,
    max_concurrency=settings.langgraph_max_concurrency,
    harness_base_url=settings.deepseek_harness_base_url,
    harness_provider=settings.deepseek_harness_provider,
    harness_agent_preset=settings.deepseek_harness_agent_preset,
    harness_workspace=settings.deepseek_harness_workspace,
    harness_timeout_seconds=settings.deepseek_harness_timeout_seconds,
)


PERSON_NAME_PLACEHOLDER = "【待补充中文姓名】"


PERSON_NAME_NON_PERSON_MARKERS = (
    "经理", "总监", "主管", "主任", "专员", "助理", "顾问", "律师", "合伙人",
    "员工", "劳务", "部门", "范围", "管理员", "管理者", "审批", "负责人", "人员", "人事",
)


CASE_CREATE_PERMISSION_BY_TYPE = {
    "民事案件": "case-new-civil",
    "刑事案件": "case-new-criminal",
    "行政案件及国家赔偿": "case-new-administrative",
    "法律顾问": "case-new-counsel",
    "仲裁": "case-new-arbitration",
}


CASE_CREATABLE_TYPES = {"民事案件", "刑事案件", "行政案件及国家赔偿", "法律顾问", "仲裁"}


CIVIL_CASE_TYPES = {"民事案件", "民事争议", "民事"}


NORMAL_CASE_BASIC_TYPES = CIVIL_CASE_TYPES | {"刑事案件", "行政案件及国家赔偿"}


CONTRACT_APPROVED_STATUS = "审批通过"


CASE_SOURCE_CONTRACT_STATUSES = {"审批中", CONTRACT_APPROVED_STATUS, "已完成"}


REQUIRED_SEAL_ASSETS = (
    ("YZ-HT-001", "合同章", "行政部保险柜 A01"),
    ("YZ-GZ-001", "公章", "行政部保险柜 A02"),
    ("YZ-SH-001", "所函专用章", "行政部保险柜 A03"),
    ("YZ-FR-001", "法人章", "行政部保险柜 A04"),
    ("YZ-FP-001", "发票章", "财务部保险柜 F01"),
    ("YZ-CW-001", "财务专用章", "财务部保险柜 F02"),
    ("YZ-CS-001", "财务三排章", "财务部保险柜 F03"),
)


REQUIRED_SEAL_TYPES = {seal_type for _, seal_type, _ in REQUIRED_SEAL_ASSETS}


SEAL_USE_TYPES = {"案件用印", "合同用印", "行政用印"}


SEAL_APPLICATION_FILE_CATEGORY = "用印文件"


SEAL_STAMPED_FILE_CATEGORY = "盖章文件"


ADMINISTRATIVE_CLIENT_POSITIONS = {"原告/申请人", "被告/被申请人", "第三人"}


CASE_CREATE_PERMISSION_KEYS = list(CASE_CREATE_PERMISSION_BY_TYPE.values())


CASE_CREATE_STATUS_ALIASES = {"新案待分配": "新案待分配", "待分配": "新案待分配"}


CASE_CLIENT_POSITIONS_BY_TYPE = {
    "民事案件": {"原告/申请人", "被告/被申请人", "第三人"},
    "刑事案件": {"被告人/犯罪嫌疑人", "被害人"},
    "行政案件及国家赔偿": {"原告/申请人", "被告/被申请人", "第三人"},
    "仲裁": {"原告/申请人", "被告/被申请人", "第三人"},
}


CRIMINAL_JUDICIAL_PREFIXES = ("public_security_", "first_procuratorate_", "second_procuratorate_", "retrial_procuratorate_")


COURT_JUDICIAL_KEYS = {
    "court", "court_case_no", "courtroom", "judge", "clerk", "judge_phone", "filing_date", "hearing_date", "hearing_time",
    "first_court_name", "first_court_case_no", "first_court_courtroom", "first_court_judge", "first_court_clerk", "first_court_filing_date", "first_court_hearing_date",
    "second_court_name", "second_court_case_no", "second_court_courtroom", "second_court_judge", "second_court_clerk", "second_court_filing_date", "second_court_hearing_date",
    "execution_court_name", "execution_court_case_no", "execution_court_courtroom", "execution_court_judge", "execution_court_clerk", "execution_court_filing_date", "execution_court_hearing_date",
    "retrial_court_name", "retrial_court_case_no", "retrial_court_courtroom", "retrial_court_judge", "retrial_court_clerk", "retrial_court_filing_date", "retrial_court_hearing_date",
}


DEFAULT_SYSTEM_MENUS = [
    ("dashboard", "", "控制台", "dashboard", 0),
    ("agent-center", "", "智能体中心", "robot", 5),
    ("seal", "", "用印中心", "file-text", 10), ("seal-my", "seal", "我的用印申请", "", 11), ("seal-audit", "seal", "用印审核", "", 12), ("seal-admin", "seal", "行政用印", "", 13),
    ("task", "", "事务中心", "file-text", 20), ("task-my", "task", "我的任务", "", 21), ("task-dept", "task", "部门任务", "", 22), ("task-company", "task", "公司任务", "", 23), ("vip-tasks", "task", "VIP任务", "", 24),
    ("customer", "", "客户管理", "team", 30), ("customer-new", "customer", "新建客户", "", 31), ("customer-mine", "customer", "我的客户", "", 32), ("customer-recycle", "customer", "个人回收站", "", 33), ("customer-dept", "customer", "部门客户", "", 34), ("customer-dept-recycle", "customer", "部门回收站", "", 35), ("customer-company", "customer", "公司客户", "", 36), ("customer-public", "customer", "公海客户", "", 37), ("customer-shared", "customer", "我的共享客户", "", 38), ("customer-recent-contact", "customer", "最近联系的客户", "", 39), ("customer-recent-update", "customer", "最近更新的客户", "", 40), ("customer-company-recycle", "customer", "公司回收站", "", 41), ("customer-conflict", "customer", "客户利益检索", "", 42),
    ("contract", "", "合同中心", "file-text", 50), ("contract-new", "contract", "合同新建", "", 51), ("contract-mine", "contract", "我的合同", "", 52), ("contract-audit", "contract", "合同审批", "", 53), ("contract-dept", "contract", "部门合同", "", 54), ("contract-company", "contract", "公司合同", "", 55), ("contract-receivable", "contract", "应收款", "", 56), ("contract-archive", "contract", "合同归档", "", 58),
    ("contract-recycle", "contract", "合同回收站", "", 57),
    ("case", "", "案件中心", "file-text", 60), ("case-new", "case", "新建案件", "", 61), ("case-mine", "case", "我的案件", "", 62), ("case-dept", "case", "部门案件", "", 63), ("case-company", "case", "公司案件", "", 64), ("case-files", "case", "案件文件", "", 65), ("case-archive", "case", "案件归档审核", "", 66),
    ("ipr", "", "知识产权中心", "file-text", 67), ("ipr-patent", "ipr", "专利案件", "", 1), ("ipr-trademark", "ipr", "商标案件", "", 2), ("ipr-review", "ipr", "知识产权立案审核", "", 3), ("ipr-office-files", "ipr", "知识产权官文", "", 4), ("ipr-custom-file-import", "ipr", "案件自定义文件导入", "", 5),
    ("ipr-source-person", "ipr", "我是案源人", "", 6), ("ipr-procurator", "ipr", "我是代理人", "", 7), ("ipr-copywriter", "ipr", "我是撰稿人", "", 8), ("ipr-officer", "ipr", "我是处理人", "", 9), ("ipr-business-owner", "ipr", "我是案件管理人", "", 10),
    ("investigation", "", "调查大厅", "search", 70), ("clue", "investigation", "我的调查线索", "", 71), ("notary", "investigation", "公证管理", "", 72), ("evidence", "investigation", "证据管理", "", 73),
    ("documents", "", "收发文台", "file-text", 80), ("documents-official", "documents", "官文收文", "", 1), ("documents-outgoing", "documents", "正式发文", "", 2), ("documents-my", "documents", "我的收文", "", 3), ("documents-company", "documents", "公司收文", "", 4), ("documents-register", "documents", "收发文登记", "", 84), ("documents-files", "documents", "文件附件", "", 85), ("documents-template", "documents", "文书模板", "", 86), ("documents-agent", "documents", "AI 智能文档", "", 87), ("documents-archive", "documents", "归档材料", "", 88),
    ("finance", "", "财务中心", "file-text", 90),
    ("platform-finance", "", "平台财务中心", "bank", 100),
    ("user-center", "", "用户中心", "user", 110), ("user-messages", "user-center", "消息通知", "", 111), ("user-communications", "user-center", "沟通日志", "", 112), ("user-account", "user-center", "账户管理", "", 113),
    ("hr", "", "人事中心", "team", 120), ("hr-new", "hr", "新建员工", "", 1), ("hr-all", "hr", "员工管理", "", 2), ("hr-departments", "hr", "部门管理", "", 3), ("hr-roles", "hr", "角色管理", "", 4), ("hr-performance", "hr", "绩效管理", "", 5),
    ("system", "", "系统中心", "user", 130), ("system-parameters", "system", "系统参数", "", 1), ("system-management", "system", "系统管理", "", 2),
    ("warehouse", "", "仓库管理", "file-text", 140), ("warehouse-list", "warehouse", "仓库一览表", "", 1), ("reports", "", "报表中心", "dashboard", 150),
]


DEFAULT_SYSTEM_MENUS += [
    ("seal-my-pending", "seal-my", "待审批", "", 1), ("seal-my-stamping", "seal-my", "待用印", "", 2), ("seal-my-used", "seal-my", "已用印", "", 3), ("seal-my-refused", "seal-my", "已拒绝", "", 4), ("seal-my-withdrawn", "seal-my", "已撤回", "", 5),
    ("seal-audit-pending", "seal-audit", "待审批用印", "", 1), ("seal-audit-stamping", "seal-audit", "已审待用印", "", 2), ("seal-audit-refused", "seal-audit", "已拒绝用印", "", 3),
    ("seal-admin-pending", "seal-admin", "待用印", "", 1), ("seal-admin-used", "seal-admin", "已用印", "", 2), ("seal-admin-query", "seal-admin", "用印查询", "", 3),
    ("task-my-created", "task-my", "我发起的任务", "", 1), ("task-my-accepted", "task-my", "我接受的任务", "", 2), ("task-my-collaborating", "task-my", "我协作的任务", "", 3), ("task-my-unread", "task-my", "未读新消息的任务", "", 4),
    ("task-dept-created", "task-dept", "部门发起的任务", "", 1), ("task-dept-accepted", "task-dept", "部门接受的任务", "", 2), ("task-dept-collaborating", "task-dept", "部门协作的任务", "", 3),
    ("task-company-created", "task-company", "公司发起的任务", "", 1), ("task-company-accepted", "task-company", "公司接受的任务", "", 2), ("task-company-collaborating", "task-company", "公司协作的任务", "", 3),
    ("contract-audit-pending", "contract-audit", "待审批合同", "", 1), ("contract-audit-refused", "contract-audit", "已驳回合同", "", 2), ("contract-audit-approved", "contract-audit", "已审批合同", "", 3),
    ("contract-receivable-mine", "contract-receivable", "我的应收款", "", 1), ("contract-receivable-dept", "contract-receivable", "部门应收款", "", 2), ("contract-receivable-company", "contract-receivable", "公司应收款", "", 3), ("contract-receivable-detail", "contract-receivable", "应收款明细", "", 4),
    ("case-new-civil", "case-new", "民事争议", "", 1), ("case-new-criminal", "case-new", "刑事案件", "", 2), ("case-new-administrative", "case-new", "行政案件及国家赔偿", "", 3), ("case-new-counsel", "case-new", "法律顾问", "", 4), ("case-new-arbitration", "case-new", "仲裁", "", 5),
    ("case-mine-civil", "case-mine", "民事争议", "", 1), ("case-mine-criminal", "case-mine", "刑事案件", "", 2), ("case-mine-administrative", "case-mine", "行政案件及国家赔偿", "", 3), ("case-mine-counsel", "case-mine", "法律顾问", "", 4), ("case-mine-arbitration", "case-mine", "仲裁", "", 5), ("case-mine-schedule", "case-mine", "我的案件开庭排期", "", 6), ("case-mine-execution", "case-mine", "执行案件", "", 7), ("case-mine-unclaimed", "case-mine", "未申请提成的到账案件", "", 8),
    ("case-dept-civil", "case-dept", "民事争议", "", 1), ("case-dept-criminal", "case-dept", "刑事案件", "", 2), ("case-dept-administrative", "case-dept", "行政案件及国家赔偿", "", 3), ("case-dept-counsel", "case-dept", "法律顾问", "", 4), ("case-dept-arbitration", "case-dept", "仲裁", "", 5), ("case-dept-schedule", "case-dept", "部门案件开庭排期", "", 6),
    ("case-company-civil", "case-company", "民事争议", "", 1), ("case-company-criminal", "case-company", "刑事案件", "", 2), ("case-company-administrative", "case-company", "行政案件及国家赔偿", "", 3), ("case-company-counsel", "case-company", "法律顾问", "", 4), ("case-company-arbitration", "case-company", "仲裁", "", 5), ("case-company-schedule", "case-company", "公司案件开庭排期", "", 6), ("case-company-execution", "case-company", "执行案件", "", 7), ("case-company-unclaimed", "case-company", "未申请提成的到账案件", "", 8), ("case-company-stage", "case-company", "案件阶段统计", "", 9), ("case-company-no-refund", "case-company", "不再办理退费案件", "", 10),
    ("case-files-receipt", "case-files", "案件票据文件", "", 1), ("case-files-invoice", "case-files", "案件发票文件", "", 2),
    ("case-archive-pending", "case-archive", "待审核列表", "", 1), ("case-archive-done", "case-archive", "已归档列表", "", 2), ("case-archive-refused", "case-archive", "已拒绝列表", "", 3), ("case-archive-loss-internal", "case-archive", "亏损内审列表", "", 4), ("case-archive-loss-audit", "case-archive", "亏损审核列表", "", 5), ("case-archive-loss-done", "case-archive", "亏损归档列表", "", 6), ("case-archive-loss-refused", "case-archive", "亏损拒绝列表", "", 7),
]


DEFAULT_SYSTEM_MENUS += [
    ("investigation-task-published", "investigation", "我发布的调查任务", "", 1), ("investigation-task-mine", "investigation-task-published", "我的调查任务", "", 2), ("investigation-task-overdue", "investigation-task-published", "过期调查任务", "", 3), ("investigation-task-unassigned", "investigation-task-published", "待我分配的调查任务", "", 4), ("investigation-task-sub-published", "investigation-task-published", "我发布的调查子任务", "", 5), ("investigation-task-sub-mine", "investigation-task-published", "我的调查任务", "", 6),
    ("clue-my-draft", "clue", "待提交线索", "", 1), ("clue-my-pending", "clue", "待审核线索", "", 2), ("clue-my-customer", "clue", "待客户审核", "", 3), ("clue-my-collect", "clue", "待取证线索", "", 4), ("clue-my-collected", "clue", "已取证线索", "", 5), ("clue-my-refused", "clue", "已拒绝线索", "", 6), ("clue-my-no-fee", "clue", "未申请费用线索", "", 7), ("clue-my-fee", "clue", "已申请费用线索", "", 8),
    ("clue-audit", "investigation", "调查线索审核", "", 72), ("clue-audit-pending", "clue-audit", "待审批线索", "", 1), ("clue-audit-customer", "clue-audit", "待客户审核", "", 2), ("clue-audit-refused", "clue-audit", "已拒绝线索", "", 3), ("clue-audit-collect", "clue-audit", "待取证线索", "", 4), ("clue-audit-collected", "clue-audit", "已取证线索", "", 5),
    ("clue-company", "investigation", "公司调查线索", "", 73), ("clue-company-draft", "clue-company", "待提交线索", "", 1), ("clue-company-pending", "clue-company", "待审核线索", "", 2), ("clue-company-collect", "clue-company", "待取证线索", "", 3), ("clue-company-collected", "clue-company", "已取证线索", "", 4), ("clue-company-refused", "clue-company", "已拒绝线索", "", 5), ("clue-company-no-fee", "clue-company", "未申请费用线索", "", 6), ("clue-company-fee", "clue-company", "已申请费用线索", "", 7),
    ("notary-import-storage", "notary", "公证书号仓库信息导入", "", 1), ("notary-import-files", "notary", "公证书文件导入", "", 2), ("notary-import-invoices", "notary", "发票文件导入", "", 3), ("notary-query-files", "notary", "公证文件查询", "", 4),
    ("finance-receipts", "finance", "回款管理", "", 1), ("finance-receipts-icbc", "finance-receipts", "回款(工行)", "", 1), ("finance-receipts-citic", "finance-receipts", "回款(中信)", "", 2), ("finance-receipts-boc", "finance-receipts", "回款(中行)", "", 3), ("finance-receipts-new", "finance-receipts", "新增回款", "", 4), ("finance-receipts-manage", "finance-receipts", "回款管理", "", 5), ("finance-receipts-claim", "finance-receipts", "回款领取", "", 6), ("finance-receipts-pending", "finance-receipts", "待分配回款", "", 7), ("finance-receipts-allocated", "finance-receipts", "已分配回款", "", 8), ("finance-receipts-query", "finance-receipts", "到账查询", "", 9),
    ("finance-payment", "finance", "付款管理", "", 2), ("finance-payment-mine", "finance-payment", "我的请款单", "", 1), ("finance-payment-audit", "finance-payment", "请款单审批", "", 2), ("finance-payment-waiting", "finance-payment", "待付款列表", "", 3), ("finance-payment-print", "finance-payment", "付款单打印", "", 4), ("finance-payment-package-manage", "finance-payment", "付款打包-管理", "", 5), ("finance-payment-writeoff", "finance-payment", "待核销列表", "", 6), ("finance-payment-query", "finance-payment", "付款单查询", "", 7),
    ("finance-internal", "finance", "内部费用", "", 3), ("finance-internal-mine", "finance-internal", "我的请款单", "", 1), ("finance-internal-settle", "finance-internal", "内部提成-待结算", "", 2), ("finance-internal-archive", "finance-internal", "内部提成-待归档", "", 3), ("finance-internal-audit", "finance-internal", "内部提成-待审核", "", 4), ("finance-internal-fee-audit", "finance-internal", "内部费用-待审核", "", 5), ("finance-internal-refused", "finance-internal", "内部提成-已拒绝", "", 6), ("finance-internal-void", "finance-internal", "内部提成-已作废", "", 7), ("finance-internal-refund-audit", "finance-internal", "内部提成(退费)-待审核", "", 8), ("finance-internal-payment", "finance-internal", "待付款列表", "", 9), ("finance-internal-writeoff", "finance-internal", "待核销列表", "", 10), ("finance-internal-query", "finance-internal", "付款单查询", "", 11), ("finance-internal-done", "finance-internal", "已核销列表", "", 12), ("finance-internal-detail", "finance-internal", "内部费用明细", "", 13), ("finance-internal-company", "finance-internal", "内部费用明细(公司)", "", 14),
    ("finance-jar", "finance", "JAR交案费管理", "", 8),
    ("finance-invoice", "finance", "开票管理", "", 4), ("finance-invoice-mine", "finance-invoice", "我的开票", "", 1), ("finance-invoice-pending", "finance-invoice", "待处理开票", "", 2), ("finance-invoice-company", "finance-invoice", "公司开票", "", 3), ("finance-invoice-unissued", "finance-invoice", "未开票", "", 4), ("finance-invoice-company-unissued", "finance-invoice", "公司未开票", "", 5),
    ("finance-settlement", "finance", "结算管理", "", 5), ("finance-settlement-pending", "finance-settlement", "待结算", "", 1), ("finance-settlement-audit", "finance-settlement", "待审核", "", 2), ("finance-settlement-payment", "finance-settlement", "待付款", "", 3), ("finance-settlement-paid", "finance-settlement", "已付款", "", 4), ("finance-settlement-refused", "finance-settlement", "已拒绝", "", 5),
    ("finance-archive-fee", "finance", "归档费结算", "", 6), ("finance-archive-fee-pending", "finance-archive-fee", "待归档", "", 1), ("finance-archive-fee-payment", "finance-archive-fee", "待支付", "", 2), ("finance-archive-fee-paid", "finance-archive-fee", "已支付", "", 3), ("finance-archive-fee-refused", "finance-archive-fee", "已拒绝", "", 4),
    ("finance-fee-query", "finance", "费用查询", "", 7),
    ("platform-finance-overview", "platform-finance", "回款管理", "", 1), ("platform-finance-overview-icbc", "platform-finance-overview", "回款(工行)", "", 1), ("platform-finance-overview-citic", "platform-finance-overview", "回款(中信)", "", 2), ("platform-finance-overview-boc", "platform-finance-overview", "回款(中行)", "", 3), ("platform-finance-overview-cmb", "platform-finance-overview", "回款(招商)", "", 10), ("platform-finance-overview-gdicbc", "platform-finance-overview", "回款(固定工行)", "", 11), ("platform-finance-overview-new", "platform-finance-overview", "新增回款", "", 4), ("platform-finance-overview-manage", "platform-finance-overview", "回款管理", "", 5), ("platform-finance-overview-claim", "platform-finance-overview", "回款领取", "", 6), ("platform-finance-overview-pending", "platform-finance-overview", "待分配回款", "", 7), ("platform-finance-overview-allocated", "platform-finance-overview", "已分配回款", "", 8), ("platform-finance-overview-query", "platform-finance-overview", "到账查询", "", 9),
    ("platform-finance-invoice", "platform-finance", "开票管理", "", 3), ("platform-finance-invoice-mine", "platform-finance-invoice", "我的开票", "", 1), ("platform-finance-invoice-pending", "platform-finance-invoice", "待处理开票", "", 2), ("platform-finance-invoice-company", "platform-finance-invoice", "公司开票", "", 3),
        ("reports-brand", "reports", "品牌资金运营情况统计", "", 1), ("reports-lawyer", "reports", "律师资金运营情况统计", "", 2), ("reports-refund", "reports", "退费进度案件统计", "", 3), ("reports-execution-1", "reports", "执行进度案件统计1", "", 4), ("reports-execution-2", "reports", "执行进度案件统计2", "", 5), ("reports-execution-3", "reports", "执行进度案件统计3", "", 6), ("reports-customer-roi", "reports", "客户ROI统计", "", 7), ("reports-large-screen", "reports", "报表大屏", "", 8), ("reports-staff-roi", "reports", "员工业绩ROI统计", "", 9),
]


DEFAULT_SYSTEM_MENUS += [
    ("platform-finance-payment", "platform-finance", "付款管理", "", 2), ("platform-finance-payment-mine", "platform-finance-payment", "我的请款单", "", 1), ("platform-finance-payment-audit", "platform-finance-payment", "请款单审批", "", 2), ("platform-finance-payment-waiting", "platform-finance-payment", "待付款列表", "", 3), ("platform-finance-payment-print", "platform-finance-payment", "付款单打印", "", 4), ("platform-finance-payment-writeoff", "platform-finance-payment", "待核销列表", "", 5), ("platform-finance-payment-query", "platform-finance-payment", "付款单查询", "", 6),
    ("platform-finance-settlement", "platform-finance", "结算管理", "", 4), ("platform-finance-settlement-pending", "platform-finance-settlement", "待结算", "", 1), ("platform-finance-settlement-audit", "platform-finance-settlement", "待审核", "", 2), ("platform-finance-settlement-payment", "platform-finance-settlement", "待付款", "", 3), ("platform-finance-settlement-paid", "platform-finance-settlement", "已付款", "", 4), ("platform-finance-settlement-refused", "platform-finance-settlement", "已拒绝", "", 5),
    ("platform-finance-archive-fee", "platform-finance", "归档费结算", "", 5), ("platform-finance-archive-fee-pending", "platform-finance-archive-fee", "待归档", "", 1), ("platform-finance-archive-fee-payment", "platform-finance-archive-fee", "待支付", "", 2), ("platform-finance-archive-fee-paid", "platform-finance-archive-fee", "已支付", "", 3), ("platform-finance-archive-fee-refused", "platform-finance-archive-fee", "已拒绝", "", 4),
    ("platform-finance-fee-query", "platform-finance", "费用查询", "", 6),
]


DEFAULT_SYSTEM_MENUS += [
    ("system-parameters-case-type", "system-parameters", "案件类型", "", 1),
    ("system-parameters-fee-type", "system-parameters", "费用类型", "", 2),
    ("system-parameters-case-phase", "system-parameters", "案件阶段", "", 3),
    ("system-parameters-court", "system-parameters", "法院设置", "", 4),
    ("system-parameters-notary", "system-parameters", "公证处设置", "", 5),
    ("system-parameters-cause", "system-parameters", "案由设置", "", 6),
    ("system-parameters-payment", "system-parameters", "付款类型", "", 7),
    ("system-parameters-company", "system-parameters", "公司设置", "", 8),
    ("system-parameters-customer-type", "system-parameters", "客户类型", "", 9),
    ("system-parameters-case-file-type", "system-parameters", "案件文件类型", "", 10),
    ("system-parameters-ipr-case-file-type", "system-parameters", "知识产权案件文件类型", "", 11),
    ("system-parameters-district", "system-parameters", "地区设置", "", 12),
    ("system-parameters-court-officer", "system-parameters", "法院工作人员", "", 13),
    ("system-law-firms", "system", "律所档案", "", 13),
    ("system-management-cache", "system-management", "缓存管理", "", 1),
    ("system-management-menu", "system-management", "菜单管理", "", 2),
    ("system-management-config", "system-management", "系统配置", "", 3),
]


SYSTEM_MENU_ROUTE_KEYS = {key for key, *_ in DEFAULT_SYSTEM_MENUS}


MENU_KEYS = [key for key, *_ in DEFAULT_SYSTEM_MENUS if key != "dashboard"]


MENU_PARENT_BY_KEY = {key: parent_key for key, parent_key, *_ in DEFAULT_SYSTEM_MENUS}


DEFAULT_MENU_LABEL_BY_KEY = {key: label for key, _, label, _, _ in DEFAULT_SYSTEM_MENUS}


MENU_CHILDREN_BY_KEY: dict[str, list[str]] = {}


for _menu_key, _menu_parent_key in MENU_PARENT_BY_KEY.items():
    if _menu_parent_key:
        MENU_CHILDREN_BY_KEY.setdefault(_menu_parent_key, []).append(_menu_key)


LEGACY_FINANCE_MENU_KEYS = {
    "finance-fees", "finance-audit", "finance-refund", "finance-transactions", "finance-reconcile",
    "platform-finance-reconcile",
}


LEGACY_ADMIN_MENU_KEYS = {
    "hr-active", "hr-probation", "hr-offboard",
    "system-roles", "system-audit", "system-security",
}


ORIGINAL_FINANCE_MENU_KEYS = {
    key for key, _, _, _, _ in DEFAULT_SYSTEM_MENUS
    if key == "finance" or key.startswith("finance-") or key == "platform-finance" or key.startswith("platform-finance-")
}


ORIGINAL_ADMIN_MENU_KEYS = {
    key for key, _, _, _, _ in DEFAULT_SYSTEM_MENUS
    if key == "hr" or key.startswith("hr-") or key == "system" or key.startswith("system-") or key == "warehouse" or key.startswith("warehouse-")
}


ORIGINAL_INVESTIGATION_MENU_KEYS = {
    key for key, _, _, _, _ in DEFAULT_SYSTEM_MENUS
    if key == "investigation" or key in {"clue", "notary", "evidence"} or key.startswith(("investigation-", "clue-", "notary-"))
}


LEGACY_INVESTIGATION_MENU_KEYS = {"notary-import-info"}


LEGACY_TASK_MENU_KEYS = {"task-reminders"}


FIELD_KEYS = ["customer.billing", "customer.bank", "customer.legal", "contract.amount", "finance.amount", "hr.identity"]


DEFAULT_ROLE_PERMISSIONS = {
    "admin": {"display_name": "系统管理员", "data_scope": "全所数据", "menu_keys": MENU_KEYS, "field_keys": FIELD_KEYS},
    "manager": {"display_name": "部门负责人", "data_scope": "本部门数据", "menu_keys": ["agent-center", "task", "seal", "customer", "customer-conflict", "contract", "case", *CASE_CREATE_PERMISSION_KEYS, "investigation", "documents", "finance", "user-center", "hr", "warehouse", "reports"], "field_keys": FIELD_KEYS},
    "auditor": {"display_name": "审批人员", "data_scope": "授权审批数据", "menu_keys": ["agent-center", "task", "seal", "contract", "case", "investigation", "finance", "platform-finance", "user-center", "reports"], "field_keys": ["contract.amount", "finance.amount"]},
    "user": {"display_name": "普通用户", "data_scope": "本人及共享数据", "menu_keys": ["agent-center", "seal-my", "task", "customer", "customer-conflict", "contract", "case", *CASE_CREATE_PERMISSION_KEYS, "investigation", "documents", "finance", "user-center"], "field_keys": ["customer.legal", "contract.amount"]},
}


SYSTEM_USER_ROLE_CODES = frozenset(DEFAULT_ROLE_PERMISSIONS)


ROLE_DATA_SCOPES = frozenset({
    "全所数据", "本部门数据", "授权审批数据", "本人及共享数据",
})


SYSTEM_PARAMETER_CATEGORIES = {
    "case_type": "案件类型",
    "fee_type": "费用类型",
    "case_phase": "案件阶段",
    "court": "法院设置",
    "notary_office": "公证处设置",
    "cause": "案由设置",
    "payment_type": "付款类型",
    "customer_type": "客户类型",
    "case_file_type": "案件文件类型",
    "district": "地区设置",
    "court_officer": "法院工作人员",
    "ipr_case_file_type": "知识产权案件文件类型",
    "ipr_case_type": "知识产权案件类型",
    "ipr_fee_type": "知识产权费用类型",
}


DEFAULT_SYSTEM_PARAMETERS = [
    ("case_type", "110", "民事争议", {"letter_code": "MS"}),
    ("case_type", "120", "刑事案件", {"letter_code": "XS"}),
    ("case_type", "130", "行政案件及国家赔偿", {"letter_code": "XZ"}),
    ("ipr_case_file_type", "IPR-OTHER", "普通知识产权案件文档", {"case_kinds": ["专利", "商标"], "is_official": False, "requires_transmission": False, "allow_repeat": True, "hedging_file_type_codes": [], "hedging_fee_type_codes": []}),
    ("ipr_case_file_type", "IPR-TRANSFER", "知识产权待转文", {"case_kinds": ["专利", "商标"], "is_official": False, "requires_transmission": True, "allow_repeat": True, "hedging_file_type_codes": [], "hedging_fee_type_codes": []}),
    ("ipr_case_type", "IPR-PATENT", "专利案件", {"case_kind": "专利"}),
    ("ipr_case_type", "IPR-TRADEMARK", "商标案件", {"case_kind": "商标"}),
    ("ipr_fee_type", "IPR-OFFICIAL", "官方费用", {"group": "知识产权费用"}),
    ("ipr_fee_type", "IPR-SERVICE", "代理服务费", {"group": "知识产权费用"}),
    ("case_type", "140", "法律顾问", {"letter_code": "GW"}),
    ("case_type", "150", "仲裁", {"letter_code": "ZC"}),
    ("fee_type", "OFFICIAL", "官方费用", {"parent_code": ""}),
    ("fee_type", "AGENCY", "代理费", {"parent_code": ""}),
    ("fee_type", "OTHER", "其他费用", {"parent_code": ""}),
    ("fee_type", "INTERNAL", "内部费用", {"parent_code": ""}),
    ("fee_type", "SETTLEMENT", "结算费用", {"group": "结算费用"}),
    ("fee_type", "ARCHIVE", "归档费用", {"group": "归档费用"}),
    ("fee_type", "1101010", "一审诉讼费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101020", "二审诉讼费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101030", "再审诉讼费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101040", "公证费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101050", "调解金额", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101060", "判决金额", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101070", "保全费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101080", "执行费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101090", "官费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101100", "诉讼费", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1101110", "核定成本", {"parent_code": "OFFICIAL"}),
    ("fee_type", "1102010", "律师代理费", {"parent_code": "AGENCY"}),
    ("fee_type", "1102020", "律师咨询费", {"parent_code": "AGENCY"}),
    ("fee_type", "1102030", "律师培训费", {"parent_code": "AGENCY"}),
    ("fee_type", "1102040", "律师见证费", {"parent_code": "AGENCY"}),
    ("fee_type", "1102050", "平台代理费", {"parent_code": "AGENCY"}),
    ("fee_type", "1103010", "检索费", {"parent_code": "OTHER"}),
    ("fee_type", "1103020", "公告费", {"parent_code": "OTHER"}),
    ("fee_type", "1103030", "担保费", {"parent_code": "OTHER"}),
    ("fee_type", "1103040", "鉴定费", {"parent_code": "OTHER"}),
    ("fee_type", "1103050", "公证服务费", {"parent_code": "OTHER"}),
    ("fee_type", "1103060", "案源介绍费", {"parent_code": "OTHER"}),
    ("fee_type", "1103070", "权利人赔偿款", {"parent_code": "OTHER"}),
    ("fee_type", "1103080", "投资人分成", {"parent_code": "OTHER"}),
    ("fee_type", "1104010", "产品购买费", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104020", "翻译费", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104030", "调档费", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104040", "投资提成", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104050", "手续费", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104060", "任务调期扣款", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104070", "服务费(调查)", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104080", "服务费(开庭)", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104090", "服务费(案源)", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104100", "服务费(文书)", {"parent_code": "INTERNAL"}),
    ("fee_type", "1104110", "服务费(品管)", {"parent_code": "INTERNAL"}),
    ("case_phase", "WAIT_NOTARY", "等待公证书", {"case_type": "民事争议", "parent_code": "", "sort_order": 10}),
    ("case_phase", "WAIT_NOTARY_REVIEW", "审核公证书", {"case_type": "民事争议", "parent_code": "", "sort_order": 20}),
    ("case_phase", "SUBJECT_DISCLOSURE", "待主体披露", {"case_type": "民事争议", "parent_code": "", "sort_order": 30}),
    ("case_phase", "NEW", "新案待分配", {"case_type": "民事争议", "parent_code": "", "sort_order": 40}),
    ("case_phase", "DOCUMENT", "文书准备", {"case_type": "民事争议", "parent_code": "", "sort_order": 50}),
    ("case_phase", "CUSTOMER_SEAL", "客户盖章", {"case_type": "民事争议", "parent_code": "", "sort_order": 60}),
    ("case_phase", "WAIT_FILING", "等待立案", {"case_type": "民事争议", "parent_code": "", "sort_order": 70}),
    ("case_phase", "EVIDENCE_SUPPLEMENT", "补充取证", {"case_type": "民事争议", "parent_code": "", "sort_order": 80}),
    ("case_phase", "SUBMIT_FILING", "提交立案", {"case_type": "民事争议", "parent_code": "", "sort_order": 90}),
    ("case_phase", "FIRST", "一审阶段", {"case_type": "民事争议", "parent_code": "", "sort_order": 100}),
    ("case_phase", "SECOND", "二审阶段", {"case_type": "民事争议", "parent_code": "", "sort_order": 110}),
    ("case_phase", "RETRIAL", "再审阶段", {"case_type": "民事争议", "parent_code": "", "sort_order": 120}),
    ("case_phase", "EXECUTION", "执行阶段", {"case_type": "民事争议", "parent_code": "", "sort_order": 130}),
    ("case_phase", "ARCHIVE", "归档阶段", {"case_type": "民事争议", "parent_code": "", "sort_order": 140}),
    ("case_phase", "FIRST_ACCEPTED", "一审立案受理", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 201}),
    ("case_phase", "FIRST_EVIDENCE", "一审补充证据", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 202}),
    ("case_phase", "FIRST_HEARING_PREP", "一审准备开庭", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 203}),
    ("case_phase", "FIRST_REHEARING", "一审再次开庭", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 204}),
    ("case_phase", "FIRST_POST_HEARING", "一审庭后待判", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 205}),
    ("case_phase", "FIRST_WAIT_APPEAL", "一审等待上诉", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 206}),
    ("case_phase", "FIRST_APPEAL_PREP", "一审上诉准备", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 207}),
    ("case_phase", "FIRST_AGENT_OPINION", "一审补充代理意见", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 208}),
    ("case_phase", "FIRST_MEDIATION", "一审和解中", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 209}),
    ("case_phase", "FIRST_MEDIATION_CLOSED", "一审和解结案", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 210}),
    ("case_phase", "FIRST_JUDGMENT_CLOSED", "一审判决结案", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 211}),
    ("case_phase", "FIRST_CUSTOMER_PAYMENT", "一审待客户回款", {"case_type": "民事争议", "parent_code": "FIRST", "sort_order": 212}),
    ("case_phase", "SECOND_ACCEPTED", "二审立案受理", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 301}),
    ("case_phase", "SECOND_EVIDENCE", "二审补充证据", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 302}),
    ("case_phase", "SECOND_HEARING_PREP", "二审通知开庭", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 303}),
    ("case_phase", "SECOND_REHEARING", "二审再次开庭", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 304}),
    ("case_phase", "SECOND_POST_HEARING", "二审庭后待判", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 305}),
    ("case_phase", "SECOND_AGENT_OPINION", "二审补充代理意见", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 306}),
    ("case_phase", "SECOND_MEDIATION", "二审和解中", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 307}),
    ("case_phase", "SECOND_MEDIATION_CLOSED", "二审和解结案", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 308}),
    ("case_phase", "SECOND_JUDGMENT_CLOSED", "二审判决结案", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 309}),
    ("case_phase", "SECOND_CUSTOMER_PAYMENT", "二审待客户回款", {"case_type": "民事争议", "parent_code": "SECOND", "sort_order": 310}),
    ("case_phase", "RETRIAL_ACCEPTED", "再审立案受理", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 401}),
    ("case_phase", "RETRIAL_EVIDENCE", "再审补充证据", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 402}),
    ("case_phase", "RETRIAL_HEARING_PREP", "再审通知开庭", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 403}),
    ("case_phase", "RETRIAL_POST_HEARING", "再审庭后待判", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 404}),
    ("case_phase", "RETRIAL_PENDING_EXECUTION", "再审待执行", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 405}),
    ("case_phase", "RETRIAL_MEDIATION", "再审和解中", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 406}),
    ("case_phase", "RETRIAL_MEDIATION_CLOSED", "再审和解结案", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 407}),
    ("case_phase", "RETRIAL_JUDGMENT_CLOSED", "再审判决结案", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 408}),
    ("case_phase", "RETRIAL_CUSTOMER_PAYMENT", "再审待客户回款", {"case_type": "民事争议", "parent_code": "RETRIAL", "sort_order": 409}),
    ("case_phase", "FIRST_PENDING_EXECUTION", "一审待执行", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 501}),
    ("case_phase", "SECOND_PENDING_EXECUTION", "二审待执行", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 502}),
    ("case_phase", "EXECUTION_PREP_MATERIALS", "准备材料", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 503}),
    ("case_phase", "EXECUTION_SUBMIT_COURT", "提交法院", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 504}),
    ("case_phase", "EXECUTION_ACCEPTED", "执行受理", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 505}),
    ("case_phase", "EXECUTION_SUSPENDED", "执行中止", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 506}),
    ("case_phase", "EXECUTION_CLOSED_CASE", "执行结案", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 507}),
    ("case_phase", "EXECUTION_TERMINATED_CURRENT", "执行终本", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 508}),
    ("case_phase", "EXECUTION_TERMINATED", "执行终结", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 509}),
    ("case_phase", "EXECUTION_DEFICIT", "执行亏损", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 510}),
    ("case_phase", "EXECUTION_OBJECTION", "执行异议", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 511}),
    ("case_phase", "EXECUTION_MEDIATING", "执行和解中", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 512}),
    ("case_phase", "ARCHIVE_REVIEW", "归档审核", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 601}),
    ("case_phase", "ARCHIVE_COMPLETED", "已归档", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 602}),
    ("case_phase", "ARCHIVE_REJECTED", "归档拒绝", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 603}),
    ("case_phase", "ARCHIVE_DEFICIT_INTERNAL", "亏损内审", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 604}),
    ("case_phase", "ARCHIVE_DEFICIT_REVIEW", "亏损审核", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 605}),
    ("case_phase", "ARCHIVE_DEFICIT", "亏损归档", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 606}),
    ("case_phase", "ARCHIVE_DEFICIT_REJECTED", "亏损拒绝", {"case_type": "民事争议", "parent_code": "ARCHIVE", "sort_order": 607}),
    ("court", "SHBS", "上海市宝山区人民法院", {}),
    ("court", "SHXH", "上海市徐汇区人民法院", {}),
    ("court", "SHIP", "上海知识产权法院", {}),
    ("notary_office", "SHDF", "上海市东方公证处", {"number_template": "（{year}）沪东证经字第{serial}号"}),
    ("notary_office", "SHXH", "上海市徐汇公证处", {"number_template": "（{year}）沪徐证经字第{serial}号"}),
    ("cause", "IP-TRADEMARK", "侵害商标权纠纷", {"parent_code": "知识产权纠纷"}),
    ("cause", "IP-COPYRIGHT", "侵害著作权纠纷", {"parent_code": "知识产权纠纷"}),
    ("cause", "IP-PATENT", "侵害专利权纠纷", {"parent_code": "知识产权纠纷"}),
    ("payment_type", "COURT", "法院费用", {"nature": "对公", "payee": "人民法院", "account": ""}),
    ("payment_type", "NOTARY", "公证费用", {"nature": "对公", "payee": "公证处", "account": ""}),
    ("customer_type", "CUSTOMER", "客户", {}),
    ("customer_type", "PARTY", "当事人", {}),
    ("case_file_type", "CASE", "案件文件", {"parent_code": ""}),
    ("case_file_type", "CLIENT", "客户文档", {"parent_code": ""}),
    ("case_file_type", "CONTRACT", "合同文档", {"parent_code": ""}),
    ("case_file_type", "MANDATE", "委托材料", {"parent_code": ""}),
    ("case_file_type", "EVIDENCE", "证据材料", {"parent_code": ""}),
    ("case_file_type", "LITIGATION", "诉讼文书", {"parent_code": ""}),
    ("case_file_type", "JUDGMENT", "裁判文书", {"parent_code": ""}),
    ("case_file_type", "INVESTIGATION", "调查文档", {"parent_code": ""}),
    ("case_file_type", "IDENTIFICATION", "鉴别资料", {"parent_code": "INVESTIGATION"}),
    ("case_file_type", "NOTARY", "取证文档", {"parent_code": "INVESTIGATION"}),
    ("case_file_type", "SUBJECT", "主体及委托资料", {"parent_code": "CASE"}),
    ("case_file_type", "COMPLAINT", "起诉材料及证据", {"parent_code": "CASE"}),
    ("case_file_type", "DEFENSE", "答辩材料及证据", {"parent_code": "CASE"}),
    ("case_file_type", "COURT", "法院诉讼文书", {"parent_code": "CASE"}),
    ("case_file_type", "HEARING", "庭审及庭后文件", {"parent_code": "CASE"}),
    ("district", "CN", "中国", {"parent_code": ""}),
    ("district", "CN-SH", "上海市", {"parent_code": "CN"}),
    ("court_officer", "SHBS-JUDGE-01", "示例法官", {"court_code": "SHBS", "role": "法官", "phone": ""}),
]


DEFAULT_SYSTEM_CONFIGS = {
    "customer_share_policy": {
        "label": "客户共享时间设置", "group": "业务配置", "description": "客户在不同等级或状态下进入共享范围的天数。",
        "value": {"all_days": 100, "filed_days": 360, "premium_days": 30, "standard_days": 40, "basic_days": 60, "shared_days": 1000},
    },
    "company_profile": {
        "label": "公司设置", "group": "机构配置", "description": "系统抬头、开票和联系信息。",
        "value": {"name": "上海申浩律师事务所", "code": "31280", "short_code": "SH", "address": "上海市徐汇区华山路1954号浩然高科技大厦", "phone": "021-64484005", "fax": "", "email": "", "postal_code": "", "bank_name": "", "bank_account": "", "bank_address": ""},
    },
    "application_settings": {
        "label": "系统配置", "group": "运行配置", "description": "网页端显示与业务运行参数。",
        "value": {"system_name": "申浩律师协作平台", "default_department": "上海分所", "page_size": 20, "attachment_limit_mb": 20, "maintenance_mode": False},
    },
    "investigation_assignment": {
        "label": "调查任务分配人", "group": "业务配置", "description": "合同新建调查任务时固定流转到该调查主管，由其再分配调查子任务。",
        "value": {"supervisor_username": ""},
    },
}


SYSTEM_PARAMETER_CACHE: dict[str, list[dict]] = {}


SYSTEM_CACHE_REGISTRY = {
    "IPR_CASETYPE_PREFIX_casetype": {"name": "非诉讼案件类型", "description": "system_parameters:case_type", "category": "case_type"},
    "IPR_CASEFEETYPE_PREFIX_casefeetype": {"name": "非诉讼案案件费用", "description": "system_parameters:fee_type", "category": "fee_type"},
    "IPR_CASEPHASETYPE_PREFIX_casephasetype": {"name": "非诉讼案案件阶段", "description": "system_parameters:case_phase", "category": "case_phase"},
    "IPR_CASEPHASETYPE_PREFIX_casefiletype": {"name": "非诉讼案案件文档", "description": "system_parameters:case_file_type", "category": "case_file_type"},
    # These legacy cache names are retained in the management list.  The last
    # four are database queries in this service, so they must never pretend to
    # be Redis/in-memory cache entries or report a successful no-op clear.
    "IPR_CASEFEETYPE_PREFIX_caseassistedfeeType": {"name": "非诉讼案案件资助费用", "description": "直接查询 IPR 资助费用数据，当前未启用缓存"},
    "DEPARTMENT_PREFIX_department": {"name": "部门", "description": "直接查询启用部门，当前未启用缓存"},
    "USER_PREFIX_userlist": {"name": "用户", "description": "直接查询启用用户，当前未启用缓存"},
    "SYS_APPSETTING_PREFIX_configtype": {"name": "系统自动配置", "description": "直接查询系统配置，当前未启用缓存"},
    "system-parameters": {"name": "系统参数字典缓存", "description": "system_parameters:all", "category": "__all__"},
}


SYSTEM_CACHE_META = {key: {"last_cleared_at": None, "last_cleared_by": ""} for key in SYSTEM_CACHE_REGISTRY}


DEFAULT_DEPARTMENTS = [
    ("SHONE", "诉讼一部"), ("SHTWO", "诉讼二部"), ("SH-THREE", "诉讼三部"), ("SHFOUR", "诉讼四部"),
    ("IP", "知识产权中心"), ("DCQZ", "调查取证部"), ("CW", "财务部"), ("SH", "审核部"),
    ("DA", "档案部"), ("LC", "行政流程部"), ("HZ", "合作律师部"), ("HH", "合伙人律师部"),
    ("SHNJ", "申浩南京办公室"), ("GENERAL", "综合管理部"), ("SH-OFFICE", "上海分所"),
    ("BJ-OFFICE", "北京分所"), ("HZ-OFFICE", "杭州分所"), ("SZ-OFFICE", "深圳分所"),
]


SYSTEM_ADMIN_JOB_PERMISSIONS = [
    "客户查看", "客户新建", "客户修改", "客户分配", "客户回收/恢复", "客户共享", "利益冲突检索", "合同查看", "合同新建", "合同修改", "合同提交审批", "合同审批", "合同归档",
    "案件查看", "案件新建", "案件分配", "案件承办", "案件进展维护", "案件法院信息修改", "开庭排期", "案件办结", "案件归档申请", "案件归档审核", "调查任务发起", "调查任务办理", "线索审核", "公证管理", "证据管理",
    "任务查看", "任务派发", "任务接受", "任务协作", "任务交接", "任务完成确认", "收文登记", "发文登记", "文书模板维护", "业务附件上传/下载", "智能文档生成", "智能文档人工确认",
    "费用查看", "费用申请", "费用审批", "回款登记", "回款分配", "付款登记", "付款审批", "开票申请", "开票审批", "退款办理", "内部结算", "对账", "用印申请", "用印审批", "印章管理",
    "员工查看", "员工新建", "员工修改", "部门管理", "岗位角色管理", "仓库查看", "仓库出入库", "报表查看", "报表导出", "系统权限配置", "系统参数配置", "审计日志查看",
]


DEFAULT_JOB_ROLES = [
    ("SYSTEM-ADMIN", "系统管理员", SYSTEM_ADMIN_JOB_PERMISSIONS),
    ("BUSINESS-SPECIALIST", "业务专员", ["客户新建", "客户编辑", "联系人管理"]),
    ("CUSTOMER-SUPERVISOR", "客户主管", ["客户审批", "客户分级调整", "客户服务端开通"]),
    ("CUSTOMER-CONTACT", "客户联系人", ["客户服务端登录"]),
    ("CONTRACT-ADMIN", "合同管理员", ["合同创建", "合同变更", "外部合同号管理"]),
    ("INVESTIGATION-SUPERVISOR", "调查主管", ["调查任务发布", "线索审批", "取证安排"]),
    ("INVESTIGATOR-ROLE", "调查员", ["线索提交", "取证执行", "扫描上传"]),
    ("NOTARY", "公证员", ["公证书号码登记", "公证审核"]),
    ("CASE-SUPERVISOR", "案件主管", ["案件审批", "任务分配", "阶段流转"]),
    ("HANDLING-LAWYER", "承办律师", ["案件办理", "费用申请", "文档上传"]),
    ("FINANCE-SPECIALIST", "财务专员", ["付款录入", "回款录入", "开票录入", "退费录入"]),
    ("FINANCE-SUPERVISOR", "财务主管", ["财务审批", "财务对账", "归档结算"]),
    ("ARCHIVIST", "档案管理员", ["原件接收", "档案移交", "归档登记"]),
    ("GENERAL-USER", "普通用户", ["控制台查看", "待办处理"]),
    ("PARTNER", "合伙人律师", ["案件承办", "合同审批", "部门管理"]),
    ("LEAD-LAWYER", "主办律师", ["案件承办", "开庭办理", "任务派发"]),
    ("ASSISTANT", "律师助理", ["文书准备", "材料归档", "任务办理"]),
    ("INVESTIGATOR", "调查专员", ["调查取证", "证据整理"]),
    ("FINANCE", "财务人员", ["费用审核", "收付款", "对账"]),
    ("ADMINISTRATION", "行政人员", ["用印管理", "收发文", "仓库管理"]),
]


UPLOAD_ROOT = (
    Path(settings.upload_root).expanduser().resolve()
    if settings.upload_root.strip()
    else Path(__file__).resolve().parents[2] / "uploads"
)


UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


LEGACY_UPLOAD_ROOTS = (
    Path("/var/lib/docker/volumes/sunhold-legal-platform_uploads_data/_data"),
)


INVESTIGATION_RECORD_MODULES = {"investigation", "clue", "notary", "evidence"}


INVESTIGATION_CREATE_STATUS_BY_MODULE = {
    "investigation": "待分配",
    "clue": "草稿",
    "notary": "待审核",
    "evidence": "待整理",
}


INVESTIGATION_EDIT_DATA_FIELDS = {
    "region", "address", "right_type", "deadline", "priority", "platform",
    "product", "source", "infringement_method", "sales_channel", "store_url", "shop_name", "shop_id", "has_product", "producer",
    "indictee", "investigation_assistant", "investigated_at", "customer_manager",
    "start_date", "end_date", "authorized_from", "authorized_to", "authorization_scope",
    "province", "city", "district",
}


CASE_EXECUTION_STATUSES = (
    "一审待执行", "二审待执行", "准备材料", "提交法院", "执行受理",
    "执行中止", "执行结案", "执行终本", "执行终结", "执行亏损",
    "执行异议", "执行和解中", "未开始", "执行中", "已执行",
)


CASE_EXECUTION_STATUS_ALIASES = {
    "执行立案": "提交法院",
    "终结执行": "执行终结",
}


CASE_PENDING_EXECUTION_PHASES = frozenset({
    "一审待执行", "二审待执行", "再审待执行",
})


CASE_PHASE_STATUS_BY_CODE = {
    "WAIT_NOTARY_REVIEW": "等待审核公证书",
    "NEW": "新案待分配",
    "DOCUMENT": "文书准备",
    "FIRST": "一审",
    "SECOND": "二审",
    "RETRIAL": "再审",
    "EXECUTION": "执行",
    "ARCHIVE": "归档",
}


IPR_CASE_KINDS = {"专利", "商标"}


IPR_CASE_DRAFT_STATUSES = {"草稿", "已驳回"}


IPR_CASE_CATEGORIES = {"litigation", "non_litigation"}


WORKFLOW_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "customer": {"跟进中": ["正常", "公海"], "正常": ["待共享", "公海"], "待共享": ["正常"], "公海": ["跟进中", "已回收"]},
    "contract": {"草稿": ["审批中"], "审批中": [CONTRACT_APPROVED_STATUS, "已拒绝"], CONTRACT_APPROVED_STATUS: ["已完成"]},
    "case": {"等待公证书": ["等待审核公证书"], "等待审核公证书": ["新案待分配"], "新案待分配": ["文书准备"], "文书准备": ["一审立案受理"], "一审立案受理": ["一审准备开庭"], "一审准备开庭": ["待上诉", "二审", "执行", "已归档"], "待上诉": ["二审", "执行", "已归档"], "二审": ["执行", "已归档"], "执行": ["已归档"]},
    "task": {"待处理": ["处理中", "已撤回"], "处理中": ["已完成", "已逾期", "已撤回"], "已逾期": ["处理中", "已完成"]},
    "clue": {"草稿": ["待审批"], "待审批": ["待取证", "已驳回"], "待取证": ["已取证"], "已取证": ["待公证", "已转案件"], "待公证": ["已转案件", "已驳回"]},
    "notary": {"待审核": ["审核通过", "审核驳回"], "审核驳回": ["待审核"]},
    "evidence": {"待整理": ["已整理"], "已整理": ["已入卷"]},
    "seal": {"草稿": ["待审批", "已撤回"], "待审批": ["待用印", "已拒绝", "已撤回"], "待用印": ["已用印", "已撤回"], "已用印": ["已归档"]},
    "finance": {"草稿": ["待审批"], "待审批": ["已审批", "已退回"], "已审批": ["已付款"], "已付款": ["已对账"]},
    "document": {"待登记": ["待签收"], "待签收": ["已签收"], "已签收": ["已归档"]},
    "hr": {"试用": ["在职", "离职"], "在职": ["离职", "停用"], "离职": ["在职"], "停用": ["在职"]},
    "warehouse": {"在库": ["借出", "报废"], "借出": ["归还中"], "归还中": ["在库"]},
    "report": {"生成中": ["已生成"], "已生成": ["已发布"]},
    "system": {"启用": ["停用"], "停用": ["启用"]},
}


GENERIC_RECORD_EDITABLE_MODULES = {"customer", "report", "system"}


GENERIC_RECORD_TRANSITION_MODULES = {"report", "system"}


GENERIC_RECORD_DELETABLE_MODULES = {"report"}


FIELD_PERMISSION_DATA_KEYS = {
    "customer.billing": {"invoice_title", "taxpayer_id", "invoice_address", "invoice_phone"},
    "customer.bank": {"bank_name", "bank_account"},
    "customer.legal": {"credit_code", "legal_representative", "registered_address"},
    "contract.amount": {"amount"},
    "finance.amount": {"amount", "paid_amount", "invoice_amount", "refund_amount", "official_fee_amount", "agency_fee_amount", "other_fee_amount"},
    "hr.identity": {"id_no"},
}


CONTRACT_PERSON_NAME_PLACEHOLDER = "姓名待维护"


CONTRACT_PERSON_NAME_PATTERN = re.compile(r"[\u3400-\u9fff]")


CONTRACT_NON_PERSON_NAME_MARKERS = PERSON_NAME_NON_PERSON_MARKERS


RECORD_PERSON_FIELDS_BY_MODULE: dict[str, tuple[str, ...]] = {
    "case": (
        "source_person", "customer_manager", "hearing_lawyer", "assistant", "assistant_username",
        "handler", "case_manager", "case_officer", "initiator", "submitted_by", "created_by", "updated_by",
        "investigator_username", "archive_submitter", "archive_internal_reviewer", "archive_reviewer",
    ),
    "seal": (
        "applicant", "requester", "submitted_by", "approver", "stamped_by", "archived_by", "created_by", "updated_by",
    ),
    "finance": (
        "applicant", "requester", "submitted_by", "approver", "payer", "claimant", "operator", "created_by", "updated_by",
    ),
    "hr": (
        "username", "created_by", "updated_by", "resigned_by", "login_status_updated_by", "contract_approval_updated_by",
    ),
    "warehouse": (
        "borrower", "borrowed_by", "return_requested_by", "returned_by", "checked_in_by", "checked_out_by",
        "recipient", "rechecked_in_by", "destroyed_by", "scrapped_by", "created_by", "updated_by",
    ),
    "document": (
        "handler", "register_operator", "signer", "archived_by", "submitted_by", "created_by", "updated_by",
    ),
}


RECORD_PERSON_LIST_FIELDS_BY_MODULE: dict[str, tuple[str, ...]] = {
    "case": ("handling_usernames", "handling_lawyers", "handling_lawyer_usernames", "assistant_usernames", "assistants", "case_team_usernames", "collaborators"),
    "seal": ("approvers",),
    "finance": ("approvers",),
    "document": ("recipients",),
}


_OFFICIAL_RECEIVABLE_FEE_WORDS = (
    "官方", "官费", "差旅费", "诉讼费", "公证费", "调解金额", "判决金额",
    "保全费", "公告费", "担保费", "鉴定费", "执行费", "公证服务费",
)


_INVALID_RECEIVABLE_FEE_STATUSES = {"已驳回", "已拒绝", "已作废"}


_CASE_HEARING_LEVELS = (
    ("retrial", "再审开庭"),
    ("execution", "执行开庭"),
    ("second", "二审开庭"),
    ("first", "一审开庭"),
)


AI_SPACE_CATEGORY = "AI空间"


AI_SPACE_EDITABLE_SUFFIXES = {".docx", ".md", ".txt"}


WORD_DOCUMENT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


ARCHIVE_REQUIRED_CATEGORIES = {"委托材料", "证据材料", "诉讼文书", "裁判文书"}


JOB_ACTION_MENU_GRANTS: dict[str, tuple[str, ...]] = {
    # Historical personnel roles stored approval capabilities as business-action
    # labels. Keep those records effective without widening them to an entire
    # business center.
    "合同审批": ("contract-audit",),
    "用印审批": ("seal-audit",),
}


JOB_ROLE_LABEL_MENU_GRANTS: dict[str, tuple[str, ...]] = {
    "客户查看": ("customer",), "客户新建": ("customer-new",), "客户修改": ("customer-mine",),
    "客户分配": ("customer",), "客户回收/恢复": ("customer-recycle",), "客户共享": ("customer-shared",),
    "利益冲突检索": ("customer-conflict",),
    "合同查看": ("contract",), "合同新建": ("contract-new",), "合同修改": ("contract-mine",),
    "合同提交审批": ("contract-mine",), "合同审批": ("contract-audit",), "合同归档": ("contract-archive",),
    "案件查看": ("case",), "案件新建": ("case-new",), "案件分配": ("case-company",),
    "案件承办": ("case-mine",), "案件进展维护": ("case-mine",), "开庭排期": ("case-mine-schedule",),
    "案件办结": ("case-mine",), "案件归档申请": ("case-archive",), "案件归档审核": ("case-archive",),
    "调查任务发起": ("investigation-task-published",), "调查任务办理": ("investigation-task-mine",),
    "线索提交": ("clue-my-draft",), "线索审核": ("clue-audit",), "取证安排": ("evidence",),
    "取证执行": ("evidence",), "公证管理": ("notary",), "证据管理": ("evidence",),
    "任务查看": ("task",), "任务派发": ("task",), "任务接受": ("task",), "任务协作": ("task",),
    "任务交接": ("task",), "任务完成确认": ("task",),
    "收文登记": ("documents-register",), "发文登记": ("documents-register",),
    "文书模板维护": ("documents-template",), "业务附件上传/下载": ("documents",),
    "智能文档生成": ("documents",), "智能文档人工确认": ("documents",),
    "费用查看": ("finance",), "费用申请": ("finance",), "费用审批": ("finance",),
    "回款登记": ("finance-receipts",), "回款分配": ("finance-receipts",), "付款登记": ("finance-payment",),
    "付款审批": ("finance-payment",), "开票申请": ("finance-invoice",), "开票审批": ("finance-invoice",),
    "退款办理": ("finance",), "内部结算": ("finance-internal",), "对账": ("finance",),
    "用印申请": ("seal-my",), "用印审批": ("seal-audit",), "印章管理": ("seal-admin",),
    "员工查看": ("hr-all",), "员工新建": ("hr-new",), "员工修改": ("hr-all",),
    "部门管理": ("hr-departments",), "岗位角色管理": ("hr-roles",), "仓库查看": ("warehouse-list",),
    "仓库出入库": ("warehouse",), "报表查看": ("reports",), "报表导出": ("reports",),
    "系统权限配置": ("system",), "系统参数配置": ("system-parameters",), "审计日志查看": ("system",),
}


JOB_ROLE_LABEL_MENU_GRANTS.update({
    "控制台查看": ("dashboard",), "待办处理": ("dashboard",),
    "客户编辑": ("customer-mine",), "联系人管理": ("customer-mine",),
    "客户审批": ("customer",), "客户分级调整": ("customer-mine",), "客户服务端开通": ("customer-mine",),
    "客户服务端登录": ("customer-mine",),
    "合同创建": ("contract-new",), "合同变更": ("contract-mine",), "外部合同号管理": ("contract-mine",),
    "任务分配": ("task",), "任务办理": ("task",), "任务查看": ("task",), "任务派发": ("task",), "任务接受": ("task",), "任务协作": ("task",),
    "公证书号码登记": ("notary",), "公证审核": ("notary",), "公证管理": ("notary",),
    "调查取证": ("evidence",), "证据整理": ("evidence",), "扫描上传": ("evidence",), "取证执行": ("evidence",),
    "费用查看": ("finance",), "费用申请": ("finance",), "费用审核": ("finance",), "财务审批": ("finance",), "财务对账": ("finance",), "收付款": ("finance",),
    "回款录入": ("finance-receipts",), "付款录入": ("finance-payment",), "开票录入": ("finance-invoice",), "退费录入": ("finance",), "归档结算": ("finance",),
    "用印管理": ("seal",), "用印申请": ("seal-my",), "用印审批": ("seal-audit",), "印章管理": ("seal-admin",),
    "seal": ("seal",), "seal-my": ("seal-my",), "seal-audit": ("seal-audit",), "seal-admin": ("seal-admin",),
    "seal-my-pending": ("seal-my-pending",), "seal-my-stamping": ("seal-my-stamping",), "seal-my-used": ("seal-my-used",), "seal-my-refused": ("seal-my-refused",), "seal-my-withdrawn": ("seal-my-withdrawn",),
    "seal-audit-pending": ("seal-audit-pending",), "seal-audit-stamping": ("seal-audit-stamping",), "seal-audit-refused": ("seal-audit-refused",), "seal-admin-pending": ("seal-admin-pending",), "seal-admin-used": ("seal-admin-used",), "seal-admin-query": ("seal-admin-query",),
    "员工查看": ("hr-all",), "员工新建": ("hr-new",), "员工修改": ("hr-all",), "仓库管理": ("warehouse",), "仓库查看": ("warehouse-list",),
    "原件接收": ("case-archive",), "档案移交": ("case-archive",), "归档登记": ("case-archive",),
    "开庭办理": ("case-mine-schedule",), "案件办理": ("case-mine",), "案件审批": ("case-archive",), "阶段流转": ("case-mine",),
    "文书准备": ("documents",), "文档上传": ("documents",), "材料归档": ("case-files",), "收发文": ("documents",),
    "调查任务发布": ("investigation-task-published",), "线索审批": ("clue-audit",),
})


JOB_ROLE_ACTION_KEY_GRANTS: dict[str, tuple[str, ...]] = {
    "员工新建": ("hr.employee.create",),
    "员工修改": ("hr.employee.update",),
    "客户新建": ("record.customer.create",),
    "客户修改": ("record.customer.update",),
    "客户编辑": ("record.customer.update",),
    "合同审批": ("contract.application.approve",),
    "合同新建": ("contract.application.create",),
    "合同创建": ("contract.application.create",),
    "合同修改": ("contract.application.update",),
    "合同编辑": ("contract.application.update",),
    "合同提交审批": ("contract.application.submit",),
    "合同变更": ("contract.application.change",),
    "合同变更审批": ("contract.application.change.approve",),
    "合同归档": ("contract.archive.close",),
    "合同付款申请": ("contract.payment.create",),
    "合同付款审批": ("contract.payment.approve",),
    "合同付款登记": ("contract.payment.pay",),
    "合同付款核销": ("contract.payment.writeoff",),
    "案件分配": ("case.team.assign",),
    "案件承办": (
        "case.detail.update", "case.log.create", "case.reminder.manage",
        "case.task.create", "case.attachment.write", "case.progress.update", "case.phase.update",
        "case.assisted_fee.manage",
    ),
    "案件进展维护": ("case.progress.update", "case.phase.update"),
    "案件法院信息修改": ("case.court.update",),
    "案件办结": ("case.close",),
    "案件归档申请": ("case.archive.apply",),
    "案件归档审核": ("case.archive.review",),
    # 用印岗位动作必须和前端能力字段、审批接口共用同一组键。菜单仅控制
    # 导航；这里才是后端可执行操作的授权来源。
    "用印申请": ("seal.application.apply",),
    "用印审批": ("seal.application.approve", "seal.application.reject"),
    "印章管理": ("seal.application.stamp", "seal.application.archive", "seal.asset.manage"),
}


SYSTEM_ACTION_OPERATION_LABELS = {
    "query": "查询", "create": "新增", "update": "编辑", "delete": "删除",
    "clear": "清理", "reset": "重置", "permissions": "维护权限",
}


def _system_action_definitions(menu_keys: list[str] | set[str] | None = None) -> list[dict]:
    """Build the M/A catalog from local system menu capabilities.

    The legacy RoleController obtained actions dynamically from ActionService and
    MenuService.GetMenuActionList. The local service has no action table, so its
    endpoint capabilities are the maintainable source of truth.
    """
    keys = sorted(set(menu_keys or SYSTEM_MENU_ROUTE_KEYS))
    definitions: list[dict] = []
    for menu_key in keys:
        if menu_key == "system":
            operations = ("query", "permissions")
        elif menu_key == "system-management-cache":
            operations = ("query", "clear")
        elif menu_key == "system-management-menu":
            operations = ("query", "create", "update", "delete", "reset")
        elif menu_key == "system-management-config":
            operations = ("query", "update")
        elif menu_key == "system-parameters" or menu_key.startswith("system-parameters-"):
            operations = ("query", "create", "update", "delete")
        elif menu_key == "system-law-firms":
            operations = ("query", "create", "update", "delete")
        elif menu_key.startswith("system-"):
            operations = ("query",)
        else:
            continue
        definitions.extend(
            {"code": f"{menu_key}.{operation}", "menu_key": menu_key, "label": SYSTEM_ACTION_OPERATION_LABELS[operation]}
            for operation in operations
        )
    return definitions


SYSTEM_ACTION_DEFINITIONS = _system_action_definitions()


SYSTEM_ACTION_BY_CODE = {item["code"]: item for item in SYSTEM_ACTION_DEFINITIONS}


RECORD_MODULE_MENU_ROOTS: dict[str, tuple[str, ...]] = {
    "customer": ("customer",),
    "contract": ("contract",),
    "case": ("case",),
    "ipr_case": ("ipr",),
    "ipr_official_file": ("ipr",),
    "task": ("task",),
    "investigation": ("investigation",),
    "clue": ("investigation",),
    "notary": ("investigation",),
    "evidence": ("investigation",),
    "document": ("documents",),
    "seal": ("seal",),
    "hr": ("hr",),
    "warehouse": ("warehouse",),
    "report": ("reports",),
    "system": ("system",),
    # Financial records are shared by firm finance and platform finance workbenches.
    "finance": ("finance", "platform-finance"),
    "jar_fee": ("finance-jar",),
    "invoice": ("finance", "platform-finance"),
    "refund": ("finance", "platform-finance"),
    "finance_package": ("finance", "platform-finance"),
    "finance_settlement": ("finance", "platform-finance"),
    "finance_archive_settlement": ("finance", "platform-finance"),
    "contract_payment": ("finance", "platform-finance"),
}


FEE_TYPE_ROOT_BASES = {
    "OFFICIAL": "官方费用",
    "AGENCY": "代理费",
    "OTHER": "其他费用",
    "INTERNAL": "内部费用",
    "SETTLEMENT": "结算费用",
    "ARCHIVE": "归档费用",
}


FEE_TYPE_BASE_SCOPES = {
    "官方费用": ["律所", "平台"],
    "代理费": ["律所", "平台"],
    "其他费用": ["律所", "平台"],
    "内部费用": ["内部"],
    "结算费用": [],
    "归档费用": [],
}


SYSTEM_PARAMETER_RELATION_CONFIG = {
    "case-type-file-types": (CaseTypeFileTypeRelation, "case_type_id", "file_type_id", "case_type", "case_file_type"),
    "file-type-fee-types": (CaseFileTypeFeeTypeRelation, "file_type_id", "fee_type_id", "case_file_type", "fee_type"),
    "case-type-case-phases": (CaseTypeCasePhaseRelation, "case_type_id", "case_phase_id", "case_type", "case_phase"),
}


PARAMETER_REFERENCE_FIELDS: dict[str, dict[str, set[str]]] = {
    "customer_type": {"customer": {"customer_type"}},
    "case_type": {"case": {"case_type"}},
    "fee_type": {"finance": {"fee_type"}},
    "court": {"case": {"court", "first_court_name", "second_court_name", "execution_court_name", "retrial_court_name"}},
    "notary_office": {"clue": {"notary_institution"}, "notary": {"notary_institution"}},
    "cause": {"case": {"cause", "cause_of_action", "reason"}},
    "payment_type": {"finance": {"payment_type"}, "contract": {"payment_type"}},
    "district": {"customer": {"province", "city", "district"}, "case": {"province", "city", "district"}},
    "court_officer": {"case": {"judge", "clerk", "first_court_judge", "first_court_clerk", "second_court_judge", "second_court_clerk", "execution_court_judge", "execution_court_clerk", "retrial_court_judge", "retrial_court_clerk"}},
}


DASHBOARD_SUPPLEMENT_EVIDENCE_STATUSES = {
    "一审补充证据",
    "二审补充证据",
    "再审补充证据",
}


DASHBOARD_SUPPLEMENT_OPINION_STATUSES = {
    "一审补充代理意见",
    "二审补充代理意见",
}


DASHBOARD_CASE_QUEUES = {"supplement_evidence", "supplement_opinion", "urgent"}


CUSTOMER_MODIFICATION_ACTIONS = {
    "创建客户", "批量导入", "编辑", "编辑变更",
    "领取客户", "释放公海", "共享客户", "移入回收站", "恢复客户",
    "新增联系人", "删除联系人", "更新客户管理人",
    "新增客户跟进", "删除客户跟进",
    "新增沟通日志", "修改沟通日志", "删除沟通日志",
}


RECORD_IMPORT_COLUMNS = {
    "contract": ["业务编号", "合同名称", "客户/主体", "合同类型", "合同金额", "签订日期", "外部合同号", "负责人", "部门", "说明"],
    "case": ["业务编号", "案件名称", "关联合同号", "案件类型", "对方当事人", "法院", "负责人", "说明"],
    "task": ["业务编号", "任务内容", "客户/主体", "截止日期", "优先级", "来源", "关联案号", "负责人", "协作人", "部门", "说明"],
    "document": ["业务编号", "文件名称", "客户/主体", "收发类型", "文件日期", "关联案号", "来文/送达单位", "负责人", "部门", "说明"],
    "finance": ["业务编号", "费用名称", "客户/主体", "费用类型", "金额", "关联案号", "经办人", "部门", "说明"],
    "hr": ["员工编号", "姓名", "状态", "部门", "岗位", "联系电话", "入职日期", "用工类型", "证件号码", "邮箱", "说明"],
    "warehouse": ["物品编号", "物品名称", "物品类别", "数量", "单位", "存放位置", "部门", "供应商", "说明"],
    "seal": ["申请编号", "申请标题", "客户/主体", "印章编号", "份数", "用途", "计划日期", "办理方式", "文件名称", "负责人", "部门", "说明"],
}


RECORD_IMPORT_SAMPLES = {
    "contract": ["HT2026079999", "知识产权专项服务合同", "示例客户有限公司", "专项服务", "100000.00", str(date.today()), "EXT-001", "admin", "上海分所", "示例数据请删除"],
    "case": ["SHMS2699999", "示例商标侵权纠纷", "HT2026060097", "民事案件", "示例对方有限公司", "上海知识产权法院", "admin", "合同必须已经审批通过"],
    "task": ["RW2026079999", "准备案件证据目录", "示例客户有限公司", str(date.today() + timedelta(days=7)), "普通", "日常任务", "", "admin", "协作人甲、协作人乙", "上海分所", "示例数据请删除"],
    "document": ["SW2026079999", "法院开庭传票", "示例客户有限公司", "收文", str(date.today()), "SH191000382B", "上海市示例人民法院", "admin", "上海分所", "示例数据请删除"],
    "finance": ["FY2026079999", "示例诉讼费", "示例客户有限公司", "官方费用", "3500.00", "SH191000382B", "admin", "上海分所", "示例数据请删除"],
    "hr": ["YG2026079999", "示例员工", "试用", "上海分所", "律师助理", "13800000000", str(date.today()), "全职", "", "demo@example.com", "示例数据请删除"],
    "warehouse": ["WP2026079999", "示例笔记本电脑", "电子设备", "1", "台", "行政仓 A-01", "上海分所", "示例供应商", "示例数据请删除"],
    "seal": ["YY2026079999", "示例用印申请", "示例客户有限公司", "YZ-GZ-001", "2", "法院立案", str(date.today() + timedelta(days=1)), "现场用印", "民事起诉状", "admin", "上海分所", "示例数据请删除"],
}


CUSTOMER_CREATE_DATA_FIELDS = {
    "contact", "contact_accounts", "phone", "credit_code", "legal_representative", "registered_address",
    "invoice_title", "taxpayer_id", "invoice_address", "invoice_phone", "bank_name", "bank_account",
    "customer_type", "short_name", "fax", "legal_agent_id_no", "legal_agent_title", "customer_source",
    "is_shared", "is_assisted", "file_date", "level", "province", "postal_code", "patent_customer_type",
    "fee_reduction", "industry", "output_value", "cooperation_status", "gb_classification", "website",
    "organization_nature", "organization_code", "registration_region", "registration_postal_code",
    "registered_capital", "registration_year",
}


CUSTOMER_SYSTEM_DATA_FIELDS = {
    "notes", "last_contact_at", "contact_count", "last_modified_by", "last_modified_date",
    "status_before_recycle", "recycled_at", "recycled_by", "restored_at", "restored_by",
    "released_at", "released_by", "claimed_at", "claimed_by", "shared_with", "is_shared", "shared_at",
    "level_change", "key_change", "portal_access",
}


CUSTOMER_CREATE_STATUSES = {"潜在", "目标", "立项", "关怀", "签约", "谈判", "价值"}


CUSTOMER_LEVELS = {"潜在客户", "目标客户", "签约客户", "立案客户", "高级客户", "中级客户", "低级客户"}


CASE_PLAINTIFF_FIELDS = (
    "plaintiff", "plaintiffs", "plaintiff_name", "plaintiff_names",
    "appellant", "appellants", "appellant_name", "appellant_names",
)


CASE_DEFENDANT_FIELDS = (
    "defendant", "defendants", "defendant_name", "defendant_names", "opponent",
    "appellee", "appellees", "appellee_name", "appellee_names",
)


CASE_THIRD_PARTY_FIELDS = (
    "third_party", "third_parties", "third_party_name", "third_party_names",
)


CASE_PARTY_SEPARATOR = re.compile(r",(?!\s)|[，、;；\r\n]+")


CONTRACT_APPROVAL_ACTION_CODE = "contract.application.approve"


_contract_serial_lock = asyncio.Lock()


JAR_FEE_MODULE = "jar_fee"


JAR_FEE_STATUSES = {"待确认", "已确认", "已入账", "已作废"}


JAR_FEE_TRANSITIONS = {
    "待确认": {"已确认", "已作废"},
    "已确认": {"已入账", "已作废"},
    "已入账": set(),
    "已作废": set(),
}


INVESTIGATION_MATERIAL_CATEGORIES = {
    "investigation": ["调查授权书", "权利证明", "调查资料", "客户指示"],
    "clue": ["现场照片", "网页截图", "购买记录", "调查报告"],
    "notary": ["公证书扫描件", "公证费发票", "公证实物登记"],
    "evidence": ["证据原件", "证据扫描件", "证据目录"],
}


VIP_TASK_STATUSES = {"待处理", "处理中", "已完成", "已验收", "已拒绝", "已暂停", "已取消"}


VIP_TASK_PRIORITIES = {"低", "普通", "重要", "紧急"}


_LEGACY_CASE_TASK_HISTORY_ENTITIES = {
    "nodes": (LegacyCaseTaskHistoryNode, LegacyCaseTaskHistoryNode.legacy_task_guid, LegacyCaseTaskHistoryNode.id),
    "participants": (LegacyCaseTaskHistoryNodeParticipant, LegacyCaseTaskHistoryNodeParticipant.legacy_task_guid, LegacyCaseTaskHistoryNodeParticipant.id),
    "messages": (LegacyCaseTaskHistoryMessage, LegacyCaseTaskHistoryMessage.legacy_task_guid, LegacyCaseTaskHistoryMessage.legacy_message_id),
    "notifications": (LegacyCaseTaskHistoryNotification, LegacyCaseTaskHistoryNotification.legacy_task_guid, LegacyCaseTaskHistoryNotification.legacy_seq_id),
    "read-receipts": (LegacyCaseTaskHistoryReadReceipt, LegacyCaseTaskHistoryReadReceipt.legacy_task_id, LegacyCaseTaskHistoryReadReceipt.legacy_seq_id),
    "files": (LegacyCaseTaskHistoryFile, LegacyCaseTaskHistoryFile.legacy_task_guid, LegacyCaseTaskHistoryFile.legacy_file_id),
}


FINANCE_FEE_TYPES = {"官方费用", "代理费", "其他费用", "内部费用", "结算费用", "预损费用", "归档费用"}


EXPENSE_SUBTYPE_FEE_TYPE = {
    "官费": "官方费用", "一审诉讼费": "官方费用", "二审诉讼费": "官方费用", "再审诉讼费": "官方费用",
    "诉讼费": "官方费用", "保全费": "官方费用", "鉴定费": "官方费用", "公证费": "官方费用",
    "公告费": "官方费用", "调解金额": "官方费用", "判决金额": "官方费用", "执行费": "官方费用", "核定成本": "官方费用",
    "检索费": "其他费用", "公告费": "其他费用", "担保费": "其他费用", "鉴定费": "其他费用", "公证服务费": "其他费用",
    "律师代理费": "代理费", "律师咨询费": "代理费", "律师培训费": "代理费", "律师见证费": "代理费",
    "平台代理费": "代理费",
    "案源介绍费": "其他费用", "权利人赔偿款": "其他费用", "投资人分成": "其他费用",
    "第三方费用": "其他费用", "代理费": "代理费", "其他费用": "其他费用", "内部费用": "内部费用",
    "产品购买费": "内部费用", "翻译费": "内部费用", "投资提成": "内部费用", "调档费": "内部费用",
    "手续费": "内部费用", "任务调期扣款": "内部费用", "服务费(调查)": "内部费用", "服务费(开庭)": "内部费用",
    "服务费(案源)": "内部费用", "服务费(文书)": "内部费用", "服务费(品管)": "内部费用",
}


EXPENSE_SCOPE_FEE_TYPES = {"律所": {"官方费用", "代理费", "其他费用"}, "平台": {"官方费用", "代理费", "其他费用"}, "内部": {"内部费用"}}


FINANCE_TRANSACTION_TYPES = {"付款", "开票", "回款", "退费"}


FINANCE_VOUCHER_CATEGORIES = {"付款凭证", "发票扫描件", "回款凭证", "退费凭证"}


FINANCE_DEFAULT_VOUCHER_CATEGORY = {"付款": "付款凭证", "开票": "发票扫描件", "回款": "回款凭证", "退费": "退费凭证"}


INVOICE_RELEASED_STATUSES = {"已撤回", "已作废"}


REFUND_CASE_FEE_STATUSES = {
    "R10": "准备材料",
    "R20": "已提交法院",
    "R30": "法院处理中",
    "R35": "待退款到账",
    "R40": "退款已到账",
    "R50": "退费完成",
    "R100": "不再办理退费",
}


REFUND_CASE_FEE_STATUS_BY_LABEL = {label: code for code, label in REFUND_CASE_FEE_STATUSES.items()}


REFUND_LIST_STATUSES = {"草稿", "待审批", "退款办理中", "已退款", "已驳回"}


REFUND_PAGE_SIZES = {10, 15, 20, 50, 100, 200}


REFUND_GROUP_ALIASES = {"lawfirm": "lawfirm", "trad": "trad", "1": "lawfirm", "2": "trad", "律所": "lawfirm", "商标": "trad"}


CASE_COMMISSION_ROLES = (
    {
        "key": "hearing", "label": "开庭", "subtype": "服务费(开庭)",
        "rate_field": "hearing_rate", "fixed_field": "hearing_fixed",
        "rate_name": "开庭提成", "fixed_name": "开庭固定提成",
        "fields": ("hearing_lawyer_usernames", "hearing_lawyer_username", "court_lawyer_username", "hearing_lawyers", "hearing_lawyer", "court_lawyer"),
    },
    {
        "key": "document", "label": "文书", "subtype": "服务费(文书)",
        "rate_field": "document_rate", "fixed_field": "document_fixed",
        "rate_name": "文书提成", "fixed_name": "文书固定提成",
        "fields": ("assistant_usernames", "assistant_username", "assistants", "assistant", "case_assistant"),
    },
    {
        "key": "source", "label": "案源", "subtype": "服务费(案源)",
        "rate_field": "source_rate", "fixed_field": "source_fixed",
        "rate_name": "案源提成", "fixed_name": "案源固定提成",
        "fields": ("business_owner_usernames", "business_owner_username", "source_person_usernames", "source_person_username", "business_owner", "source_person"),
    },
    {
        "key": "investigation", "label": "调查", "subtype": "服务费(调查)",
        "rate_field": "investigation_rate", "fixed_field": "investigation_fixed",
        "rate_name": "调查提成", "fixed_name": "调查固定提成",
        "fields": ("investigator_usernames", "investigator_username", "investigators", "investigator"),
    },
    {
        "key": "quality", "label": "品管", "subtype": "服务费(品管)",
        "rate_field": "quality_rate", "fixed_field": "quality_fixed",
        "rate_name": "品牌管理费", "fixed_name": "品牌固定管理费",
        "fields": ("coordinator_usernames", "coordinator_username", "quality_manager_username", "coordinators", "coordinator", "quality_manager"),
    },
)


FINANCE_PAYMENT_CANCELABLE_STATUSES = {"草稿", "待审批", "已审批", "待付款"}


FINANCE_PAYMENT_ROLLBACKABLE_STATUSES = {"待审批", "已审批", "待付款"}


CASE_EVENT_PENDING_STATUS = "待处理"


CASE_EVENT_COMPLETED_STATUS = "已完成"


CASE_EVENT_OVERDUE_STATUS = "已逾期"


CASE_EVENT_TIME_ZONE = ZoneInfo("Asia/Shanghai")


_BUILTIN_DOCUMENT_TEMPLATES: dict[str, dict] = {
    "authorization": {
        "name": "授权委托书",
        "category": "诉讼文书",
        "content": """授 权 委 托 书

{{plaintiff_name}}（以下简称"委托人"）因与 {{defendant_name}} {{case_type}} 纠纷一案，特委托 {{law_firm_name}}（以下简称"受托人"）的律师作为代理人。

一、委托事项
{{entrust_matter}}

二、委托权限
{{entrust_authority}}

三、委托期限
自本委托书签署之日起至 {{entrust_deadline}} 止。

四、其他约定
{{other_terms}}

委托人（盖章）：________________
法定代表人（签字）：________________
日期：{{sign_date}}

受托人（盖章）：{{law_firm_name}}
经办律师：{{handling_lawyer}}
日期：{{sign_date}}""",
    },
    "law-firm-letter": {
        "name": "律师事务所函",
        "category": "诉讼文书",
        "content": """律师事务所函

{{recipient_unit}}：

本律所接受 {{plaintiff_name}} 的委托，指派本所 {{handling_lawyer}} 律师担任贵单位审理的 {{plaintiff_name}} 与 {{defendant_name}} {{case_type}} 纠纷一案中 {{plaintiff_name}} 的诉讼代理人。

该律师在本案中的代理权限为：{{entrust_authority}}

请贵单位依法予以接洽并提供相应的诉讼便利。

特此函告。

{{law_firm_name}}（盖章）
年　　月　　日

附：授权委托书一份""",
    },
    "identity": {
        "name": "身份证明",
        "category": "诉讼文书",
        "content": """身 份 证 明

兹证明：

单位名称：{{subject_name}}
统一社会信用代码/注册号：{{credit_code}}
住所地：{{subject_address}}
法定代表人/负责人：{{legal_representative}}
职务：{{representative_title}}

上述人员系我单位法定代表人（负责人），以我单位名义办理相关事项，其行为我单位均予承认。

特此证明。

{{subject_name}}（盖章）
年　　月　　日

附：法定代表人/负责人身份证复印件""",
    },
    "settlement": {
        "name": "结算提成表",
        "category": "内部表单",
        "content": """案 件 结 算 提 成 表

一、案件基本信息
案　　号：{{case_no}}
案件类型：{{case_type}}
客户名称：{{customer_name}}
对方当事人：{{opposite_name}}
经办律师：{{handling_lawyer}}
开庭律师：{{hearing_lawyer}}
案　源　人：{{source_lawyer}}

二、费用明细
合同金额：￥{{contract_amount}} 元
已收费用：￥{{received_amount}} 元
未收费用：￥{{outstanding_amount}} 元
退费金额：￥{{refund_amount}} 元
诉讼标的：￥{{litigation_amount}} 元

三、提成计算
提成比例：{{commission_rate}}
提成金额：￥{{commission_amount}} 元

四、复核意见
{{review_comment}}

经办律师签字：________________
部门负责人签字：________________
财务审核：________________
日期：______年____月____日""",
    },
}


AGENT_CASE_UPDATE_FIELDS = {"title", "customer", "status", "description"}


AGENT_CASE_DATA_FIELDS = {
    "court", "first_instance_court", "first_instance_case_no", "second_instance_court",
    "second_instance_case_no", "cause_or_charge", "case_stage", "filing_date",
    "acceptance_date", "judgment_date", "effective_date", "archive_no",
    "paper_archive_location", "client_position",
}


AGENT_ACTION_CAPABILITY = {
    "case.update": "can_edit_basic",
    "case.data.update": "can_edit_basic",
    "case.task.create": "can_create_case_task",
    "case.reminder.create": "can_create_reminder",
    "customer.update": "can_update_customer",
    "contract.update": "can_update_contract",
}


CASE_CUSTOM_DOCUMENT_FOLDERS_KEY = "custom_case_document_folders"


CASE_DOCUMENT_FOLDER_HEADERS = {"AI空间", "客户文档", "合同文档", "调查文档", "案件文档", "调查文档全部", "案件文档全部"}


CASE_FORMAL_DOCUMENT_FOLDER_ORDER = (
    "主体及委托资料",
    "起诉材料及证据",
    "答辩材料及证据",
    "法院诉讼文书",
    "庭审及庭后文件",
)


CASE_FORMAL_DOCUMENT_FOLDERS = set(CASE_FORMAL_DOCUMENT_FOLDER_ORDER)


CASE_INVESTIGATION_DOCUMENT_FOLDERS = ("鉴别资料", "调查文档", "取证文档")


WORD_EDITOR_LOCK_SECONDS = 15 * 60


ATTACHMENT_TEXT_PREVIEW_MAX_CHARS = 200_000


XLSX_PREVIEW_MAX_SHEETS = 20


XLSX_PREVIEW_MAX_ROWS_PER_SHEET = 2_000


XLSX_PREVIEW_MAX_COLUMNS = 100


PDF_PREVIEW_MAX_FILE_BYTES = 40 * 1024 * 1024


PDF_PREVIEW_MAX_PAGES = 500


PDF_PREVIEW_MIN_WIDTH = 96


PDF_PREVIEW_MAX_WIDTH = 2048


PDF_PREVIEW_MAX_DIMENSION = 2048


PDF_PREVIEW_MAX_PIXELS = 4_000_000


SEAL_ACTION_CODES = {
    "apply": "seal.application.apply",
    "approve": "seal.application.approve",
    "reject": "seal.application.reject",
    "stamp": "seal.application.stamp",
    "archive": "seal.application.archive",
    "manage_assets": "seal.asset.manage",
}


HR_SUBRECORD_KINDS = {"leave", "matter", "commission"}


IPR_REMINDER_EVENT_TYPES: tuple[tuple[int, str], ...] = (
    (0, "自定义未分类"), (1, "申请费"), (2, "提实质审查缴纳实质审查费"), (3, "缴纳登记、印刷费、印花税、首年年费"),
    (4, "缴纳年费"), (5, "缴纳滞纳金及年费"), (6, "缴纳优先权费"), (7, "补充优先权证明文本"),
    (8, "专利补正"), (9, "提出复审缴纳复审费"), (10, "缴纳著入项目变更费"),
    (11, "专利补充证据材料"), (12, "商标提出复审"), (13, "商标补正"), (14, "商标补充证据材料"),
    (15, "商标续展"), (16, "商标初审公布"), (17, "著作权补正"), (18, "缴纳无效申请费"),
    (19, "答复审查意见"), (20, "待转文案件"), (21, "待转票案件"), (22, "费用减缓请求"),
    (23, "商标异议答辩"), (24, "办理专利资助"),
)


IPR_REMINDER_EVENT_TYPE_BY_ID = dict(IPR_REMINDER_EVENT_TYPES)


LEGACY_IPR_REMINDER_TYPE_SEEDS: tuple[tuple[int, str, bool, bool, str, str, str], ...] = (
    (0, "自定义未分类", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (1, "申请费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (2, "提实质审查缴纳实质审查费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (3, "缴纳登记、印刷费、印花税、首年年费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (4, "缴纳年费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (5, "缴纳滞纳金及年费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (6, "缴纳优先权费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (7, "补充优先权证明文本", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (8, "专利补正", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (9, "提出复审缴纳复审费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (10, "缴纳著入项目变更费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (11, "专利补充证据材料", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (12, "商标提出复审", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (13, "商标补正", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (14, "商标补充证据材料", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (15, "商标续展", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (16, "商标初审公布", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (17, "著作权补正", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (18, "缴纳无效申请费", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (19, "答复审查意见", True, True, "system", "admin", "2017-03-27T16:27:56.617"),
    (20, "待转文案件", True, True, "system", "admin", "2017-02-27T16:27:56.617"),
    (21, "待转票案件", True, True, "system", "admin", "2017-02-27T16:27:56.617"),
    (22, "费用减缓请求", True, False, "system", "admin", "2017-03-27T16:27:56.617"),
)


IPR_WARNING_TIME_NODES = {"case_deadline", "reminder_deadline"}


IPR_CASE_DOCUMENT_TYPES = {
    "case-summary": "知识产权案件信息表",
    "authorization-letter": "知识产权代理授权委托书",
    "law-firm-letter": "律师事务所函",
    "identity-certificate": "主体身份证明核对单",
}


CASE_DOCUMENT_TYPES = {
    "identification_letter": "鉴定函",
    "authorization-letter": "授权委托书",
    "archive-cover": "归档封面",
    "archive-letter": "归档函",
    "gd-authorization-letter": "广东版授权委托书",
    "compensation-letter": "赔偿函",
    "law-firm-letter": "律师事务所函",
    "identity-certificate": "法定代表人身份证明",
    "settlement-list": "结算提成表",
    "compensation-payment-application": "代收代付赔偿款申请单",
    "first-instance-appellant-lawyer-letter": "一审（我方原告）律所函",
    "first-instance-appellee-lawyer-letter": "一审（我方被告）律所函",
    "second-instance-appellant-lawyer-letter": "二审（我方上诉）律所函",
    "second-instance-appellee-lawyer-letter": "二审（对方上诉）律所函",
    "execution-lawyer-letter": "执行律所函",
    "gd-first-instance-appellant-lawyer-letter": "广东版一审上诉人律师函",
    "gd-first-instance-appellee-lawyer-letter": "广东版一审被上诉人律师函",
    "gd-second-instance-appellant-lawyer-letter": "广东版二审上诉人律师函",
    "gd-second-instance-appellee-lawyer-letter": "广东版二审被上诉人律师函",
    "gd-execution-lawyer-letter": "广东版执行律师函",
}


CASE_LEGACY_LAW_FIRM_LETTER_TYPES = {
    "first-instance-appellant-lawyer-letter",
    "first-instance-appellee-lawyer-letter",
    "second-instance-appellant-lawyer-letter",
    "second-instance-appellee-lawyer-letter",
    "execution-lawyer-letter",
}


CASE_DOCUMENT_CATEGORY = {
    "identification_letter": "法院诉讼文书",
    "authorization-letter": "主体及委托资料",
    "identity-certificate": "主体及委托资料",
    "archive-cover": "庭审及庭后文件",
    "settlement-list": "庭审及庭后文件",
    "compensation-payment-application": "庭审及庭后文件",
    **{key: "法院诉讼文书" for key in CASE_LEGACY_LAW_FIRM_LETTER_TYPES},
}


LEGACY_CONTRACT_STATUS_BY_NEW = {
    "草稿": 0,
    "审批中": 10,
    CONTRACT_APPROVED_STATUS: 20,
    "已拒绝": 30,
    "已回收": 40,
    "已归档": 60,
    "已完成": 80,
}


LEGACY_INVESTIGATION_STATUS = {"待分配": 0, "进行中": 10, "已完成": 20, "已取消": 30}


LEGACY_INVESTIGATION_TASK_STATUS = {
    "待接收": 0, "未开始": 0, "处理中": 10, "待确认": 15,
    "已完成": 20, "已验收": 20, "已拒绝": 30, "已撤回": 40,
    "已停止": 40, "已取消": 40,
}


LEGACY_INVESTIGATION_CLUE_STATUS = {
    "草稿": 0, "待审批": 10, "待客户审核": 15, "待取证": 20,
    "已取证": 30, "待公证": 35, "已转案件": 40, "已驳回": 50,
}


LEGACY_OFFICIAL_DOCUMENT_STATUS = {
    "草稿": 0,
    "待审批": 10,
    "待用印": 20,
    "已拒绝": 30,
    "已撤回": 40,
    "已用印": 60,
    "已归档": 60,
}

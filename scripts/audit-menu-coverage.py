"""Verify every configured menu leaf resolves to an implemented web page.

This is a structural guard for the original-system clone.  It deliberately
parses the authoritative backend menu declarations instead of maintaining a
second hand-written menu list.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "apps/api-server/app/main.py").read_text(encoding="utf-8")
APP = (ROOT / "apps/admin-web/src/App.tsx").read_text(encoding="utf-8")
STYLES = (ROOT / "apps/admin-web/src/styles.css").read_text(encoding="utf-8")
FINANCE = (ROOT / "apps/admin-web/src/FinanceCenterPage.tsx").read_text(encoding="utf-8")
FINANCE_CSS = (ROOT / "apps/admin-web/src/finance-center.css").read_text(encoding="utf-8")
NORMALIZED_FINANCE = re.sub(r"\s+", "", FINANCE)
CASE = (ROOT / "apps/admin-web/src/CaseCenterPage.tsx").read_text(encoding="utf-8")
CASE_CSS = (ROOT / "apps/admin-web/src/case-center.css").read_text(encoding="utf-8")
CUSTOMER = (ROOT / "apps/admin-web/src/CustomerCenterPage.tsx").read_text(encoding="utf-8")
CUSTOMER_CSS = (ROOT / "apps/admin-web/src/customer-center.css").read_text(encoding="utf-8")
CUSTOMER_CONFLICT = (ROOT / "apps/admin-web/src/CustomerConflictPage.tsx").read_text(encoding="utf-8")
CUSTOMER_CONFLICT_CSS = (ROOT / "apps/admin-web/src/customer-conflict.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "apps/admin-web/src/ContractCenterPage.tsx").read_text(encoding="utf-8")
INVESTIGATION = (ROOT / "apps/admin-web/src/InvestigationCenterPage.tsx").read_text(encoding="utf-8")
TASK = (ROOT / "apps/admin-web/src/TaskCenterPage.tsx").read_text(encoding="utf-8")
NORMALIZED_TASK = re.sub(r"\s+", "", TASK)
NOTIFICATION = (ROOT / "apps/admin-web/src/NotificationCenter.tsx").read_text(encoding="utf-8")
SMOKE = (ROOT / "scripts/smoke-api.py").read_text(encoding="utf-8")
NORMALIZED_SMOKE = re.sub(r"\s+", "", SMOKE)
DOCUMENT = (ROOT / "apps/admin-web/src/DocumentCenterPage.tsx").read_text(encoding="utf-8")
AGENT_DOCUMENT = (ROOT / "apps/admin-web/src/AgentDocumentPage.tsx").read_text(encoding="utf-8")
SEAL = (ROOT / "apps/admin-web/src/SealCenterPage.tsx").read_text(encoding="utf-8")
WAREHOUSE = (ROOT / "apps/admin-web/src/WarehousePage.tsx").read_text(encoding="utf-8")
SYSTEM = (ROOT / "apps/admin-web/src/SystemCenterPage.tsx").read_text(encoding="utf-8")
HR = (ROOT / "apps/admin-web/src/HrCenterPage.tsx").read_text(encoding="utf-8")
ORGANIZATION = (ROOT / "apps/admin-web/src/OrganizationCenterPage.tsx").read_text(encoding="utf-8")
REPORT = (ROOT / "apps/admin-web/src/ReportCenterPage.tsx").read_text(encoding="utf-8")
SEAL_CSS = (ROOT / "apps/admin-web/src/seal-center.css").read_text(encoding="utf-8")
WEB_NGINX = (ROOT / "apps/admin-web/nginx.conf").read_text(encoding="utf-8")


def declared_menus() -> list[tuple[str, str, str, str, int]]:
    result: list[tuple[str, str, str, str, int]] = []
    for match in re.finditer(r"DEFAULT_SYSTEM_MENUS\s*(?:\+?=)\s*\[", MAIN):
        start = match.end() - 1
        depth = 0
        for index in range(start, len(MAIN)):
            if MAIN[index] == "[":
                depth += 1
            elif MAIN[index] == "]":
                depth -= 1
                if depth == 0:
                    result.extend(ast.literal_eval(MAIN[start : index + 1]))
                    break
    return result


def canonical_route(route: str) -> str:
    if route.startswith("case-") and route.endswith("-schedule"):
        return "case-schedule"
    if route.startswith("case-") and route.endswith("-execution"):
        return "case-execution"
    if route.startswith(("investigation-task-published", "investigation-task-sub-published")):
        return "task-my-created"
    if route.startswith(("investigation-task-mine", "investigation-task-sub-mine")):
        return "task-my-accepted"
    if route == "investigation-task-overdue":
        return "task-reminders"
    if route == "investigation-task-unassigned":
        return "task-company"
    if route.startswith("reports-"):
        return "reports"
    prefixes = (
        "seal-my", "seal-audit", "seal-admin", "task-my", "task-dept",
        "task-company", "contract-audit", "contract-receivable", "case-new",
        "case-mine", "case-dept", "case-company", "case-archive", "clue",
        "notary", "evidence", "finance-fees", "finance-audit",
        "finance-receipts", "finance-invoice", "platform-finance-overview",
        "platform-finance-invoice",
    )
    return next((prefix for prefix in prefixes if route.startswith(prefix + "-")), route)


def is_implemented(route: str) -> bool:
    return (
        route == "dashboard"
        or route.startswith("seal-")
        or route == "customer-conflict"
        or route.startswith("customer-")
        or route == "contract-receivable"
        or route.startswith("contract-")
        or route in {"investigation", "clue", "notary", "evidence"}
        or route.startswith("case-")
        or route.startswith("task-")
        or route == "documents-agent"
        or route.startswith("documents-")
        or route.startswith("platform-finance-")
        or route in {"user-messages", "user-communications", "user-center", "user-account"}
        or route.startswith("finance-")
        or route == "system-audit"
        or route.startswith("system-")
        or route in {"hr-departments", "hr-roles"}
        or route.startswith("hr-")
        or route.startswith("warehouse")
        or route == "reports"
    )


def main() -> None:
    unsafe_form_date_formats: list[str] = []
    unsafe_pattern = re.compile(r"\b(?:v|value|values)\.[A-Za-z_][A-Za-z0-9_]*\.format\(")
    for path in (ROOT / "apps/admin-web/src").glob("*.tsx"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if unsafe_pattern.search(line):
                unsafe_form_date_formats.append(f"{path.name}:{line_no}")
    assert not unsafe_form_date_formats, (
        "form date values must use formatRequiredDate so hidden/unmounted fields cannot cause silent runtime errors: "
        + ", ".join(unsafe_form_date_formats)
    )

    menus = declared_menus()
    keys = [item[0] for item in menus]
    assert len(menus) == 264, f"expected 264 original-visible menu nodes, got {len(menus)}"
    assert len(keys) == len(set(keys)), "duplicate menu keys found"
    parents = {item[1] for item in menus if item[1]}
    leaves = [key for key in keys if key not in parents]
    assert len(leaves) == 219, f"expected 219 original-visible menu leaves, got {len(leaves)}"
    missing = [(key, canonical_route(key)) for key in leaves if not is_implemented(canonical_route(key))]
    assert not missing, f"menu leaves without a page component: {missing}"
    assert "页面不存在，请从左侧菜单重新选择" in APP, "missing explicit unknown-route guard"

    fallback_menu = APP[APP.index("const menuItems: NavItem[] = [") : APP.index("function configuredMenuItems")]
    fallback_top_order = [
        fallback_menu.index(f'\n    key: "{key}",')
        for key in ("dashboard", "seal", "task", "customer")
    ]
    assert fallback_top_order == sorted(fallback_top_order), (
        "fallback top-level order must match the original/backend order: "
        "dashboard -> seal -> task -> customer"
    )

    customer_new_start = CUSTOMER.index('{initialView === "customer-new" && (')
    customer_new_end = CUSTOMER.index("<Modal", customer_new_start)
    customer_new = CUSTOMER[customer_new_start:customer_new_end]
    normalized_customer_new = re.sub(r"\s+", "", customer_new)
    assert '<Card className="customer-create-page">' in customer_new, "customer-new must start with the form and must not add a card title bar"
    for section in ("基本信息", "法人信息", "开票信息", "控制信息"):
        assert f"<h3>{section}</h3>" in customer_new, f"customer-new is missing visible section {section}"
    for hidden_section in ("专利必填信息", "附加信息"):
        assert hidden_section not in customer_new, f"customer-new must not expose original zero-height section {hidden_section}"
    assert 'label="所属部门"' not in customer_new, "customer-new must not invent a department input"
    normalized_main_customer = re.sub(r"\s+", "", MAIN)
    for token in (
        'name="title"rules={[{required:true}]}',
        'name="serial_no"><Inputdisabledplaceholder="自动生成"',
        'name="status"><SelectallowClearplaceholder="请选择"',
        'name="customer_type"><Selectoptions={["客户","当事人"]',
        'placeholder="不允许有空格."',
        'tabBarExtraContent={<Buttontype="primary"onClick={save}><span>保</span><span>存</span></Button>}',
        'value:user.username,label:user.display_name||user.username',
    ):
        assert token in normalized_customer_new, f"customer-new field/control contract missing: {token}"
    related_tables = (
        ("没有查询到联系人，可以去 ", ("序号", "姓名", "职务", "项目角色", "办公电话", "移动电话", "IM", "邮箱", "是否接收邮件", "是否需要联系", "是否有效", "操作")),
        ("没有查询到事项记录，可以去 ", ("序号", "内容", "操作人", "操作日期", "操作")),
        ("没有查询到客户文件，可以去 ", ("序号", "上传人", "文件名称", "文档日期", "查看", "操作")),
    )
    for marker, headers in related_tables:
        table_start = customer_new.rindex("<Table", 0, customer_new.index(marker))
        table_end = customer_new.index("]} />", table_start)
        table_source = customer_new[table_start:table_end]
        positions = [table_source.index(f'title:"{header}"') for header in headers]
        assert positions == sorted(positions), f"customer-new related table headers are out of order: {headers}"
    for empty_text in (
        "没有查询到联系人，可以去 ",
        "没有查询到事项记录，可以去 ",
        "没有查询到客户文件，可以去 ",
    ):
        assert empty_text in customer_new, f"customer-new empty state is missing: {empty_text}"
    for token in ('title: "提示"', 'content: "请先保存客户基本资料."', 'okText: <><span>确</span><span>定</span></>'):
        assert token in CUSTOMER, f"customer-new unsaved related modal is missing: {token}"
    assert 'tabBarExtraContent={<Button type="primary" onClick={save}><span>保</span><span>存</span></Button>}' in CUSTOMER, "customer-new save must keep the original unspaced two-character label"
    assert 'serial_no: "",' in CUSTOMER, "customer-new must show the original blank auto-generated customer number"
    assert '.customer-create-form .ant-form-item-control-input { min-height: 23px; }' in CUSTOMER_CSS, "customer-new rows must override Ant Form's 32px control wrapper to match the original compact table"
    assert '.customer-create-form .ant-select { height: 23px; }' in CUSTOMER_CSS, "customer-new selects must not expand the original 25px table rows"
    assert '.customer-create-form .ant-form-item { height: 25px;' in CUSTOMER_CSS, "customer-new field rows must retain the original 25px table rhythm"
    assert ': await api.post("/customers", {' in CUSTOMER, "customer-new must use the dedicated protected create API"
    assert 'open={Boolean(contacts) && initialView !== "customer-new" && !detailPageOpen}' in CUSTOMER, "customer-new and customer-mine view states must not fall through to the editable drawer"
    assert "height: 20px" in CUSTOMER_CSS and "border-bottom: 1px solid #d9d9d9" in CUSTOMER_CSS, "customer-new must retain horizontal 20px section headers"
    assert "grid-template-columns: 92px minmax(0, 1fr)" not in CUSTOMER_CSS, "customer-new must not use a vertical section heading column"
    assert ".customer-control-grid { grid-template-columns: repeat(5" in CUSTOMER_CSS, "customer-new control section must keep five fields on its first row"
    assert '@app.post(f"{settings.api_prefix}/customers"' in MAIN, "dedicated customer create API is missing"

    # Original-evidence contract for /6001001/CRM/Customer/CustomerList.
    assert '("customer-mine", "customer", "我的客户", "", 32)' in MAIN, "customer-mine backend menu declaration is missing"
    assert '{ key: "customer-mine", label: "我的客户" }' in APP, "customer-mine fallback menu declaration is missing"
    assert '<CustomerCenterPage initialView={route} onNavigate={navigate} />' in APP, "customer routes must preserve the visible leaf key"
    normalized_customer = re.sub(r"\s+", "", CUSTOMER)
    for token in (
        '"customer-mine":"mine","customer-recycle":"recycle","customer-dept":"department"',
        'scope:originalCustomerScope,customer_name:keyword,customer_type:customerType,...(["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?{}:{manager:managerKeyword}),page,page_size:pageSize',
        'elseif(["customer-mine","customer-dept","customer-company","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)){',
        '<label>客户名称</label>',
        '<label>客户/当事人</label>',
        '<label>客户管理人</label>',
        'pagination={isOriginalCustomerList?false:{pageSize:15,showSizeChanger:true,pageSizeOptions:[15,30,50],showTotal:(count)=>`共${count}条`,}}',
        'locale={{emptyText:"没有查询到符合条件的记录。"}}',
        'columnWidth:44',
        '[10,15,20,50,100,200].map((value)=>({value,label:String(value)}))',
        '<ButtononClick={()=>goToCustomerPage(Number(jumpPage||page))}>GO</Button>',
        '<ButtononClick={()=>{consttarget=requireSingleSelected();if(target)voidopenDetail(target);}}>客户查看</Button>',
        'onClick={()=>openDetail(r)}',
        'onClick={()=>openCustomerContracts(r)}',
        'onClick={()=>openCustomerCivilCases(r)}',
        'sessionStorage.setItem("sunhold:contract-customer"',
        'onNavigate?.("contract-new")',
        'api.get("/attachments",{params:{record_id:target.id}})',
        'setContacts(null);setDetailPageOpen(false);setSelectedRowKeys([]);setPage(1);setJumpPage("1");',
        'responseTotal>0&&responseItems.length===0&&page>responseLastPage',
        'setPage(responseLastPage);setJumpPage(String(responseLastPage));setSelectedRowKeys([]);return;',
        '(r.data.customer_managers||[r.owner]).map(userLabel).join(["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-recent-update"].includes(initialView)?",":"、")',
        '<tdclassName="ant-table-cellcustomer-amount-cell">{amount(listSummary.agency_fee_due)}</td>',
    ):
        assert token in normalized_customer, f"customer-mine original contract missing: {token}"
    assert 'width: 235' in CUSTOMER[CUSTOMER.index('title: "客户编号"'):CUSTOMER.index('title: "客户名称"')], "customer number column must be wide enough to display the generated identifier"
    assert 'tableLayout="fixed"' in CUSTOMER and '<button' in CUSTOMER[CUSTOMER.index('title: "客户编号"'):CUSTOMER.index('title: "客户名称"')], "customer table must use fixed columns and a cell-contained number action"
    assert all(token in CUSTOMER_CSS for token in ('.customer-original-table .ant-table-cell', 'overflow: hidden !important;', '.customer-cell-link > span', 'text-overflow: ellipsis;')), "customer number text must be clipped inside its own cell"
    normalized_app = re.sub(r"\s+", "", APP)
    normalized_hr = re.sub(r"\s+", "", HR)
    normalized_contract = re.sub(r"\s+", "", CONTRACT)
    assert 'constisAuditView=initialView==="contract-audit"||initialView.startsWith("contract-audit-");' in normalized_contract, "contract-audit menu route must render the approval view and expose pending contract-change review actions"
    assert 'className="workspace-tabs"' in APP and 'sunhold:open-pages' in APP and 'closeOpenPage' in APP, "workspace must retain independently closeable accumulated page tabs"
    assert "api.get('/system/users')" in HR and 'id:-Number(user.id)' in normalized_hr, "employee list must include system accounts without a separate HR record"
    assert '>继续新建员工</Button>' in HR and 'setCurrentEmployeeId(undefined)' in HR, "employee create page must reset after a successful save"
    assert 'showSearchoptionFilterProp="label"placeholder="输入客户名称关键字后选择"' in normalized_contract, "contract customer must use searchable registered-customer selection"
    assert 'sessionStorage.getItem("sunhold:contract-customer")' in CONTRACT, "contract creation must consume customer context from the customer page"
    assert 'user.can_approve_contract' in CONTRACT and 'notFoundContent="没有可用审批人，请由管理员在角色管理中授予合同审批权限"' in CONTRACT, "contract approval selector must use configured job-role permission and explain an empty directory"
    assert all(token in MAIN for token in ('"job_permissions": job_permissions', '"can_approve_contract": item.role == "admin"', '_user_has_job_permission(approver_user, "合同审批", db)', 'async def _user_permission_payload(user: User, db: AsyncSession)', 'if can_approve_contract and "contract" not in menu_keys:')), "user directory, login permissions, and contract submission must resolve contract approval from job-role permissions"
    assert 'permission = await _permission_payload(user.role, db)\n    can_approve_contract = await _user_has_job_permission(user, "合同审批", db)' in MAIN and 'permission = await _user_permission_payload(user, db)\n    return {"access_token": create_token' in MAIN, "contract approver menu access must be built from the role payload and returned by login"
    assert '>新增审批人</Button>' in CONTRACT and 'role: "auditor"' in CONTRACT and 'profile: { position: values.position, staff_role: values.position }' in CONTRACT and 'must_change_password: true' in CONTRACT, "contract workflow must let administrators create a first-login-protected contract approver"
    assert '合同审批只能选择一名具有合同审批权限的人员' in MAIN and '合同发起人不能审批自己提交的合同' in MAIN and '管理员也不能代替指定审批人操作' in MAIN, "contract API must enforce one role-authorized approver and separation of duties"
    assert 'approvers: values.approvers ? [values.approvers] : []' in CONTRACT and 'name="approvers"' in CONTRACT and 'placeholder="请选择具有合同审批权限的人员"' in CONTRACT, "contract approval UI must submit exactly one role-authorized approver"
    assert 'value:customer.id' in normalized_contract and 'customer.id===Number(v.customer_id)' in normalized_contract, "contract customer selection must persist a unique customer id instead of an ambiguous duplicate name"
    assert 'title.normalize("NFKC").trim().toLocaleLowerCase()' in CONTRACT and 'label:customer.title' in normalized_contract and '${customer.serial_no}' not in CONTRACT[CONTRACT.index('const customerOptions'):CONTRACT.index('const openChange')], "contract customer selection must display only one option per normalized customer name without showing its number"
    assert '_ensure_unique_customer_name' in MAIN and '客户名称已存在，不能创建或改为同名客户' in MAIN, "customer API must block exact duplicate names on create and rename"
    assert 'employeeEditFields' in HR and '员工完整资料修改' in HR and '保存全部修改' in HR and 'lawyer_license_no' in HR and 'school' in HR and 'editableData' in HR, "employee edit must expose and save the full employee profile"
    assert 'name="username" label="用户名"' in HR and 'username:value.username' in normalized_hr and '_rename_system_username' in MAIN, "administrator employee edit must rename the login account and migrate exact username references"
    assert 'dayjs.isDayjs(v.signed_at)' in CONTRACT and 'loading={savingContract}' in CONTRACT, "contract creation must safely default hidden fields and expose the real save-in-progress state"
    assert 'localStorage.removeItem(WIZARD_STORAGE_KEY)' in CONTRACT and '>开始新建合同</Button>' in CONTRACT and '>继续新建合同</Button>' in CONTRACT and '是否同步办理合同用印？' in CONTRACT, "completed contract wizard must clear recovery state, expose create-another from every sealing state, and ask for synchronous sealing"
    assert 'sunhold:route-reselect' in CONTRACT and 'sunhold:route-reselect' in APP, "reselecting the active contract-new menu must reset the wizard instead of keeping the completed contract"
    assert '_resolve_contract_customer' in MAIN and '不能手工录入未登记客户名称' in MAIN, "contract API must reject unregistered customer names"
    for seal_type in ("合同章", "公章", "所函专用章", "法人章", "发票章", "财务专用章", "财务三排章"):
        assert seal_type in MAIN and seal_type in SEAL, f"required contract seal type is not available end to end: {seal_type}"
    assert 'notFoundContent="暂无可用印章，请管理员到用印中心维护"' in CONTRACT, "contract seal selector must explain missing inventory instead of silently showing no data"
    assert 'required_seal_types <=' in SMOKE, "API smoke test must prove all required contract seal types are available"
    assert 'permissionGroups' in ORGANIZATION and 'job-permission-matrix' in ORGANIZATION and '合同提交审批' in ORGANIZATION and '智能文档人工确认' in ORGANIZATION, "job roles must expose granular business-action permissions"
    for header in (
        "客户编号", "客户名称", "案源人", "客户管理人", "建档日期", "最后联系日期",
        "最后修改日期", "联系次数", "合同数量", "民事案件数", "代理费", "官费", "客户状态",
    ):
        assert header in CUSTOMER, f"customer-mine current table is missing header {header}"
    for action_label in ("客户删除", "客户编辑", "新增合同"):
        assert action_label in CUSTOMER, f"customer-mine operation is missing: {action_label}"
    for token in (
        'constrecycleCustomer=(row:Customer)=>{',
        'content:"删除后客户将进入回收站，可在回收站恢复或进入公海。"',
        'awaitapi.post(`/customers/${row.id}/recycle`,{comment:"我的客户：客户删除",});',
        'message.success("客户已移入回收站")',
        'if(key==="delete")recycleCustomer(target)',
    ):
        assert token in normalized_customer, f"customer-mine delete-to-recycle contract missing: {token}"
    assert 'api.delete(`/records/${row.id}`)' not in CUSTOMER, "customer production UI must not hard-delete customer records"
    customer_list_start = CUSTOMER.index('<Card className="panel customer-list-panel"')
    customer_list_end = CUSTOMER.index('</Card>', customer_list_start)
    customer_list_source = CUSTOMER[customer_list_start:customer_list_end]
    for forbidden_action in ("共享客户", "导入CSV", "导出CSV"):
        assert forbidden_action not in customer_list_source, f"customer-mine must not invent original action {forbidden_action}"
    for token in (
        '@app.get(f"{settings.api_prefix}/customers")',
        'scope:str=Query("mine",pattern="^(mine|recycle|department|department_recycle|company|company_recycle|public|shared|recent_contact|recent_update)$")',
        'page_size:int=Query(15,ge=1,le=200)',
        'BusinessRecord.status.not_in(["已回收","公海"])',
        'ifscopein{"mine","recycle"}andcurrent_user.role!="admin":',
        'orbool(exact_managers(item)&manager_tokens)',
        '"summary":{"agency_fee_due"',
        '"customer_type":"客户","invoice_address":"test"',
    ):
        assert re.sub(r"\s+", "", token) in normalized_main_customer, f"customer-mine dedicated API contract missing: {token}"
    for smoke_token in (
        'mine_page=call("GET","/customers?scope=mine&page=1&page_size=1")',
        'exact_mine=call("GET",f"/customers?scope=mine&customer_name=',
        'manager_mine=call("GET",f"/customers?scope=mine&customer_name=',
        'deleted_from_mine=call("POST",f"/customers/{company_recycle_record[\'id\']}/recycle"',
        'deleted_personal_recycle=call("GET",f"/customers?scope=recycle&customer_name=',
    ):
        assert re.sub(r"\s+", "", smoke_token) in NORMALIZED_SMOKE, f"customer-mine smoke evidence missing: {smoke_token}"
    assert ".customer-original-table .customer-original-selected > td { background: #ffff00 !important; }" in CUSTOMER_CSS
    assert ".customer-grid-footer" in CUSTOMER_CSS and ".customer-original-pagination" in CUSTOMER_CSS
    customer_view_start = CUSTOMER.index('className="customer-view-page"')
    customer_view_end = CUSTOMER.index('{initialView !== "customer-new"', customer_view_start)
    customer_view_source = CUSTOMER[customer_view_start:customer_view_end]
    normalized_customer_view = re.sub(r"\s+", "", customer_view_source)
    for token in (
        '<h3>基本信息</h3>', '<h3>法人信息</h3>', '<h3>开票信息</h3>', '<h3>控制信息</h3>',
        'label:"联系人"', 'label:"事项记录"', 'label:"客户文档"',
        '["潜在","目标","立项","关怀","签约","谈判","价值"].includes(contacts.status)?contacts.status:"请选择"',
        'value={contacts.data.invoice_address||""}',
        'locale={{emptyText:"没有查询到联系人"}}',
        '"没有查询到事项记录"',
        '"没有查询到客户文件"',
        'aria-label="关闭客户查看"',
    ):
        assert re.sub(r"\s+", "", token) in normalized_customer_view, f"customer-mine read-only view contract missing: {token}"
    assert "setNewEditor" not in customer_view_source and "documentFileRef" not in customer_view_source, "customer view must remain read-only"
    assert '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&(<Buttondisabled={page===customerPageCount}onClick={()=>goToCustomerPage(customerPageCount)}>»</Button>)' in normalized_customer, "customer lists with directly evidenced complete paging must expose their last-page double-arrow button"
    for token in (
        '[detailPageOpen,setDetailPageOpen]=useState(false)',
        'setDetailPageOpen(isReadOnlyCustomerList)',
        'open={Boolean(contacts)&&initialView!=="customer-new"&&!detailPageOpen}',
    ):
        assert token in normalized_customer, f"customer-mine read-only navigation contract missing: {token}"
    assert ".customer-view-fields-four { grid-template-columns: repeat(4" in CUSTOMER_CSS
    assert ".customer-view-fields-five { grid-template-columns: repeat(5" in CUSTOMER_CSS

    # Original-evidence contract for /6001002/CRM/Customer/CustomerList.
    for token in (
        '("customer-recycle", "customer", "个人回收站", "", 33)',
        '"customer-recycle": "recycle"',
        '? [{ key: "restore", label: "客户恢复" }, { key: "release", label: "进入公海" }]',
        '!["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) || rows.length > 0',
        'summary={["customer-recycle", "customer-dept", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-shared", "customer-recent-contact", "customer-recent-update"].includes(initialView) && rows.length === 0 ? undefined',
        'isReadOnlyCustomerList && detailPageOpen && contacts',
        '["customer-recycle", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-recent-update"].includes(initialView) && v === "已回收" ? "已删除" : v',
        'join(["customer-recycle", "customer-dept-recycle", "customer-company", "customer-company-recycle", "customer-public", "customer-recent-update"].includes(initialView) ? "," : "、")',
    ):
        assert token in MAIN or token in CUSTOMER, f"customer-recycle original contract missing: {token}"
    for token in (
        'ifscopein{"recycle","department_recycle","company_recycle"}:',
        'conditions.append(BusinessRecord.status=="已回收")',
        '"已回收",*CUSTOMER_CREATE_STATUSES',
    ):
        assert token in normalized_main_customer, f"customer-recycle API/action contract missing: {token}"
    for token in (
        'recycle_page=call("GET",f"/customers?scope=recycle&customer_name=',
        'released_from_recycle=call("POST",f"/customers/{customer[\'id\']}/release"',
        'claimed_from_public=call("POST",f"/customers/{customer[\'id\']}/claim"',
    ):
        assert token in NORMALIZED_SMOKE, f"customer-recycle smoke evidence missing: {token}"

    # Original-evidence contract for 部门客户 and its real assignment flow.
    assert '("customer-dept", "customer", "部门客户", "", 34)' in MAIN
    assert '{ key: "customer-dept", label: "部门客户" }' in APP
    for token in (
        '"customer-dept":"department"',
        'setDetailPageOpen(isReadOnlyCustomerList)',
        'initialView==="customer-dept"?"部门客户"',
        'isOriginalCustomerList&&<divclassName="customer-original-pagination">',
        'summary={["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined:',
        '["customer-dept","customer-company"].includes(initialView)?[{key:"assign",label:"分配客户"}',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
    ):
        assert token in normalized_customer, f"customer-dept original list contract missing: {token}"
    for token in (
        '{key:"level-review",label:"审批客户分级"}',
        '{key:"key-change-review",label:"审批关键字段变更"}',
        '{key:"portal-open",label:"开通/重置客户服务端"}',
        '{key:"portal-close",label:"停用客户服务端"}',
    ):
        assert token in normalized_customer, f"customer PDF-alignment action missing: {token}"
    assignment_start = CUSTOMER.index('open={Boolean(assigning)}')
    assignment_end = CUSTOMER.index('<Modal', assignment_start)
    assignment_source = CUSTOMER[assignment_start:assignment_end]
    normalized_assignment = re.sub(r"\s+", "", assignment_source)
    for token in (
        'title="客户分配"', 'okText="确定"', 'cancelText="取消"',
        'label="客户编码"', 'label="客户名称"', 'label="原客戶管理人"', 'label="现客戶管理人"',
        '<InputreadOnlyvalue={assigning?.serial_no||""}/>',
        '<InputreadOnlyvalue={assigning?.title||""}/>',
        'name="manager"', '<SelectshowSearch',
    ):
        assert token in normalized_assignment, f"customer-dept assignment dialog missing: {token}"
    assert "分配说明" not in assignment_source and "第一位客户管理人" not in assignment_source, "customer-dept assignment dialog must not invent fields or help text"
    assert 'api.put(`/customers/${assigning.id}/managers`,{managers:[values.manager]})' in normalized_customer, "customer-dept assignment must submit one selected manager through the protected API"
    for token in (
        'ifscopein{"department","department_recycle"}:',
        'ifcurrent_user.rolenotin{"admin","manager"}:',
        'conditions.append(BusinessRecord.department==current_user.department)',
    ):
        assert token in normalized_main_customer, f"customer-dept scope contract missing: {token}"
    for token in (
        'call("GET","/customers?scope=department",expected=(403,))',
        'department_page=call("GET","/customers?scope=department&page=1&page_size=1")',
        'admin_department=call("GET",f"/customers?scope=department&customer_name=',
        'department_assigned=call("PUT",f"/customers/{department_substring_record[\'id\']}/managers"',
        'department_assignment_restored=call("PUT",f"/customers/{department_substring_record[\'id\']}/managers"',
    ):
        assert token in NORMALIZED_SMOKE, f"customer-dept smoke evidence missing: {token}"

    # Original-evidence contract for /6001004/CRM/Customer/CustomerList.
    assert '("customer-dept-recycle", "customer", "部门回收站", "", 35)' in MAIN
    assert '{ key: "customer-dept-recycle", label: "部门回收站" }' in APP
    for token in (
        '"customer-dept-recycle":"department_recycle"',
        'constisReadOnlyCustomerList=isOriginalCustomerList',
        'setDetailPageOpen(isReadOnlyCustomerList)',
        'initialView==="customer-dept-recycle"?"部门回收站"',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&v==="已回收"?"已删除":v',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-recent-update"].includes(initialView)?",":"、"',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
        '["customer-recycle","customer-dept-recycle","customer-company-recycle"].includes(initialView)?[{key:"restore",label:"客户恢复"},{key:"release",label:"进入公海"}]',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&(<Buttondisabled={page===customerPageCount}onClick={()=>goToCustomerPage(customerPageCount)}>»</Button>)',
    ):
        assert token in normalized_customer, f"customer-dept-recycle original contract missing: {token}"
    manager_lock_start = CUSTOMER.index('const managerLocked = [')
    manager_lock_end = CUSTOMER.index('].includes(initialView);', manager_lock_start)
    assert 'customer-dept-recycle' not in CUSTOMER[manager_lock_start:manager_lock_end], "department recycle manager filter must remain editable"
    for token in (
        'scope:str=Query("mine",pattern="^(mine|recycle|department|department_recycle|company|company_recycle|public|shared|recent_contact|recent_update)$")',
        'ifscopein{"recycle","department_recycle","company_recycle"}:',
        'ifscopein{"department","department_recycle"}:',
    ):
        assert token in normalized_main_customer, f"customer-dept-recycle API scope missing: {token}"
    for token in (
        'call("GET","/customers?scope=department_recycle",expected=(403,))',
        'department_recycle_page=call("GET","/customers?scope=department_recycle&page=1&page_size=1")',
        'restored_department_customer=call("POST",f"/customers/{department_recycle_record[\'id\']}/restore"',
        'released_department_customer=call("POST",f"/customers/{department_recycle_record[\'id\']}/release"',
        'admin_department_recycle=call("GET",f"/customers?scope=department_recycle&customer_name=',
    ):
        assert token in NORMALIZED_SMOKE, f"customer-dept-recycle smoke evidence missing: {token}"

    # Original-evidence contract for /6001005/CRM/Customer/CustomerList.
    assert '("customer-company", "customer", "公司客户", "", 36)' in MAIN
    assert '{ key: "customer-company", label: "公司客户" }' in APP
    for token in (
        '"customer-company":"company"',
        'elseif(["customer-mine","customer-dept","customer-company","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)){',
        'initialView==="customer-company"?"公司客户"',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&v==="已回收"?"已删除":v',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-recent-update"].includes(initialView)?",":"、"',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&(<Buttondisabled={page===customerPageCount}onClick={()=>goToCustomerPage(customerPageCount)}>»</Button>)',
        '["customer-dept","customer-company"].includes(initialView)?[{key:"assign",label:"分配客户"}',
    ):
        assert token in normalized_customer, f"customer-company original contract missing: {token}"
    assert 'customer-company' not in CUSTOMER[manager_lock_start:manager_lock_end], "company customer manager filter must remain editable"
    assert normalized_assignment.count('label="客户编码"') == 1 and 'name="manager"' in normalized_assignment, "company assignment must reuse the exact single-manager dialog"
    for token in (
        'elifscope=="company":',
        'conditions.append(BusinessRecord.status!="公海")',
        'elifscopein{"company","company_recycle"}andcurrent_user.role!="admin":',
    ):
        assert token in normalized_main_customer, f"customer-company API scope missing: {token}"
    for token in (
        'call("GET","/customers?scope=company",expected=(403,))',
        'company_page=call("GET","/customers?scope=company&page=1&page_size=1")',
        'company_recycled=call("GET",f"/customers?scope=company&customer_name=',
        'company_assigned=call("PUT",f"/customers/{shanghai_record[\'id\']}/managers"',
        'company_assignment_restored=call("PUT",f"/customers/{shanghai_record[\'id\']}/managers"',
    ):
        assert token in NORMALIZED_SMOKE, f"customer-company smoke evidence missing: {token}"

    # Original-evidence contract for /6001006/CRM/Customer/CustomerList.
    # The empty state and hidden controls were observed directly.  The non-empty
    # 15-row/six-size pager follows the shared customer-list template contract
    # because the inspected administrator account currently has no public rows.
    assert '("customer-public", "customer", "公海客户", "", 37)' in MAIN
    assert '{ key: "customer-public", label: "公海客户" }' in APP
    for token in (
        '"customer-public":"public"',
        'elseif(["customer-mine","customer-dept","customer-company","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)){',
        'constisReadOnlyCustomerList=isOriginalCustomerList',
        'initialView==="customer-public"?"公海客户"',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-recent-update"].includes(initialView)?",":"、"',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
        'initialView==="customer-public"?[{key:"claim",label:"拾回"}]',
        'if(key==="claim")voidaction(target,"claim")',
        'pageSize:15',
        'options={[10,15,20,50,100,200].map((value)=>({value,label:String(value)}))}',
    ):
        assert token in normalized_customer, f"customer-public original contract missing: {token}"
    assert 'customer-public' not in CUSTOMER[manager_lock_start:manager_lock_end], "public customer manager filter must remain editable"
    public_action_start = normalized_customer.index('initialView==="customer-public"?')
    public_action_end = normalized_customer.index(':[' , public_action_start)
    assert 'claim' in normalized_customer[public_action_start:public_action_end], "public customer must expose the pickup action"
    for token in (
        'elifscope=="public":',
        'conditions.append(BusinessRecord.status=="公海")',
        'admin_public=call("GET",f"/customers?scope=public&customer_name=',
        'claimed_public=call("POST",f"/customers/{public_record[\'id\']}/claim"',
    ):
        source = normalized_main_customer if token.startswith(('elif', 'conditions')) else NORMALIZED_SMOKE
        assert token in source, f"customer-public API/smoke evidence missing: {token}"

    # Original-evidence contract for /6001007/CRM/Customer/CustomerList.
    # The administrator's original page was empty, so its exact empty-state
    # hiding and read-only View page were observed directly.  Non-empty totals,
    # the 15-row/six-size pager and the multi-manager separator intentionally
    # retain the common customer-list template contract as indirect evidence.
    assert '("customer-shared", "customer", "我的共享客户", "", 38)' in MAIN
    assert '{ key: "customer-shared", label: "我的共享客户" }' in APP
    for token in (
        '"customer-shared":"shared"',
        'elseif(["customer-mine","customer-dept","customer-company","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)){',
        'constisReadOnlyCustomerList=isOriginalCustomerList',
        'initialView==="customer-shared"?"我的共享客户"',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
        'initialView==="customer-shared"?[]',
        '...(["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?{}:{manager:managerKeyword})',
        '["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?"":isOriginalCustomerList&&managerLocked',
        'initialView==="customer-shared"?"没有查询到事项记录，可以去新建"',
        'initialView==="customer-shared"?"没有查询到客户文件，可以去上传客户文件"',
        'pageSize:15',
        'options={[10,15,20,50,100,200].map((value)=>({value,label:String(value)}))}',
    ):
        assert token in normalized_customer, f"customer-shared original contract missing: {token}"
    shared_action_start = normalized_customer.index('initialView==="customer-shared"?[]')
    shared_action_end = normalized_customer.index(':initialView==="customer-public"', shared_action_start)
    assert 'key:' not in normalized_customer[shared_action_start:shared_action_end], "shared customer must not invent a more-action item"
    assert 'customer-shared' in CUSTOMER[manager_lock_start:manager_lock_end], "shared customer manager filter must remain disabled"
    comma_join_start = normalized_customer.index('.map(userLabel).join(["customer-recycle"')
    comma_join_end = normalized_customer.index('),', comma_join_start)
    assert 'customer-shared' not in normalized_customer[comma_join_start:comma_join_end], "shared customer keeps the personal-list multi-manager separator contract"
    for token in (
        'elifscope=="shared":',
        'conditions.append(BusinessRecord.status.not_in(["已回收","公海"]))',
        'shared_page=call("GET",f"/customers?scope=shared&customer_name=',
        'admin_shared=call("GET",f"/customers?scope=shared&customer_name=',
    ):
        source = normalized_main_customer if token.startswith(('elif', 'conditions')) else NORMALIZED_SMOKE
        assert token in source, f"customer-shared API/smoke evidence missing: {token}"

    # Original-evidence contract for /6001008/CRM/Customer/CustomerList.
    # The administrator's inspected page was empty.  Its GET form, three
    # filters, blank disabled manager field, default page size, exact empty
    # state and hidden totals/footer/pager were observed directly.  The common
    # 13-column template, read-only four-section/three-tab View and the sole
    # non-empty 客户编辑 menu entry were additionally confirmed from the page
    # template and a safe direct GET of View; no original write was submitted.
    assert '("customer-recent-contact", "customer", "最近联系的客户", "", 39)' in MAIN
    assert '{ key: "customer-recent-contact", label: "最近联系的客户" }' in APP
    for token in (
        '"customer-recent-contact":"recent_contact"',
        'elseif(["customer-mine","customer-dept","customer-company","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)){',
        'constisReadOnlyCustomerList=isOriginalCustomerList',
        'initialView==="customer-recent-contact"?"最近联系的客户"',
        '(["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?{}:{manager:managerKeyword})',
        '["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?""',
        '["customer-recent-contact","customer-recent-update"].includes(initialView)?[{key:"edit",label:"客户编辑"}]',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
        'pageSize:15',
        'options={[10,15,20,50,100,200].map((value)=>({value,label:String(value)}))}',
        'locale={{emptyText:"没有查询到符合条件的记录。"}}',
    ):
        assert token in normalized_customer, f"customer-recent-contact original contract missing: {token}"
    assert 'customer-recent-contact' in CUSTOMER[manager_lock_start:manager_lock_end], "recent-contact manager filter must be disabled"
    recent_action_start = normalized_customer.index('["customer-recent-contact","customer-recent-update"].includes(initialView)?')
    recent_action_end = normalized_customer.index(':[];', recent_action_start)
    recent_action_source = normalized_customer[recent_action_start:recent_action_end]
    assert recent_action_source.count('key:') == 1 and 'key:"edit"' in recent_action_source, "recent-contact must expose only customer edit"
    assert '(b.data.last_contact_at||"").localeCompare' not in normalized_customer, "recent-contact ordering must be server-side, not a truncated client sort"
    for token in (
        'elifscope=="recent_contact":',
        'ifscope=="recent_contact":',
        'def_parse_customer_contact_at(value:object)->datetime|None:',
        '_parse_customer_contact_at((item.dataor{}).get("last_contact_at"))isnotNone',
        'candidate_rows.sort(',
        '_parse_customer_contact_at((item.dataor{}).get("last_contact_at"))ordatetime.min',
    ):
        assert token in normalized_main_customer, f"customer-recent-contact API contract missing: {token}"
    for protected_contact_field in ('"notes"', '"last_contact_at"', '"contact_count"'):
        assert protected_contact_field in normalized_main_customer, f"customer contact metric protection missing: {protected_contact_field}"
    assert '"/customers?scope=recent_contact' in SMOKE, "customer-recent-contact smoke coverage is missing"

    # Original-evidence contract for /6001009/CRM/Customer/CustomerList.
    # The inspected page had one recycled row.  Its GET form, three filters,
    # blank disabled manager field, common 13 business columns, two amount
    # totals, comma-separated managers, edit-only menu and complete pager were
    # observed directly.  A safe no-match GET additionally proved that totals,
    # footer and pager all disappear with the exact common empty-state text.
    assert '("customer-recent-update", "customer", "最近更新的客户", "", 40)' in MAIN
    assert '{ key: "customer-recent-update", label: "最近更新的客户" }' in APP
    for token in (
        '"customer-recent-update":"recent_update"',
        'elseif(["customer-mine","customer-dept","customer-company","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)){',
        'constisReadOnlyCustomerList=isOriginalCustomerList',
        'initialView==="customer-recent-update"?"最近更新的客户"',
        '(["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?{}:{manager:managerKeyword})',
        '["customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)?""',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&v==="已回收"?"已删除":v',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-recent-update"].includes(initialView)?",":"、"',
        '["customer-recent-contact","customer-recent-update"].includes(initialView)?[{key:"edit",label:"客户编辑"}]',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)&&<divclassName="customer-grid-footer">',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&(<Buttondisabled={page===customerPageCount}onClick={()=>goToCustomerPage(customerPageCount)}>»</Button>)',
        'displayDate(initialView==="customer-recent-update"?r.updated_at:r.data.last_modified_date||r.updated_at)',
        'pageSize:15',
        'options={[10,15,20,50,100,200].map((value)=>({value,label:String(value)}))}',
        'locale={{emptyText:"没有查询到符合条件的记录。"}}',
    ):
        assert token in normalized_customer, f"customer-recent-update original contract missing: {token}"
    assert 'customer-recent-update' in CUSTOMER[manager_lock_start:manager_lock_end], "recent-update manager filter must be disabled"
    recent_update_action_start = normalized_customer.index('["customer-recent-contact","customer-recent-update"].includes(initialView)?')
    recent_update_action_end = normalized_customer.index(':[];', recent_update_action_start)
    recent_update_action_source = normalized_customer[recent_update_action_start:recent_update_action_end]
    assert recent_update_action_source.count('key:') == 1 and 'key:"edit"' in recent_update_action_source, "recent-update must expose only customer edit"
    assert 'if(initialView==="customer-recent-update")list.sort' not in normalized_customer, "recent-update ordering must be server-side, not a truncated client sort"
    for token in (
        'elifscope=="recent_update":',
        'conditions.append(BusinessRecord.status!="公海")',
        'ifscope=="recent_update":',
        'latest_modifier_by_record:dict[int,str]={}',
        'WorkflowEvent.action.in_(CUSTOMER_MODIFICATION_ACTIONS)',
        ').strip()==identity["username"]',
        'def_mark_customer_modified(customer:BusinessRecord,identity:dict)->None:',
        'data["last_modified_by"]=identity["username"]',
        'CUSTOMER_SYSTEM_DATA_FIELDS={"notes","last_contact_at","contact_count","last_modified_by","last_modified_date",',
        'forprotected_customer_fieldinCUSTOMER_SYSTEM_DATA_FIELDS:',
    ):
        assert token in normalized_main_customer, f"customer-recent-update API contract missing: {token}"
    for token in (
        '"/customers?scope=recent_update',
        '"last_modified_by":outsider_name',
        'expected=(409,)',
        'recent_update_recycled',
        'recent_update_public',
    ):
        assert token in NORMALIZED_SMOKE, f"customer-recent-update smoke contract missing: {token}"

    # Original-evidence contract for /6001010/CRM/Customer/CustomerList.
    # The inspected administrator page had 17 recycled rows.  Its editable
    # manager filter, comma-separated managers, two amount totals, complete
    # pager, restore/public menu, read-only View and exact empty-state hiding
    # were all observed directly; no original write was submitted.
    assert '("customer-company-recycle", "customer", "公司回收站", "", 41)' in MAIN
    assert '{ key: "customer-company-recycle", label: "公司回收站" }' in APP
    for token in (
        '"customer-company-recycle":"company_recycle"',
        '["customer-recycle","customer-dept-recycle","customer-company-recycle"].includes(initialView)',
        'constisReadOnlyCustomerList=isOriginalCustomerList',
        'initialView==="customer-company-recycle"?"公司回收站"',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-recent-update"].includes(initialView)?",":"、"',
        '["customer-recycle","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&v==="已回收"?"已删除":v',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)&&rows.length===0?undefined',
        '(!["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-public","customer-shared","customer-recent-contact","customer-recent-update"].includes(initialView)||rows.length>0)',
        '["customer-recycle","customer-dept-recycle","customer-company-recycle"].includes(initialView)?[{key:"restore",label:"客户恢复"},{key:"release",label:"进入公海"}]',
        '["customer-recycle","customer-dept","customer-dept-recycle","customer-company","customer-company-recycle","customer-recent-update"].includes(initialView)&&(<Buttondisabled={page===customerPageCount}onClick={()=>goToCustomerPage(customerPageCount)}>»</Button>)',
        'pageSize:15',
        'options={[10,15,20,50,100,200].map((value)=>({value,label:String(value)}))}',
        'locale={{emptyText:"没有查询到符合条件的记录。"}}',
    ):
        assert token in normalized_customer, f"customer-company-recycle original contract missing: {token}"
    assert 'customer-company-recycle' not in CUSTOMER[manager_lock_start:manager_lock_end], "company recycle manager filter must remain editable"
    for token in (
        'scope:str=Query("mine",pattern="^(mine|recycle|department|department_recycle|company|company_recycle|public|shared|recent_contact|recent_update)$")',
        'ifscopein{"recycle","department_recycle","company_recycle"}:',
        'elifscopein{"company","company_recycle"}andcurrent_user.role!="admin":',
    ):
        assert token in normalized_main_customer, f"customer-company-recycle API scope missing: {token}"
    for token in (
        'call("GET","/customers?scope=company_recycle",expected=(403,))',
        'company_recycle_page=call("GET","/customers?scope=company_recycle&page=1&page_size=1")',
        'exact_company_recycle=call("GET",f"/customers?scope=company_recycle&customer_name=',
        'restored_company_customer=call("POST",f"/customers/{company_recycle_record[\'id\']}/restore"',
        'released_company_customer=call("POST",f"/customers/{company_recycle_record[\'id\']}/release"',
    ):
        assert token in NORMALIZED_SMOKE, f"customer-company-recycle smoke evidence missing: {token}"

    # Original-evidence contract for /6001011/CRM/Customer/CustomerSearching.
    # The original page keeps a one-field first step after an exact miss and
    # replaces it with exactly eight read-only enterprise fields after a hit.
    # Enter does not submit and there are no result tables, risk badges,
    # pagination, record links, drawers or second-step actions.
    assert '("customer-conflict", "customer", "客户利益检索", "", 42)' in MAIN
    assert '{ key: "customer-conflict", label: "客户利益检索" }' in APP
    assert 'route === "customer-conflict" ? (' in APP and '<CustomerConflictPage />' in APP
    normalized_app = re.sub(r"\s+", "", APP)
    for token in (
        'constcanUseCustomerConflict=sessionUser?.role==="admin"||Boolean(sessionUser?.menu_keys?.includes("customer-conflict"));',
        'child.key!=="customer-conflict"||canUseCustomerConflict',
        '(route!=="customer-conflict"||canUseCustomerConflict)',
    ):
        assert token in normalized_app, f"customer-conflict leaf permission UI guard missing: {token}"
    normalized_conflict = re.sub(r"\s+", "", CUSTOMER_CONFLICT)
    normalized_conflict_css = re.sub(r"\s+", "", CUSTOMER_CONFLICT_CSS)
    for token in (
        'title="客户利益冲突检索"',
        '>1.输入完整企业名称</div>',
        '>2.企业信息</div>',
        'className={foundItem?"":"active"}',
        '温馨提示：1.需要输入完整的企业名称，才能查看具体信息.',
        '<label>企业名称：</label>',
        '<Buttonloading={loading}onClick={search}><span>检索</span></Button>',
        'message.warning("请输入企业名称.")',
        'params:{name:query},signal:controller.signal',
        'error?.code!=="ERR_CANCELED"',
        '未找到该企业基本信息.',
        '{key:"enterprise_name",label:"企业名称"}',
        '{key:"latest_case_no",label:"最新立案号"}',
        '{key:"latest_case_date",label:"最新立案日期"}',
        '{key:"plaintiffs",label:"原告"}',
        '{key:"defendants",label:"被告"}',
        '{key:"third_parties",label:"第三人"}',
        '{key:"our_customer",label:"我方客户"}',
        '{key:"customer_managers",label:"客户管理人"}',
        'Array.isArray(value)?value.join(","):value||""',
        '<InputreadOnlyvalue={displayValue(field.key,foundItem[field.key])}/>',
    ):
        assert token in normalized_conflict, f"customer-conflict original contract missing: {token}"
    for forbidden in ("onPressEnter", "<Table", "<Drawer", "<Alert", "<Tag", "pagination", "viewRecord"):
        assert forbidden not in CUSTOMER_CONFLICT, f"customer-conflict must not invent original interaction: {forbidden}"
    for token in (
        '.conflict-steps{display:grid;grid-template-columns:1fr1fr;height:25px;',
        '.conflict-steps>div.active{background:linear-gradient(#10b9c4,#079ab0);}',
        'border-left:13pxsolid#c8c8c8;',
        '.conflict-steps>div:first-child.active::after{border-left-color:#079ab0;}',
        '.conflict-search{display:grid;grid-template-columns:95px300px;',
        '.conflict-enterprise-grid{display:grid;grid-template-columns:1fr;',
        'border:1pxsolid#ddd;',
        '.conflict-enterprise-field{display:grid;grid-template-columns:120px350px;',
        'width:600px;min-height:44px;',
        '.conflict-enterprise-field.ant-input{height:26px;',
        'background:transparent;border-color:transparent;',
    ):
        assert token in normalized_conflict_css, f"customer-conflict visual contract missing: {token}"
    for token in (
        'CASE_PLAINTIFF_FIELDS=(',
        'CASE_DEFENDANT_FIELDS=(',
        'CASE_THIRD_PARTY_FIELDS=(',
        'def_normalize_conflict_entity(value:object)->str:',
        'unicodedata.normalize("NFKC",str(valueor""))',
        'def_conflict_entity_tokens(value:object)->list[str]:',
        'asyncdef_require_customer_conflict_permission(identity:dict,db:AsyncSession)->None:',
        'if"customer-conflict"notinset(permission.get("menu_keys",[])):',
        'def_empty_customer_conflict_result(query:str)->dict:',
        'name:str=Query(min_length=1,max_length=100)',
        'query=name.strip()',
        'raiseHTTPException(status_code=422,detail="企业名称不能为空")',
        'ifany(_normalize_conflict_entity(entity)==needleforentityin_case_conflict_entities(case_record))',
        'key=lambdacase_record:(_case_filing_date(case_record)ordate.min,case_record.id)',
        '"found":True',
        '"enterprise_name":query',
        '"latest_case_no":latest_case.serial_no',
        '"latest_case_date":filing_date.isoformat()iffiling_dateelse""',
        '"customer_managers":await_conflict_customer_managers(query,db)',
    ):
        assert token in normalized_main_customer, f"customer-conflict API contract missing: {token}"
    for token in (
        'call("GET",f"/customers/conflicts?name={urllib.parse.quote(\'\')}"',
        'call("GET",f"/customers/conflicts?name={urllib.parse.quote(partial_name)}")["found"]isFalse',
        '"found","query","enterprise_name","latest_case_no","latest_case_date",',
        'assertset(result)==expected_keysandresult["found"]isTrue',
        'assert"id"notinresultand"items"notinresultand"risk"notinresult',
        'whole_firm_result=call("GET",f"/customers/conflicts?name=',
        'call("GET",f"/customers/conflicts?name={urllib.parse.quote(\'任意完整企业名称\')}",expected=(403,))',
        'assert"customer-conflict"inuser_permission["menu_keys"]',
        'without_conflict_leaf=[keyforkeyincurrent_user_permission["menu_keys"]ifkey!="customer-conflict"]',
        'current_user_permission=next(itemforitemincall("GET","/system/role-permissions")["items"]ifitem["role"]=="user")',
    ):
        # A few expressions include runtime values; compact substring checks
        # keep the gate stable while still proving each behavior is exercised.
        if token not in NORMALIZED_SMOKE:
            # Preserve a precise failure instead of silently weakening the
            # contract when smoke implementation changes.
            raise AssertionError(f"customer-conflict smoke contract missing: {token}")

    # Route-only guard for the next task page.  This intentionally proves only
    # menu/deep-link wiring; original unread-page fields and behavior require a
    # separate evidence contract after the original page has been inspected.
    assert '("task-my-unread", "task-my", "未读新消息的任务", "", 4)' in MAIN, "my-unread task backend menu declaration is missing"
    assert '{ key: "task-my-unread", label: "未读新消息的任务" }' in APP, "my-unread task fallback menu declaration is missing"
    assert 'new URLSearchParams(window.location.search).get("page") || "dashboard"' in APP, "page query deep-link initialization is missing"
    assert 'window.addEventListener("popstate", restoreRouteFromHistory)' in APP, "browser history must restore the selected deep route"
    assert 'window.history.pushState(' in APP and 'params.set("page", active)' in APP, "menu navigation must keep the page query synchronized"
    assert 'const route = canonicalRoute(active);\n  const activeRoot =\n    route === "dashboard"\n      ? "dashboard"\n      : rootMenuKey(effectiveMenuItems, route);' in APP, "deep routes must resolve authorization from their canonical menu parent"
    assert 'const ancestors = ancestorMenuKeys(effectiveMenuItems, active)' in APP, "deep routes must expand their parent menus"
    assert '<TaskCenterPage initialView={active}' in APP, "task routes must preserve the unread leaf key when rendering"
    assert '{ key: "task-reminders", label: "任务提醒" }' not in APP, "original sidebar must not invent a visible task-reminders fallback leaf"
    assert 'item.key !== "task-reminders"' in APP, "configured backend menus must not re-expose the internal task-reminders route in the sidebar"
    assert "task:'task-reminders'" in NOTIFICATION, "task notifications must retain their internal reminder route"
    for token in (
        'constisReminder=initialView==="task-reminders";',
        'reminder_only:isReminder||undefined,',
        'taskMeta.total===0&&(isCollaborating||isUnread||isReminder||',
    ):
        assert token in NORMALIZED_TASK, f"internal task-reminders compatibility contract missing: {token}"
    normalized_main = re.sub(r"\s+", "", MAIN)
    for token in (
        'LEGACY_TASK_MENU_KEYS={"task-reminders"}',
        'forkeyinLEGACY_TASK_MENU_KEYS:',
        'f"task-{task.id}-{today}-{username}"',
        'reminder_only:bool=False',
        'source_type:str=""',
        'level:str=""',
        'page:int=Query(1,ge=1)',
        'page_size:int=Query(100,ge=1,le=200)',
    ):
        assert token in normalized_main, f"task reminder backend contract missing: {token}"
    for token in (
        "legacy_task_menus",
        "manager_notice_page",
        "admin_notice_first",
        "admin_notice_second",
        "member_notice_page",
        "outsider_notice_page",
        'call("POST",f"/notifications/{admin_notice_id}/read",expected=(404,))',
    ):
        assert token in NORMALIZED_SMOKE, f"task reminder smoke evidence missing: {token}"

    assert 'route.startsWith("case-files-")' not in APP, "case receipt/invoice routes must not collapse into the generic document page"
    assert 'active.startsWith("investigation-task-")' in APP, "investigation parent/subtask routes must stay in InvestigationCenterPage"
    for token in ('initialView==="case-files-receipt"', 'initialView==="case-files-invoice"', 'endsWith("-stage")', 'endsWith("-no-refund")'):
        assert token in CASE, f"missing dedicated case-page behavior token {token}"
    assert '("case-new-civil", "case-new", "民事争议", "", 1)' in MAIN, "civil case creation must be available from the case menu"
    assert "createForm.getFieldsValue(true)" in CASE, "case wizard must submit values preserved from all three steps"
    assert 'owner: profile.username || "admin"' in CASE, "case creation must bind the signed-in account instead of a hard-coded administrator"
    assert "useState<Profile>(initialProfile)" in CUSTOMER, "customer creation must synchronously initialize the signed-in profile"
    assert "useState<Profile>(initialProfile)" in CONTRACT, "contract creation must synchronously initialize the signed-in profile"
    assert 'owner: profile.username || "admin"' in TASK, "task creation must default to the signed-in account"

    # The staged create form must expose every supported case type and keep the
    # contract as the source of customer and source-person master data.
    assert '("case-new-criminal", "case-new", "刑事案件", "", 2)' in MAIN
    assert '"民事案件": "case-new-civil"' in MAIN, "legacy civil creation capability must remain backend-compatible"
    case_fallback_start = fallback_menu.index('key: "case"')
    case_fallback_end = fallback_menu.index('key: "investigation"', case_fallback_start)
    case_fallback = fallback_menu[case_fallback_start:case_fallback_end]
    assert '{ key: "case-new-civil", label: "民事争议" }' in case_fallback
    assert '{ key: "case-new-criminal", label: "刑事案件" }' in case_fallback
    assert 'item.key !== "case-new-civil"' not in APP, "configured navigation must not hide civil case creation"
    route_create_start = CASE.index('{isCreateView && (')
    route_create_end = CASE.index('{specialMode ?', route_create_start)
    route_create = CASE[route_create_start:route_create_end]
    normalized_route_create = re.sub(r"\s+", "", route_create)
    step_one_start = route_create.index('{createStep === 0 && (')
    step_one_end = route_create.index('{createStep === 1 && (', step_one_start)
    step_one = route_create[step_one_start:step_one_end]
    expected_step_one_fields = [
        'label="案件类型"', 'label="客户"', 'label="客户诉讼地位"', 'label="合同号"',
        'label="案源人"', 'isCriminalCreate?"罪名":"案由"', 'label="案件名称"',
        'label="案件阶段"', 'label="经办律师"', 'label="律师助理"',
    ]
    normalized_step_one = re.sub(r"\s+", "", step_one)
    field_positions = [normalized_step_one.index(token) for token in expected_step_one_fields]
    assert field_positions == sorted(field_positions), "criminal create first-step fields are missing or out of order"
    for token in (
        'className="case-create-route-page"',
        'className="case-create-steps"',
        '{title:"基本信息"},{title:"当事人信息"},{title:"司法机关信息"}',
        'options={clientPositionOptions.map((value)=>({value,label:value}))}',
        'value==="新案待分配"?"待分配":value',
        '>下一步</Button>',
    ):
        assert token in normalized_route_create, f"criminal create route first-step contract missing: {token}"

    normalized_case = re.sub(r"\s+", "", CASE)
    step_two_start = route_create.index('{createStep === 1 && (', step_one_end)
    step_two_end = route_create.index('{createStep === 2 && !isCounselCreate && (', step_two_start)
    step_two = route_create[step_two_start:step_two_end]
    normalized_step_two = re.sub(r"\s+", "", step_two)
    for token in (
        'name="plaintiffs"', 'name="plaintiff_agents"',
        'name="defendants"', 'name="defendant_agents"',
        'name="third_parties"', 'name="third_party_agents"',
    ):
        assert token in normalized_step_two, f"criminal litigants step is missing party/agent field: {token}"
    for token in (
        'api.put(`/cases/${createdCaseId}/litigants`',
        'plaintiff_agents:', 'defendant_agents:', 'third_party_agents:',
        'createStep===1&&(isCounselCreate?<Buttontype="primary"loading={createSubmitting}onClick={()=>voidsaveLitigants(true)}>完成</Button>',
        'onClick={()=>voidsaveLitigants(true)}>完成</Button>',
        'createStep===2&&<Buttontype="primary"loading={createSubmitting}onClick={finishCreateFlow}>完成</Button>',
    ):
        assert token in normalized_route_create or token in normalized_case, f"criminal litigants step flow missing: {token}"

    step_three_start = route_create.index('{createStep === 2 && !isCounselCreate && (', step_two_end)
    step_three_end = route_create.index('<div className="case-create-actions">', step_three_start)
    normalized_step_three = re.sub(r"\s+", "", route_create[step_three_start:step_three_end])
    for token in (
        'name="public_security_name"', 'name="public_security_case_no"',
        'name="first_procuratorate_name"', 'name="second_procuratorate_name"',
        'name="retrial_procuratorate_name"',
        'name="first_court_name"', 'name="second_court_name"',
        'name="retrial_court_name"',
    ):
        assert token in normalized_step_three, f"criminal judicial step is missing evidenced authority field: {token}"
    assert 'api.put(`/cases/${createdCaseId}/judicial`' in normalized_case, "criminal judicial step must submit through its dedicated endpoint"
    for token in (
        'client_position:isCounselCreate?"":isCriminalCreate?"被告人/犯罪嫌疑人":"原告/申请人"',
        'handling_lawyers:[operator]',
        'assistant:operator',
        'if(isCreateView)startCreate();',
    ):
        assert token in normalized_case, f"criminal create lifecycle contract missing: {token}"
    for token in (
        'constisAdministrativeCreate=effectiveCreateType==="行政案件及国家赔偿"',
        'constisCounselCreate=effectiveCreateType==="法律顾问"',
        'createFlowToken=isCounselCreate?"CASE_NEW_COUNSEL_STAGED_FLOW_OK":isAdministrativeCreate?"CASE_NEW_ADMINISTRATIVE_STAGED_FLOW_OK":effectiveCreateType==="民事案件"?"CASE_NEW_CIVIL_STAGED_FLOW_OK":"CASE_NEW_CRIMINAL_STAGED_FLOW_OK"',
        'data-flow-token={createFlowToken}',
        'right_type:isCounselCreate?"":String(values.right_type||"").trim()',
        '["被告人/犯罪嫌疑人","被告/被申请人"].includes(values.client_position)',
        'values.client_position==="第三人"',
        '!isAdministrativeCreate&&<Buttonloading={createSubmitting}onClick={()=>voidsaveLitigants(true)}>完成</Button>',
        'createRedirectPage=isCounselCreate?"case-company-counsel":isAdministrativeCreate?"case-company-administrative":effectiveCreateType==="民事案件"?"case-company-civil":effectiveCreateType==="仲裁"?"case-company-arbitration":"case-company-criminal"',
        'params.set("page",createRedirectPage)',
        '{isCriminalCreate&&<><divclassName="case-create-section-title">公安机关</div>',
    ):
        assert token in normalized_case, f"administrative case create route guard missing: {token}"
    assert 'case-create-route-modal' not in CASE and 'case-create-route-modal' not in CASE_CSS, "case creation routes must not render as a modal"
    assert '<Alert' not in route_create, "criminal route first screen must not invent modal alerts"
    for token in (
        '<RecordImportButtonmodule="case"',
        'onClick={startCreate}>新增案件</Button>',
        'onClick={deleteSelectedCase}>删除案件</Button>',
    ):
        assert token not in normalized_case, f"generic case control must not be visible after original-page evidence: {token}"
    normalized_case_css = re.sub(r"\s+", "", CASE_CSS)
    assert '.case-create-route-page{min-height:calc(100vh-95px);padding:8px;background:#fff}' in normalized_case_css
    for token in (
        'CASE_CREATABLE_TYPES = {"民事案件", "刑事案件", "行政案件及国家赔偿", "法律顾问", "仲裁"}',
        'CASE_SOURCE_CONTRACT_STATUSES = {"已通过", "履行中", "已完成"}',
        'permission_key = CASE_CREATE_PERMISSION_BY_TYPE[case_type]',
        'ADMINISTRATIVE_CLIENT_POSITIONS = {"原告/申请人", "被告/被申请人", "第三人"}',
        'if case_type == "行政案件及国家赔偿" and client_position not in ADMINISTRATIVE_CLIENT_POSITIONS:',
        'if case_type == "行政案件及国家赔偿":',
        'raise HTTPException(status_code=422, detail="行政案件请至少录入一个法院信息")',
        'raise HTTPException(status_code=422, detail="行政案件不能填写公安或检察院信息")',
        'if body.status != "新案待分配":',
        'except IntegrityError as exc:',
        '@app.put(f"{settings.api_prefix}/cases/{{case_id}}/litigants")',
        '@app.put(f"{settings.api_prefix}/cases/{{case_id}}/complete-creation")',
        '@app.put(f"{settings.api_prefix}/cases/{{case_id}}/counsel-basic")',
        'if case_type == "法律顾问":',
        'raise HTTPException(status_code=422, detail="顾问期限不能为空")',
        'raise HTTPException(status_code=409, detail="法律顾问案件不使用司法机关步骤")',
        'if module == "case":',
        'GENERIC_RECORD_EDITABLE_MODULES = {"customer", "report", "system"}',
        'GENERIC_RECORD_DELETABLE_MODULES = {"report"}',
        'if record.module not in GENERIC_RECORD_EDITABLE_MODULES:',
        'if record.module not in GENERIC_RECORD_DELETABLE_MODULES:',
    ):
        assert token in MAIN, f"criminal case backend guard missing: {token}"
    for token in (
        'def _record_links_to_case(record: BusinessRecord, case_record: BusinessRecord) -> bool:',
        'linked_case_id = int(record_data.get("case_id") or record_data.get("case_record_id") or 0)',
        'return linked_case_id == case_record.id',
        'return str(record_data.get("case_no") or "") == case_record.serial_no',
        'if _record_links_to_case(item, case_record)',
    ):
        assert token in MAIN, f"case archive linkage must prefer case id: {token}"
    for token in (
        'call("PATCH",f"/records/{case[\'id\']}",{"status":"已归档"},expected=(409,))',
        'call("POST",f"/records/{case[\'id\']}/transition",{"to_status":"文书准备","comment":"禁止通用流转绕过"},expected=(409,))',
        'call("PUT",f"/cases/{case[\'id\']}/litigants",{',
        '"plaintiff_agents":["公诉人甲"]',
        'call("DELETE",f"/records/{case[\'id\']}",expected=(409,))',
        'ifmodule=="case":call("GET",f"/records/import-template?module={module}",expected=(409,))',
        'multipart_upload(f"/records/import?module={module}"',
        'eligible_contracts=call("GET","/cases/eligible-contracts")',
        '"case_type":"行政案件及国家赔偿"',
        '"client_position":"原告/申请人"',
        'call("PUT",f"/cases/{admin_case[\'id\']}/judicial",{},expected=(422,))',
        '"first_court_name":"上海市行政测试人民法院"',
        '"case_type":"法律顾问"',
        '"counsel_type":"常年法律顾问"',
        'call("PUT",f"/cases/{counsel_case[\'id\']}/complete-creation",{"comment":"法律顾问两步流程完成"})',
        '"完成法律顾问案件新建"',
        '"修改法律顾问案件基本信息"',
    ):
        assert token in NORMALIZED_SMOKE, f"criminal case smoke guard missing: {token}"
    print("CASE_NEW_CRIMINAL_FLOW_OK: /1001000002 direct three-step flow, dedicated litigant/judicial saves, evidenced party agents and criminal authorities, with generic case mutation controls blocked")
    print("CASE_NEW_ADMINISTRATIVE_FLOW_OK: administrative create keeps dedicated right type, parties, court-only judicial data and administrative redirect")
    print("CASE_NEW_COUNSEL_FLOW_OK: legal counsel create uses the evidenced two-step flow, dedicated counsel term fields and a non-judicial completion endpoint")
    for token in (
        'constcounselListMode=originalListMode&&initialView.includes("counsel")',
        'label="顾问期间"name="counsel_range"',
        'label="顾问类型"name="counsel_type"',
        'columns={counselListMode?counselCaseColumns:originalCaseColumns}',
        'onClick={()=>voidopenCounselDetail(row)}',
        'title={`${viewingCounselCase?.data.case_type||"案件"}详情：${viewingCounselCase?.serial_no||""}`}',
        'label:"文档信息"', 'label:"律所费用"', 'label:"平台费用"', 'label:"内部结算"',
        'label:"系统日志"', 'label:"案件任务"', 'label:"客户任务"',
        'api.put(`/cases/${editingCounselCase.id}/counsel-basic`',
        'api.post("/cases/counsel/search"',
        'api.post("/cases/counsel/export"',
        'dataSource={counselListMode?counselCases:originalCases}',
        '>导出选中（CSV）</Button>',
        '>导出全部（CSV）</Button>',
    ):
        assert token in normalized_case, f"legal counsel list/detail contract missing: {token}"
    assert 'onClick={()=>voidopenCounselDetail(row)}' in normalized_case, "case number action must open the case detail drawer rather than the task-creation flow"
    normalized_main = re.sub(r"\s+", "", MAIN)
    assert 'asyncdef_next_case_serial(case_type:str,db:AsyncSession)->str:' in normalized_main and 'prefix=f"SH{type_code}{datetime.now():%y}"' in normalized_main and 'returnf"{prefix}{sequence:05d}"' in normalized_main, "case creation must generate the compact recognizable SH/type/year/sequence identifier"
    for token in (
        '@app.post(f"{settings.api_prefix}/cases/counsel/search")',
        '@app.post(f"{settings.api_prefix}/cases/counsel/export")',
        'if body.scope not in {"mine", "department", "company"}:',
        'if body.sort_order not in {"updated_desc", "case_no_asc", "case_no_desc"}:',
        'media_type="text/csv; charset=utf-8"',
        'raise HTTPException(status_code=403, detail="选中的案件不存在、不可见或不符合当前查询条件")',
    ):
        assert token in MAIN, f"legal counsel server paging/export guard missing: {token}"
    for token in (
        'call("POST","/cases/counsel/search",counsel_search)',
        '"document_name":f"counsel-filter-{suffix}.txt"',
        'selected_export=call("POST","/cases/counsel/export"',
        'selected_export[1].startswith(b"\\xef\\xbb\\xbf")',
        '"selected_ids":[counsel_case["id"],case["id"]]',
    ):
        assert token in NORMALIZED_SMOKE, f"legal counsel server paging/export smoke missing: {token}"
    print("CASE_COUNSEL_LIST_DETAIL_OK: evidenced counsel filters/columns, case detail tabs and protected basic-information editing")
    print("CASE_COUNSEL_SERVER_LIST_OK: role-scoped server paging/filter/sort plus selected/all CSV export with anti-bypass checks")

    # Original /9001001010 (my-created tasks) evidence contract.
    created_tabs_match = re.search(r"const createdTabs: StatusTab\[\] = \[(.*?)\n\];", TASK, re.S)
    assert created_tabs_match, "my-created task status tabs declaration not found"
    created_tab_labels = re.findall(r'label:\s*"([^"]+)"', created_tabs_match.group(1))
    assert created_tab_labels == [
        "进行中", "进行中-已完成", "进行中-拒绝", "进行中-已停止", "进行中-已撤回", "已验收",
    ], f"my-created task page must keep the six evidenced status tabs, got {created_tab_labels}"

    task_query_match = re.search(r"<Form<TaskQuery>(.*?)</Form>", TASK, re.S)
    assert task_query_match, "my-created task query form not found"
    task_query_fields = re.findall(r'name="([^"]+)"', task_query_match.group(1))
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], f"my-created task page must keep the 12 evidenced filters, got {task_query_fields}"

    task_columns_match = re.search(r"const standardColumns: any\[\] = \[(.*?)\n  \];\n  const unreadColumns", TASK, re.S)
    assert task_columns_match, "my-created task columns declaration not found"
    task_column_fields = re.findall(r'dataIndex:\s*"([^"]+)"', task_columns_match.group(1))
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], f"my-created task page must keep the 14 evidenced columns, got {task_column_fields}"
    assert 'title: isCreated && statusTab === "accepted" ? "验收日期" : "最后更新时间"' in task_columns_match.group(1), "the evidenced update-time column must become acceptance date on the accepted tab"
    for token in (
        "rowSelection={{selectedRowKeys:selectedKeys,onChange:setSelectedKeys,}}",
        "pageSize:15",
        "pageSizeOptions:[10,15,20,50,100,200]",
    ):
        assert token in NORMALIZED_TASK, f"my-created task selection/paging contract missing: {token}"

    task_more_match = re.search(r"<Dropdown\s+trigger=\{\[\"click\"\]\}(.*?)<Button>更多操作</Button>", TASK, re.S)
    assert task_more_match, "my-created task more-actions menu not found"
    task_more_keys = re.findall(r'key:\s*"([^"]+)"', task_more_match.group(1))
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], f"my-created task page must keep the 11 evidenced more-actions, got {task_more_keys}"
    for token in (
        'openDialog(selected, "resend")}>重新派发',
        'simpleAction(selected, "confirm")}>确认完成',
        'simpleAction(selected, "restart")}>退回重启',
    ):
        assert token in TASK, f"my-created task action is not reachable: {token}"

    detail_stages_match = re.search(
        r'<div className="task-detail-flow"[^>]*>\s*\{\[(.*?)\]\.map',
        TASK,
        re.S,
    )
    assert detail_stages_match, "task detail must render its evidenced four-stage flow"
    detail_stage_labels = re.findall(r'"([^"]+)"', detail_stages_match.group(1))
    assert detail_stage_labels == [
        "任务已分派", "任务处理中", "任务完成", "任务已验收",
    ], f"task detail must keep the four evidenced stages, got {detail_stage_labels}"
    for token in (
        'title="案件任务"',
        'className="task-detail-meta"',
        'className="task-detail-section-title">沟通记录',
    ):
        assert token in TASK, f"task detail dialog lost original structure: {token}"

    for token in (
        'relation: str = Query("", pattern="^(|initiated|owned|collaborating)$")',
        '"status_counts": status_counts',
        '"items": items, "total": total, "page": page, "page_size": effective_page_size',
        'if body.module == "task":',
        'if record.module not in GENERIC_RECORD_EDITABLE_MODULES:',
        'if record.module not in GENERIC_RECORD_TRANSITION_MODULES:',
    ):
        assert token in MAIN, f"task service/write-bypass contract missing: {token}"

    # Original /9001001020/TP/Task/TaskList (my-accepted tasks) evidence.
    assert '("task-my-accepted", "task-my", "我接受的任务", "", 2)' in MAIN, "my-accepted task route/menu declaration is missing"
    assert 'title="任务列表"' in TASK, "task pages must keep the original 任务列表 title"
    received_tabs_match = re.search(r"const receivedTabs: StatusTab\[\] = \[(.*?)\n\];", TASK, re.S)
    assert received_tabs_match, "my-accepted task status tabs declaration not found"
    received_tab_labels = re.findall(r'label:\s*"([^"]+)"', received_tabs_match.group(1))
    assert received_tab_labels == ["待处理", "进行中", "完成", "停止"], f"my-accepted task page must keep the four evidenced tabs, got {received_tab_labels}"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "my-accepted task page must reuse the 12 evidenced filters"
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], "my-accepted task page must reuse the selectable 14-column list"
    task_column_chunks = re.split(r"\n    (?=\{)", task_columns_match.group(1))
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in task_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"my-accepted task column {field} must remain sortable"
    for token in (
        "rowSelection={{selectedRowKeys:selectedKeys,onChange:setSelectedKeys,}}",
        "pageSize:15",
        "pageSizeOptions:[10,15,20,50,100,200]",
    ):
        assert token in NORMALIZED_TASK, f"my-accepted task selection/paging contract missing: {token}"
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], "my-accepted task page must keep the 11 evidenced more-actions"
    assert '{canManageAcceptedTask && <Button onClick={acceptSelectedTask}>接受任务</Button>}' in TASK, "my-accepted task page must expose the evidenced accept-task action without leaking it into department views"

    for token in (
        'title="案件任务"',
        'className="task-detail-flow"',
        'className="task-detail-meta"',
        'className="task-detail-section-title">沟通记录',
        '>关闭</Button>',
    ):
        assert token in TASK, f"my-accepted task detail lost original structure/action: {token}"
    for token in (
        'onClick={() => void markHistoryUnread(item)}',
        '{item.unread ? "已标记未读" : "标记未读"}',
        'api.post(`/tasks/${communication.id}/history/${item.id}/mark-unread`)',
    ):
        assert token in TASK, f"my-accepted task detail mark-unread action is not reachable: {token}"
    assert '@app.post(f"{settings.api_prefix}/tasks/{{task_id}}/history/{{event_id}}/mark-unread")' in MAIN, "my-accepted task mark-unread API is missing"
    detail_meta_match = re.search(r'<div className="task-detail-meta">(.*?)</div>', TASK, re.S)
    assert detail_meta_match, "my-accepted task detail metadata block not found"
    detail_meta_labels = re.findall(r'<b>([^：<]+)：</b>', detail_meta_match.group(1))
    assert detail_meta_labels == [
        "任务标题", "任务编号", "当前负责人", "发布人", "关联案号", "截止日期", "状态", "当前协作人",
    ], f"my-accepted task detail must keep the eight evidenced metadata fields, got {detail_meta_labels}"
    assert detail_stage_labels == ["任务已分派", "任务处理中", "任务完成", "任务已验收"], "my-accepted task detail must reuse the evidenced four-stage flow"

    for token in (
        '? "owned"',
        'selected?.workflow_status || selected?.status',
        'type: "accept" | "restart" | "complete" | "confirm"',
        'api.post(`/tasks/${row.id}/${type}`',
        'type DialogAction = "reject" | "resend"',
        '`/tasks/${dialog.row.id}/${dialog.action}`',
        'api.post(`/tasks/${handoff.id}/handoff`',
    ):
        assert token in TASK, f"my-accepted task frontend special-flow contract missing: {token}"
    for endpoint in ("accept", "reject", "restart", "complete", "handoff"):
        assert f'@app.post(f"{{settings.api_prefix}}/tasks/{{{{task_id}}}}/{endpoint}")' in MAIN, f"my-accepted task API missing: {endpoint}"
    for token in (
        'if body.module == "task":',
        'if record.module not in GENERIC_RECORD_EDITABLE_MODULES:',
        'if record.module not in GENERIC_RECORD_TRANSITION_MODULES:',
    ):
        assert token in MAIN, f"my-accepted task generic-write bypass guard missing: {token}"

    # Original /9001001030/TP/Task/TaskList (my-collaborating tasks) evidence.
    # The original page exposes exactly node-status 2/3 as 进行中/完成.
    assert '("task-my-collaborating", "task-my", "我协作的任务", "", 3)' in MAIN, "my-collaborating task route/menu declaration is missing"
    assert 'const isCollaborating = initialView.endsWith("-collaborating")' in TASK, "my-collaborating route detection is missing"
    assert '? "collaborating"' in TASK, "my-collaborating page must request relation=collaborating"
    collaborating_tabs_match = re.search(r"const collaboratingTabs: StatusTab\[\] = \[(.*?)\n\];", TASK, re.S)
    assert collaborating_tabs_match, "my-collaborating status tabs declaration is missing"
    collaborating_tabs = collaborating_tabs_match.group(1)
    assert collaborating_tabs.count("{ key:") == 2, "original my-collaborating page has exactly two status tabs"
    assert 'label: "进行中"' in collaborating_tabs and 'label: "完成"' in collaborating_tabs, "my-collaborating tabs must match the original 进行中/完成 labels"
    for terminal_status in ("已拒绝", "已停止", "已撤回"):
        assert terminal_status not in collaborating_tabs, f"original my-collaborating node-status tabs do not include {terminal_status}"
    assert 'elif relation == "collaborating":' in MAIN, "task API collaborating relation is missing"
    relation_guard = re.search(r'username = identity\["username"\]\s*if scope != "department":\s*(.*?)\s*items = \[_task_dict', MAIN, re.S)
    assert relation_guard and 'elif relation == "collaborating":' in relation_guard.group(1), "task participant-role narrowing must retain collaborating filtering"
    assert 'scope == "company" and identity.get("role") == "admin"' in relation_guard.group(1), "company-wide initiated tasks must remain organization-wide while accepted tasks honor ownership"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "my-collaborating task page must reuse the 12 evidenced filters"
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], "my-collaborating task page must reuse the selectable 14-column list"
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in task_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"my-collaborating task column {field} must remain sortable"
    for token in ("pageSize:15", "pageSizeOptions:[10,15,20,50,100,200]", "sort_by", "sort_order"):
        source = NORMALIZED_TASK if token.startswith("pageSize") else MAIN
        assert token in source, f"my-collaborating paging/sorting contract missing: {token}"
    for token in (
        'className="task-detail-section-title">沟通记录',
        'onClick={() => void markHistoryUnread(item)}',
        'api.post(`/tasks/${communication.id}/history/${item.id}/mark-unread`)',
        '@app.post(f"{settings.api_prefix}/tasks/{{task_id}}/history/{{event_id}}/mark-unread")',
    ):
        source = MAIN if token.startswith("@app.post") else TASK
        assert token in source, f"my-collaborating detail communication/mark-unread contract missing: {token}"
    for token in (
        'label: "新增律所费用"', 'key: `lawFee:${subtype}`',
        'label: "新增平台费用"', 'key: `platformFee:${subtype}`',
        '["官费", "第三方费用", "代理费", "其他费用"]',
        'label: "新增内部费用"', 'label: "批量修改"',
        'hearing_lawyer: "修改开庭律师"', 'handling_lawyers: "修改经办律师"',
        'assistant: "修改律师助理"', 'case_stage: "修改案件阶段"',
        'api.post("/cases/batch-update"', 'case_nos: selectedCaseNos',
        'expense_scope: expenseScope', 'expense_subtype: feeSubtype',
    ):
        assert token in TASK, f"my-collaborating original secondary action menu missing: {token}"
    assert 'api.post("/tasks/batch-update"' not in TASK, "task-page batch modification must target associated cases, not task lifecycle fields"
    assert 'pagination={hideTaskFooter?false:' in NORMALIZED_TASK, "empty evidenced task tables must hide their TFOOT pagination"
    assert '{!hideTaskFooter&&(' in NORMALIZED_TASK, "empty evidenced task tables must hide their action footer"
    assert '...(["admin", "manager"].includes(profile.role)' in TASK, "case batch modification controls must be limited to roles accepted by the cases API"
    for action_text in (
        "纯协作人不得接收", "纯协作人不得拒绝", "纯协作人不得重新开始", "纯协作人不得完成",
        "纯协作人不得确认", "协作人无权交接", "纯协作人不得批量修改",
    ):
        assert action_text in SMOKE and "expected=(403,)" in SMOKE[SMOKE.index(action_text):SMOKE.index(action_text) + 180], f"pure-collaborator lifecycle denial evidence missing: {action_text}"
    for token in (
        'foradmin_relationin["initiated","collaborating"]',
        '"relation":"collaborating"',
        'collab_first_page["status_counts"]["处理中"]==1',
        'pure_collab_comment=call("POST",f"/tasks/{task[\'id\']}/comments"',
    ):
        assert token in NORMALIZED_SMOKE, f"my-collaborating smoke evidence missing: {token}"

    # Original /9001001040/TP/Task/TaskList (tasks with unread new messages).
    # This page deliberately reuses the common 12-filter/14-column shell while
    # projecting NewestUnReadMessage/sender/time into status/priority/title.
    assert 'const isUnread = initialView === "task-my-unread"' in TASK, "my-unread task route detection is missing"
    assert 'title="任务列表"' in TASK, "my-unread task page must use the original 任务列表 title"
    assert '{!isUnread && <div className="task-status-tabs">' in TASK, "original my-unread page must not render task status tabs"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "my-unread task page must reuse the 12 original filters"
    unread_columns_match = re.search(r"const unreadColumns: any\[\] = \[(.*?)\n  \];\n  const columns", TASK, re.S)
    assert unread_columns_match, "my-unread task columns declaration is missing"
    unread_columns = unread_columns_match.group(1)
    unread_column_fields = re.findall(r'dataIndex:\s*"([^"]+)"', unread_columns)
    assert unread_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], f"my-unread task page must keep checkbox plus 14 common columns, got {unread_column_fields}"
    for token in (
        'row.latest_unread_message || ""',
        'row.latest_unread_sender || ""',
        'row.latest_unread_at ? formatTaskDateTime(row.latest_unread_at) : ""',
        'onClick={() => openCommunication(row)}',
    ):
        assert token in unread_columns, f"my-unread NewestUnReadMessage projection is missing: {token}"
    assert unread_columns.count('render: () => ""') == 6, "the final six common cells on original unread rows must stay blank"
    unread_column_chunks = re.split(r"\n    (?=\{)", unread_columns)
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in unread_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"my-unread common column {field} must retain original sorting"
    assert 'locale={{ emptyText: "没有查询到符合条件的记录 。" }}' in TASK, "my-unread empty text must preserve the original spacing and punctuation"
    for token in (
        'api.get(isUnread?"/tasks/unread-messages":"/tasks"',
        'awaitapi.post(`/tasks/${row.id}/messages/read`)',
        'setCommunication(row)',
        'api.get(`/tasks/${row.id}/history`)',
        'rowSelection={{selectedRowKeys:selectedKeys,onChange:setSelectedKeys,}}',
        'locale={{emptyText:"没有查询到符合条件的记录。"}}',
        'pagination={hideTaskFooter?false:',
        '{!hideTaskFooter&&(',
        'pageSize:15',
        'pageSizeOptions:[10,15,20,50,100,200]',
    ):
        assert token in NORMALIZED_TASK, f"my-unread table/read/empty-state contract missing: {token}"
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], "non-empty my-unread page must retain all 11 original more-actions"

    for token in (
        '@app.get(f"{settings.api_prefix}/tasks/unread-messages")',
        'sort_by: str = Query("", pattern="^(|created_at|deadline|days_remaining|updated_at)$")',
        'sort_order: str = Query("desc", pattern="^(asc|desc)$")',
        'Notification.recipient == identity["username"]',
        'Notification.recipient_deleted.is_(False)',
        'Notification.is_read.is_(False)',
        'Notification.source_type == "task"',
        'Notification.source_key.like("task-message-%")',
        'Notification.source_key.like("task-history-%")',
        '"latest_unread_message": latest_content',
        '"latest_unread_sender":',
        '"latest_unread_at": latest.created_at',
        '"latest_unread_notification_id": latest.id',
        '"unread_count": len(task_notices)',
        'populated.sort(key=lambda item: item[sort_by], reverse=reverse_sort)',
        'items.sort(key=lambda item: (item["latest_unread_at"], item["latest_unread_notification_id"]), reverse=True)',
        '@app.post(f"{settings.api_prefix}/tasks/{{task_id}}/messages/read")',
        'if not _is_task_participant(task, identity):',
        'item.is_read = True',
        'return {"task_id": task.id, "updated": len(items), "is_read": True}',
    ):
        assert token in MAIN, f"my-unread dedicated API/recipient/read contract missing: {token}"
    assert 'Administrator visibility is intentionally not expanded here' in MAIN, "admin must not bypass recipient-specific unread state"
    assert MAIN.count('await _add_task_message_notifications(') >= 11, "task lifecycle paths must create recipient-specific unread messages"
    for token in (
        "window.addEventListener('sunhold:notifications-updated',notificationsUpdated)",
        "window.removeEventListener('sunhold:notifications-updated',notificationsUpdated)",
    ):
        assert token in NOTIFICATION, f"notification badge refresh listener contract missing: {token}"
    for endpoint in (
        'await api.post(`/tasks/${row.id}/messages/read`);',
        'await api.post(`/tasks/${communication.id}/history/${item.id}/mark-unread`);',
    ):
        start = TASK.find(endpoint)
        assert start >= 0 and 'window.dispatchEvent(new Event("sunhold:notifications-updated"));' in TASK[start:start + 220], f"task unread mutation must immediately refresh the bell badge: {endpoint}"
    for token in (
        'assertcall("GET",f"/tasks/unread-messages?{unread_task_query}")["total"]==0',
        'manager_unread["items"][0]["latest_unread_message"]=="任务已分派."',
        'manager_unread["items"][0]["latest_unread_sender"]',
        'call("GET","/tasks/unread-messages?sort_by=owner",expected=(422,))',
        '"sort_by":"deadline","sort_order":"asc"',
        'unread_collab_sorted["items"]',
        'call("POST",f"/tasks/{task[\'id\']}/messages/read")',
        'call("POST",f"/tasks/{task[\'id\']}/messages/read",expected=(403,))',
        'terminal_unread_page["items"][0]["latest_unread_message"]=="任务已确认完成."',
        'overdue_unread_task["items"][0]["latest_unread_message"]=="任务已分派."',
        'auto_task_notices',
        'item["content"]=="任务已自动完成."',
        'unread_collab_first["unread_messages"]==4',
    ):
        assert token in NORMALIZED_SMOKE, f"my-unread smoke evidence missing: {token}"

    for token in (
        'constisPersonalView=initialView.startsWith("task-my");',
        'constcanManageInitiatedTask=isPersonalView&&isCreated;',
        'constcanManageAcceptedTask=(isPersonalView&&isAccepted)||(profile.role==="admin"&&initialView==="task-company-accepted");',
        'if(!isPersonalView)returntasks;',
        'taskMeta.total===0&&(isCollaborating||isUnread||isReminder||initialView==="task-dept-created"||initialView==="task-dept-accepted"||initialView==="task-company-created"||initialView==="task-company-accepted")',
        '{canManageInitiatedTask&&<ButtononClick={openCreateTask}>',
        '{canManageAcceptedTask&&<ButtononClick={acceptSelectedTask}>',
        'scope=isPersonalView?"mine":initialView.startsWith("task-dept")?"department"',
    ):
        assert token in NORMALIZED_TASK, f"department-created task UI/range contract missing: {token}"
    for token in (
        'elif scope == "department":',
        'department_usernames = set(',
        'if relation == "owned":',
        'elif relation == "collaborating":',
        'tasks = [task for task in tasks if task.department == user.department]',
        'if scope != "department":',
    ):
        assert token in MAIN, f"department task backend scope contract missing: {token}"
    for token in (
        'department_peer_task',
        'department_initiated_ids',
        'department_owned_ids',
        'admin_department_initiated_ids',
        'call("GET","/tasks?scope=department&relation=initiated",expected=(403,))',
    ):
        assert token in NORMALIZED_SMOKE, f"department task scope smoke evidence missing: {token}"
    for token in (
        'def _require_task_owner_or_initiator(',
        '_require_task_owner_or_initiator(record, identity, action="修改任务负责人")',
        '_require_task_owner_or_initiator(task, identity, action="批量修改任务")',
    ):
        assert token in MAIN, f"department accepted task ownership bypass guard missing: {token}"
    for token in (
        'peer_manager_name',
        'peer_owned_page',
        '"旁观经理不得代接收"',
        '"旁观经理不得代拒绝"',
        '"旁观经理不得代完成"',
        '"旁观经理不得代交接"',
        '"部门权限不得替换负责人"',
        '"调查入口不得绕过任务负责人权限"',
        'denied_delete["deleted"]==0',
    ):
        assert token in NORMALIZED_SMOKE, f"department accepted anti-bypass smoke evidence missing: {token}"
    assert '{isAccepted&&<ButtononClick={acceptSelectedTask}>' not in NORMALIZED_TASK, "department accepted page must not expose personal accept controls"

    # Department collaborating uses the evidenced two-tab collaborating shell,
    # but its range is authoritative server-side department scope.  It must not
    # be narrowed back to the signed-in person or inherit owner/initiator flow
    # buttons simply because a manager can see another department member's row.
    assert '("task-dept-collaborating", "task-dept", "部门协作的任务", "", 3)' in MAIN, "department-collaborating route/menu declaration is missing"
    for token in (
        'constisPersonalView=initialView.startsWith("task-my");',
        'constisCollaborating=initialView.endsWith("-collaborating");',
        'constcanManageInitiatedTask=isPersonalView&&isCreated;',
        'constcanManageAcceptedTask=(isPersonalView&&isAccepted)||(profile.role==="admin"&&initialView==="task-company-accepted");',
        'consttabs=isCreated?createdTabs:isCollaborating?collaboratingTabs:receivedTabs;',
        'scope=isPersonalView?"mine":initialView.startsWith("task-dept")?"department"',
        'isCollaborating?"collaborating":"owned"',
        'if(!isPersonalView)returntasks;',
        'taskMeta.total===0&&(isCollaborating||isUnread||isReminder||initialView==="task-dept-created"||initialView==="task-dept-accepted"||initialView==="task-company-created"||initialView==="task-company-accepted")',
        '{canManageInitiatedTask&&<ButtononClick={openCreateTask}>',
        '{canManageAcceptedTask&&<ButtononClick={acceptSelectedTask}>',
    ):
        assert token in NORMALIZED_TASK, f"department-collaborating UI/range contract missing: {token}"
    assert collaborating_tabs.count("{ key:") == 2, "department-collaborating must retain exactly two collaborating tabs"
    assert 'label: "进行中"' in collaborating_tabs and 'label: "完成"' in collaborating_tabs, "department-collaborating tab labels drifted"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "department-collaborating must retain the shared 12 task filters"
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], "department-collaborating must retain the shared selectable 14-column table"
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in task_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"department-collaborating column {field} must remain sortable"
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], "department-collaborating non-empty page must retain all 11 shared more-actions"
    for token in (
        'department_usernames.intersection((task.data or {}).get("collaborators", []))',
        'department_collab_task',
        'peer_collab_page["total"]==1',
        '"旁观经理不得代完成部门协作任务"',
        '"部门协作读取权不得替换负责人"',
        'denied_collab_delete["deleted"]==0',
        'unchanged_department_collab_task["owner"]==outsider_name',
        'call("GET","/tasks?scope=department&relation=collaborating",expected=(403,))',
        'department_collaborating_ids',
        'assertoutside_task["id"]notindepartment_collaborating_idsandtask["id"]notindepartment_collaborating_ids',
    ):
        source = MAIN if token.startswith('department_usernames.') else NORMALIZED_SMOKE
        assert token in source, f"department-collaborating backend/anti-bypass evidence missing: {token}"

    # Original /9001003010 is a company-wide initiated-task shell. It keeps
    # administrator lifecycle operations visible on non-empty tabs, including
    # confirmation/restart after a receiver has submitted completion.
    assert '("task-company-created", "task-company", "公司发起的任务", "", 1)' in MAIN, "company-created route/menu declaration is missing"
    for token in (
        'constisPersonalView=initialView.startsWith("task-my");',
        'constisCreated=initialView.endsWith("-created");',
        'constcanManageInitiatedTask=isPersonalView&&isCreated;',
        'constcanManageAcceptedTask=(isPersonalView&&isAccepted)||(profile.role==="admin"&&initialView==="task-company-accepted");',
        'constcanManageCompanyCreatedTask=profile.role==="admin"&&initialView==="task-company-created";',
        'consttabs=isCreated?createdTabs:isCollaborating?collaboratingTabs:receivedTabs;',
        'initialView.startsWith("task-company")?"company":"default"',
        'isCreated?"initiated":',
        'if(!isPersonalView)returntasks;',
        'taskMeta.total===0&&(isCollaborating||isUnread||isReminder||initialView==="task-dept-created"||initialView==="task-dept-accepted"||initialView==="task-company-created"||initialView==="task-company-accepted")',
        '{canManageInitiatedTask&&<ButtononClick={openCreateTask}>',
        '{canManageInitiatedTask&&selected?.status==="已拒绝"&&(',
        '{(canManageInitiatedTask||canManageCompanyCreatedTask)&&["已完成","待确认"].includes(',
        '{canManageCompanyCreatedTask&&(',
        'requireOne((row)=>voidsimpleAction(row,"complete"))',
        'requireOne((row)=>{setHandoff(row);handoffForm.setFieldsValue({recipient:"",comment:""});})',
    ):
        assert token in NORMALIZED_TASK, f"company-created UI/range contract missing: {token}"
    assert created_tab_labels == [
        "进行中", "进行中-已完成", "进行中-拒绝", "进行中-已停止", "进行中-已撤回", "已验收",
    ], "company-created must retain the six evidenced created-task tabs"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "company-created must retain the shared 12 task filters"
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], "company-created must retain the shared selectable 14-column table"
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in task_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"company-created column {field} must remain sortable"
    for token in ("pageSize:15", "pageSizeOptions:[10,15,20,50,100,200]"):
        assert token in NORMALIZED_TASK, f"company-created paging contract missing: {token}"
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], "company-created non-empty page must retain all 11 shared more-actions"
    for token in (
        'elif scope == "company" and identity.get("role") != "admin":',
        'admin_company_initiated_ids',
        'assert{outside_task["id"],department_collab_task["id"],department_peer_task["id"]}.issubset(admin_company_initiated_ids)',
        'promoted_company_ids',
        'assertcall("GET","/auth/me")["role"]=="admin"',
        'assertcall("GET","/auth/me")["role"]=="manager"',
        'call("GET","/tasks?scope=company&relation=initiated",expected=(403,))',
    ):
        source = MAIN if token.startswith('elif scope') else NORMALIZED_SMOKE
        assert token in source, f"company-created company-scope/current-role evidence missing: {token}"

    # The original /9001003020 snapshot was naturally empty. Its route DOM
    # defines only the shared "more actions" menu and no lifecycle buttons;
    # keep that exact boundary while proving the company-owned API separately.
    assert '("task-company-accepted", "task-company", "公司接受的任务", "", 2)' in MAIN, "company-accepted route/menu declaration is missing"
    for token in (
        'constisPersonalView=initialView.startsWith("task-my");',
        'constisAccepted=initialView.endsWith("-accepted");',
        'constcanManageAcceptedTask=(isPersonalView&&isAccepted)||(profile.role==="admin"&&initialView==="task-company-accepted");',
        'constcanManageCompanyCreatedTask=profile.role==="admin"&&initialView==="task-company-created";',
        'consttabs=isCreated?createdTabs:isCollaborating?collaboratingTabs:receivedTabs;',
        'initialView.startsWith("task-company")?"company":"default"',
        'isAccepted?"owned":',
        'if(!isPersonalView)returntasks;',
        'taskMeta.total===0&&(isCollaborating||isUnread||isReminder||initialView==="task-dept-created"||initialView==="task-dept-accepted"||initialView==="task-company-created"||initialView==="task-company-accepted")',
        '{canManageAcceptedTask&&<ButtononClick={acceptSelectedTask}>',
        '{canManageCompanyCreatedTask&&(',
    ):
        assert token in NORMALIZED_TASK, f"company-accepted UI/range contract missing: {token}"
    assert received_tab_labels == ["待处理", "进行中", "完成", "停止"], "company-accepted must retain the four accepted-task tabs"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "company-accepted must retain the shared 12 task filters"
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], "company-accepted must retain the shared selectable 14-column table"
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in task_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"company-accepted column {field} must remain sortable"
    for token in ("pageSize:15", "pageSizeOptions:[10,15,20,50,100,200]"):
        assert token in NORMALIZED_TASK, f"company-accepted paging contract missing: {token}"
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], "company-accepted non-empty page must retain all 11 shared more-actions"
    assert "canManageCompanyAcceptedTask" not in TASK, "company-accepted must not invent lifecycle controls absent from the original route"
    for token in (
        'elif scope == "company" and identity.get("role") != "admin":',
        "admin_company_owned_ids",
        'assert{outside_task["id"],company_owned_lifecycle_task["id"],department_collab_task["id"],department_peer_task["id"]}.issubset(admin_company_owned_ids)',
        "promoted_owned_ids",
        'assertcompany_owned_lifecycle_task["id"]inpromoted_owned_ids',
        'call("GET","/tasks?scope=company&relation=owned",expected=(403,))',
        "admin_rejected",
        "admin_resent",
        "admin_handed",
        "admin_accepted",
        "admin_completed",
        "admin_confirmed",
        "lifecycle_actions",
    ):
        source = MAIN if token.startswith('elif scope') else NORMALIZED_SMOKE
        assert token in source, f"company-accepted company-owned/admin lifecycle evidence missing: {token}"

    # Original /9001003030 is a non-empty company collaborating list: 187
    # active and 11215 completed, 12 filters, 14 columns, 15-row/six-size
    # paging, exactly the shared more-actions menu, and no lifecycle button.
    # Its hidden participant/company fields are blank, so scope semantics are
    # proved by the route plus our guarded API rather than a fabricated id.
    assert '("task-company-collaborating", "task-company", "公司协作的任务", "", 3)' in MAIN, "company-collaborating route/menu declaration is missing"
    for token in (
        'constisPersonalView=initialView.startsWith("task-my");',
        'constisCollaborating=initialView.endsWith("-collaborating");',
        'constcanManageInitiatedTask=isPersonalView&&isCreated;',
        'constcanManageAcceptedTask=(isPersonalView&&isAccepted)||(profile.role==="admin"&&initialView==="task-company-accepted");',
        'constcanManageCompanyCreatedTask=profile.role==="admin"&&initialView==="task-company-created";',
        'consttabs=isCreated?createdTabs:isCollaborating?collaboratingTabs:receivedTabs;',
        'initialView.startsWith("task-company")?"company":"default"',
        'isCollaborating?"collaborating":"owned"',
        'if(!isPersonalView)returntasks;',
        'taskMeta.total===0&&(isCollaborating||isUnread||',
        '{canManageInitiatedTask&&<ButtononClick={openCreateTask}>',
        '{canManageAcceptedTask&&<ButtononClick={acceptSelectedTask}>',
        '{canManageCompanyCreatedTask&&(',
    ):
        assert token in NORMALIZED_TASK, f"company-collaborating UI/range contract missing: {token}"
    assert collaborating_tabs.count("{ key:") == 2, "company-collaborating must retain exactly two collaborating tabs"
    assert 'label: "进行中"' in collaborating_tabs and 'label: "完成"' in collaborating_tabs, "company-collaborating tab labels drifted"
    assert task_query_fields == [
        "priority", "serial_no", "title", "description", "initiator", "case_no",
        "source", "created_range", "owner", "plaintiff", "defendant", "deadline_range",
    ], "company-collaborating must retain the shared 12 task filters"
    assert task_column_fields == [
        "serial_no", "case_no", "plaintiff", "defendant", "case_stage", "status", "priority",
        "title", "created_at", "deadline", "days_remaining", "updated_at", "initiator", "owner",
    ], "company-collaborating must retain the shared selectable 14-column table"
    for field in ("created_at", "deadline", "days_remaining", "updated_at"):
        field_chunk = next((chunk for chunk in task_column_chunks if f'dataIndex: "{field}"' in chunk), "")
        assert field_chunk and "sorter:" in field_chunk, f"company-collaborating column {field} must remain sortable"
    for token in ("pageSize:15", "pageSizeOptions:[10,15,20,50,100,200]"):
        assert token in NORMALIZED_TASK, f"company-collaborating paging contract missing: {token}"
    assert task_more_keys == [
        "lawFee", "platformFee", "internalFee", "batch", "authorization", "lawFirmLetter",
        "identity", "settlement", "caseTasks", "logs", "export",
    ], "company-collaborating non-empty page must retain all 11 shared more-actions"
    for token in (
        'onClick={() => openCommunication(row)}',
        'className="task-detail-section-title">沟通记录',
        'onClick={() => void markHistoryUnread(item)}',
    ):
        assert token in TASK, f"company-collaborating row/detail operation missing: {token}"
    assert "canManageCompanyCollaboratingTask" not in TASK, "company-collaborating must not invent lifecycle controls without original evidence"
    for token in (
        'elif scope == "company" and identity.get("role") != "admin":',
        "company_collab_admin_task",
        'call("GET","/tasks?scope=company&relation=collaborating",expected=(403,))',
        "admin_company_collab_ids",
        'assertcompany_collab_admin_task["id"]inadmin_company_collab_ids',
        "promoted_collab_ids",
        'assertcompany_collab_admin_task["id"]inpromoted_collab_ids',
        "pure_company_comment",
        "pure_company_delete",
        "unchanged_company_collab",
        "admin_collab_accepted",
        "admin_collab_handed",
        "admin_collab_reaccepted",
        "admin_collab_completed",
        "admin_collab_confirmed",
        "admin_collab_actions",
    ):
        source = MAIN if token.startswith('elif scope') else NORMALIZED_SMOKE
        assert token in source, f"company-collaborating company-scope/permission evidence missing: {token}"

    assert 'owner: profile.username || "admin"' in DOCUMENT, "document creation must default to the signed-in account"
    assert '"/documents/official/upload"' in DOCUMENT and '/documents/official/upload' in MAIN, "official receipt upload must atomically create a document record and attachment"
    normalized_agent_document = re.sub(r"\s+", "", AGENT_DOCUMENT)
    for token in (
        "['case','contract','customer','clue','notary','evidence']",
        "constopenRecord=async(row:Job)=>",
        "api.get(`/records/${row.record_id}`)",
        "rememberInvestigationDetailTarget({id:record?.id,serial_no:row.record_no,module})",
        "onNavigate?.(module)",
        "scroll={{x:1500}}",
    ):
        assert token in normalized_agent_document, f"agent document related-record contract missing: {token}"
    print("AGENT_DOCUMENT_RELATION_OK: all six business modules, record-id fallback and read-only investigation navigation")
    assert "['草稿','待审批']" in SEAL, "the pending seal page must keep drafts reachable for submission"
    assert 'BusinessRecord.status.in_({"待审批", "待用印", "已拒绝"})' in MAIN, "seal audit history views must receive approved and rejected applications"
    assert '"approval_comment": body.comment.strip()' in MAIN, "seal approval must persist approver, time and opinion"
    for token in ('/cases/reference-options', 'placeholder="输入关键词选择案由"', 'placeholder="请选择权利类型"', 'disabled={Boolean(createContractId)}', 'label="案源人"'):
        assert token in (MAIN + CASE), f"case create reference/locking contract missing: {token}"
    assert '>登记证物</Button>' in WAREHOUSE and 'rowSelection={{columnWidth:42}}' not in WAREHOUSE, "warehouse must expose evidence registration without a dead selection column"
    assert "sunhold:company-bank-address" not in SYSTEM and '"bank_address"' in MAIN, "company bank address must persist through the backend config"
    assert "api.post('/hr/employees'" in HR and '/hr/employees"' in MAIN, "employee account and HR record creation must use one atomic endpoint"
    assert "const rawCellValue" in FINANCE and 'spec.control === "date"' in FINANCE and 'spec.control === "money"' in FINANCE, "finance route queries must apply typed field filters"
    for field in ("project_role", "office_phone", "im_account", "contact_status", "is_valid"):
        assert field in CUSTOMER, f"new-customer contact tab is missing {field}"
    assert "<Steps" in CONTRACT and "wizardStep" in CONTRACT, "contract creation must keep the four-step workflow"
    for route in ("notary-import-storage", "notary-import-files", "notary-import-invoices", "notary-query-files"):
        assert route in INVESTIGATION, f"missing dedicated notary page for {route}"
    import_match = re.search(r"isImport\s*=\s*\[(.*?)\]\.includes", INVESTIGATION, re.S)
    assert import_match and "notary-import-storage" in import_match.group(1), "notary storage import must use the dedicated upload page"
    for endpoint in ("/investigations/notaries/storage/import", "/investigations/notaries/files/import", "/investigations/notaries/invoices/import"):
        assert endpoint in INVESTIGATION, f"notary page is missing its real import endpoint {endpoint}"
    assert "/investigations/notaries/files" in INVESTIGATION, "notary file query must use the attachment-level API"
    for token in (
        "const openInvestigationDetail=async(row:Row)",
        "const openLinkedCustomer=async(customerName:string)",
        "if(targetRow)setInvestigationDetail(targetRow)",
        "title:'调查编号',dataIndex:'serial_no',width:170,render:(value:string,r:Row)=><Button type=\"link\" onClick={()=>void openInvestigationDetail(r)}>",
        "rememberCustomerDetailTarget({id:customer.id,serial_no:customer.serial_no,title:customer.title})",
        "调查详情：${investigationDetail?.serial_no||''}",
    ):
        assert token in INVESTIGATION, f"investigation identifier/customer link detail entry missing: {token}"
    assert "form.append('certificate_no',importReference.trim())" in INVESTIGATION, "certificate-file import must transmit the explicitly entered certificate number"
    assert "form.append('invoice_no',importReference.trim())" in INVESTIGATION, "invoice-file import must transmit the explicitly entered invoice number"
    assert "certificate_no: str = Form(...)" in MAIN and "invoice_no: str = Form(...)" in MAIN, "notary file APIs must require explicit matching numbers"
    assert ".seal-stats,.seal-original-tabs{display:none!important}" in SEAL_CSS, "legacy seal statistics/tabs must stay hidden in original-layout views"

    report_execution_titles = [
        "一审待执行案件数量", "二审待执行案件数量", "准备材料案件数量", "提交法院案件数量",
        "执行受理案件数量", "执行中止案件数量", "执行结案案件数量", "执行终本案件数量",
        "执行终结案件数量",
    ]
    for title in report_execution_titles:
        assert title in REPORT, f"execution report is missing original chart {title}"
    assert REPORT.count('{ title: "执行中止案件数量", unit: "个/案" }') == 2, "original execution report contains two distinct stop-stage charts"
    for route in ("reports-execution-2", "reports-execution-3"):
        assert f'PAGE_SPECS["{route}"]' in REPORT, f"{route} must reuse the complete ten-chart original report"
    assert 'execution_statuses = ["一审待执行", "二审待执行", "准备材料", "提交法院", "执行受理", "执行中止", "执行结案", "执行终本", "执行终结", "执行中止"]' in MAIN, "all execution report APIs must return the original ten charts"
    assert "report-toolbar" not in REPORT and "report-detail-panel" not in REPORT, "original report pages must not expose invented toolbar or detail table UI"

    finance_match = re.search(r"const originalFinanceRoutes = \[(.*?)\];", FINANCE, re.S)
    assert finance_match, "FinanceCenterPage original route declaration not found"
    finance_routes = re.findall(r'"([^"]+)"', finance_match.group(1))
    configured_finance_leaves = [key for key in leaves if key.startswith("finance-") and key != "finance-receipts-new"]
    missing_finance = sorted(set(configured_finance_leaves) - set(finance_routes))
    assert not missing_finance, f"finance leaves not using original layout: {missing_finance}"
    for token in (
        'queryField("费用类型", "feeType")',
        'const internalMineOperation',
        'setFeeDetail(row)',
        'title="请款单详情"',
        '<h5>{displayedOriginalTitle}</h5>',
    ):
        assert token in FINANCE, f"internal payment list lost original-page contract: {token}"
    assert (
        'isGeneralSettlementRoute?generalSettlementMeta.pageSize:isArchiveSettlementActiveRoute?archiveSettlementMeta.pageSize:isFeeQueryRoute?feeQueryMeta.pageSize:["finance-internal-mine","finance-internal-settle","finance-internal-refused","finance-internal-void","finance-internal-payment","finance-internal-writeoff","finance-internal-query","finance-internal-done",...internalApprovalRoutes,].includes(initialView)?15:isInvoiceMineRoute?invoiceMineMeta.pageSize:isInvoicePendingRoute?invoicePendingMeta.pageSize:isInvoiceCompanyRoute?invoiceCompanyMeta.pageSize:isInvoiceUnissuedRoute?invoiceUnissuedMeta.pageSize:isInternalDetailRoute?internalDetailMeta.pageSize:20'
        in NORMALIZED_FINANCE
    ), "internal payment list must keep 15-row paging"
    assert (
        'pageSizeOptions:["finance-settlement-pending","finance-settlement-audit","finance-archive-fee-pending","finance-archive-fee-payment","finance-archive-fee-paid","finance-archive-fee-refused","finance-internal-mine","finance-internal-settle","finance-internal-refused","finance-internal-void","finance-internal-payment","finance-internal-writeoff","finance-internal-query","finance-internal-done","finance-internal-detail","finance-internal-company","finance-invoice-mine","finance-invoice-pending","finance-invoice-company","finance-invoice-unissued","finance-invoice-company-unissued","finance-fee-query",...internalApprovalRoutes,].includes(initialView)?[10,15,20,50,100,200]:undefined'
        in NORMALIZED_FINANCE
    ), "internal payment list must keep the original page-size options"
    internal_columns_match = re.search(r"const internalOriginalColumns = \[(.*?)\n  \];", FINANCE, re.S)
    assert internal_columns_match, "internal payment columns declaration not found"
    internal_columns = internal_columns_match.group(1)
    for header in ("操作", "请款单号", "状态", "申请日期", "审核日期", "申请金额", "案件编号", "案件阶段", "案件名称", "付款日期", "申请人"):
        assert f'title: "{header}"' in internal_columns, f"internal payment list is missing header {header}"
    assert 'title: ""' not in internal_columns, "internal payment list must not append an invented blank column"

    print(f"MENU_COVERAGE_OK: {len(menus)} nodes, {len(leaves)} leaves, 0 unhandled")
    print("CUSTOMER_NEW_OK: /6001000/CRM/Customer/CreateUpdate compact four-section form, protected customer create, exact related tabs/empty states and username managers")
    print("CUSTOMER_MINE_OK: /6001001/CRM/Customer/CustomerList exact list controls/actions/paging, protected server-side mine scope and original read-only /View customer page")
    print("CUSTOMER_RECYCLE_OK: /6001002/CRM/Customer/CustomerList exact personal recycle scope, empty/footer behavior, restore/public actions, paging and read-only view")
    print("CUSTOMER_DEPT_OK: original department list/empty-footer behavior, read-only view, exact assignment dialog and protected manager reassignment API")
    print("CUSTOMER_DEPT_RECYCLE_OK: /6001004 exact department recycle scope/list/paging/empty behavior, read-only view and protected restore/public actions")
    print("CUSTOMER_COMPANY_OK: /6001005 full-firm active/deleted list, exact filters/totals/paging/empty behavior, read-only view and single-manager assignment")
    print("CUSTOMER_PUBLIC_OK: /6001006 public-only list, exact empty-state hiding, shared-template paging, read-only view and pickup-only action")
    print("CUSTOMER_SHARED_OK: /6001007 recipient-shared list, exact disabled empty manager filter and empty-state hiding, read-only view, no write actions and shared-template paging")
    print("CUSTOMER_RECENT_CONTACT_OK: /6001008 contact-timestamp projection, exact blank disabled manager filter, server-side newest-first paging, empty-state hiding, read-only view and edit-only action")
    print("CUSTOMER_RECENT_UPDATE_OK: /6001009 current-modifier projection with authoritative updated-at ordering, recycled inclusion/public exclusion, protected actor metadata, exact blank disabled manager filter, totals/empty-state hiding, read-only view, edit-only action and complete paging")
    print("CUSTOMER_COMPANY_RECYCLE_OK: /6001010 full-firm recycle scope, editable manager filter, comma-separated managers, exact totals/empty-state hiding, read-only view, protected restore/public actions and complete paging")
    print("CUSTOMER_CONFLICT_OK: /6001011 exact-name first step, exact miss text, eight-field read-only enterprise second step, stale/race-safe requests and no invented result actions")
    print("TASK_SIDEBAR_PARITY_OK: original task menu has only my/department/company groups; internal task-reminders route is hidden from fallback and configured navigation")
    print(f"FINANCE_LAYOUT_OK: {len(finance_routes)} configured original-layout routes")
    print("TASK_MY_CREATED_OK: /9001001010 six tabs, 12 filters, selectable 14-column list, 15-row/six-size paging, 11 more-actions, four-stage detail and protected task APIs")
    print("TASK_MY_ACCEPTED_OK: /9001001020 four tabs, 12 filters, selectable/sortable 14-column list, 15-row/six-size paging, accept + 11 more-actions, four-stage detail and protected owned-task APIs")
    print("TASK_MY_COLLABORATING_OK: /9001001030 two tabs, 12 filters, sortable 14-column list, empty TFOOT behavior, exact fee/case secondary actions, detail communication/mark-unread, pure-collaborator write denial and admin full scope")
    print("TASK_MY_UNREAD_OK: /9001001040 no tabs, 12 filters, checkbox plus 14 common columns with NewestUnReadMessage projection, 15-row/six-size paging, exact empty TFOOT/action behavior, 11 more-actions, recipient-scoped list/read APIs and lifecycle smoke evidence")
    print("TASK_DEPT_CREATED_OK: /9001002010 six tabs, department-initiator scope, 12 filters, selectable/sortable 14-column list, exact zero-result footer behavior, 11 more-actions and no personal create/lifecycle controls")
    print("TASK_DEPT_ACCEPTED_OK: /9001002020 four tabs, officer-department scope, 12 filters, selectable/sortable 14-column list, six-size paging, exact zero-result footer, 11 more-actions, no personal lifecycle controls and anti-owner-takeover guards")
    print("TASK_DEPT_COLLABORATING_OK: /9001002030 participant-department scope, two tabs, 12 filters, selectable/sortable 14-column list, six-size paging, exact empty footer, 11 more-actions, no personal lifecycle controls and anti-bypass guards")
    print("TASK_COMPANY_CREATED_OK: /9001003010 initiator-company scope, six tabs, 12 filters, selectable/sortable 14-column list, six-size paging, exact empty footer, admin complete/handoff, 11 more-actions and current-role company guards")
    print("TASK_COMPANY_ACCEPTED_OK: /9001003020 four zero-count tabs, 12 filters, selectable/sortable 14-column list, six-size paging, exact empty footer, 11 more-actions only, company-owned/current-role guards and admin lifecycle API evidence")
    print("TASK_COMPANY_COLLABORATING_OK: /9001003030 counts 187/11215, two tabs, 12 filters, selectable/sortable 14-column list, six-size paging, exact empty footer, 11 more-actions only, company-scope guards, collaborator anti-bypass and admin lifecycle evidence")
    print("FINANCE_INTERNAL_MINE_OK: original filters, 11 headers, view action and 15-row paging")
    settlement_contract = [
        'api.get("/finance/settlements/pending")',
        '"/finance/settlements/mark-commission-paid"',
        'finance-original-internal-settle',
        'markCommissionPaid',
        'settlementColumnWidths',
        '"official-fee"',
        '"agency-fee"',
        '"other-fee"',
        '"hearing_lawyer"',
        '"handling_lawyers"',
        '"authorization"',
        '"law-firm-letter"',
        '"identity"',
        'generateSettlementDocument',
        'api.post("/cases/batch-update"',
    ]
    missing_settlement = [token for token in settlement_contract if token not in FINANCE]
    assert not missing_settlement, f"internal settlement list lost original-page contract: {missing_settlement}"
    print("FINANCE_INTERNAL_SETTLE_OK: 9 filters, 14 headers, enriched pending API, real mark-paid action and 15-row paging")
    archive_contract = [
        '"finance-internal-archive": "请款单审批"',
        'finance-original-internal-approval',
        'setFeeReviewTargets([row])',
        'openBatchFeeReview',
        'title={<h5>提成审批</h5>}',
        'aria-label="审批意见"',
        '同意',
        '拒绝',
        'paid_investigation',
        'paid_hearing',
        'api.post("/finance/fees/batch-review"',
    ]
    missing_archive = [token for token in archive_contract if token not in FINANCE]
    assert not missing_archive, f"internal archive approval lost original-page contract: {missing_archive}"
    for token in ('/finance/fees/batch-review', '/finance/fees/{{fee_id}}/review', '费用审批驳回'):
        assert token in MAIN, f"internal archive approval API contract missing: {token}"
    print("FINANCE_INTERNAL_ARCHIVE_OK: 9 filters, selectable 10-column approval table, batch review, review dialog and 15-row paging")
    audit_contract = [
        '"finance-internal-audit": "请款单审批"',
        'f("案件阶段", { disabled: initialView === "finance-internal-audit" })',
        'configuredRows.some((row) => row.status === "待审批")',
        '"finance-internal-audit",\n        "finance-internal-fee-audit"',
    ]
    missing_audit = [token for token in audit_contract if token not in FINANCE]
    assert not missing_audit, f"internal commission pending-audit page lost original contract: {missing_audit}"
    print("FINANCE_INTERNAL_AUDIT_OK: original route title, disabled case-stage filter, empty-state footer and shared review flow")
    fee_audit_contract = [
        '"finance-internal-fee-audit": "请款单审批"',
        'title={<h5>提成审批</h5>}',
        'width={580}',
        'placement="right"',
        'mask={false}',
        'closable={{ placement: "end" }}',
        'rootClassName="finance-review-drawer"',
        'tableLayout="fixed"',
    ]
    missing_fee_audit = [token for token in fee_audit_contract if token not in FINANCE]
    assert not missing_fee_audit, f"internal-fee pending-audit page lost original slide-panel contract: {missing_fee_audit}"
    for token in ('dataIndex:"case_no",width:88', 'dataIndex:"paid_hearing",width:47'):
        assert token in NORMALIZED_FINANCE, f"internal-fee review table lost measured column: {token}"
    fee_audit_css_contract = [
        '.finance-review-drawer .ant-drawer-content',
        'textarea[aria-label="审批意见"]',
        'width: 440px',
        'width: 549px !important',
        'gap: 4px !important',
        'width: 58px',
    ]
    missing_fee_audit_css = [token for token in fee_audit_css_contract if token not in FINANCE_CSS]
    assert not missing_fee_audit_css, f"internal-fee review panel lost measured CSS contract: {missing_fee_audit_css}"
    print("FINANCE_INTERNAL_FEE_AUDIT_OK: 580px right review panel, original controls and 549px ten-column detail table")
    refused_contract = [
        '"finance-internal-refused": "请款单列表"',
        'initialView === "finance-internal-refused"\n          ? "已拒绝"',
        '"付款日期",\n            "申请人",\n            ""',
        'title: "请款单作废"',
        'api.post(`/finance/fees/${row.id}/void`',
        'className="finance-internal-list-summary"',
    ]
    missing_refused = [token for token in refused_contract if token not in FINANCE]
    assert not missing_refused, f"internal commission refused list lost original-page contract: {missing_refused}"
    for token in (
        'constinternalListColumnWidths=[50,167,134,134,134,134,134,167,501,167,167,17,]',
        '"finance-internal-refused","finance-internal-void","finance-internal-payment","finance-internal-writeoff","finance-internal-query","finance-internal-done",...internalApprovalRoutes',
    ):
        assert token in NORMALIZED_FINANCE, f"internal commission refused list lost original-page contract: {token}"
    for token in ('/finance/fees/{{fee_id}}/void', '仅已拒绝的内部费用请款单可以作废', 'action="请款单作废"'):
        assert token in MAIN, f"internal commission void API contract missing: {token}"
    refused_css_contract = [
        '.finance-original-internal-list .finance-original-query-grid',
        'grid-template-columns: repeat(3, 240px)',
        '.finance-original-internal-list .finance-original-table-wrap',
        '.finance-original-internal-list .finance-internal-list-summary > td',
    ]
    missing_refused_css = [token for token in refused_css_contract if token not in FINANCE_CSS]
    assert not missing_refused_css, f"internal commission refused list lost measured CSS contract: {missing_refused_css}"
    print("FINANCE_INTERNAL_REFUSED_OK: original 9 filters, 12-column list, amount summary, 15-row paging and real void flow")
    void_contract = [
        '"finance-internal-void": "请款单列表"',
        'initialView === "finance-internal-void"\n            ? "已作废"',
        '["finance-internal-void", "finance-internal-query"].includes(\n        initialView,\n      ) ? (\n      <Button type="link" onClick={() => setFeeDetail(row)}>\n        查看',
        'const isInternalHistoryList = [',
        'className="finance-original-panel finance-internal-payment-detail"',
        '<h5>申请付款</h5>',
        'aria-label="付款流程"',
        '付款信息查看',
        '返回请款单列表',
        'label: "付款信息"',
        '{ title: "支付对象", dataIndex: "payee", width: 110 }',
        'open={Boolean(feeDetail) && !isInternalHistoryList}',
    ]
    missing_void = [token for token in void_contract if token not in FINANCE]
    assert not missing_void, f"internal commission void list/detail lost original-page contract: {missing_void}"
    void_css_contract = [
        '.finance-internal-payment-detail',
        '.finance-payment-flow',
        'grid-template-columns: repeat(4, minmax(130px, 1fr))',
        '.finance-payment-base-info',
        '.finance-payment-info-tabs',
    ]
    missing_void_css = [token for token in void_css_contract if token not in FINANCE_CSS]
    assert not missing_void_css, f"internal commission void detail lost measured CSS contract: {missing_void_css}"
    print("FINANCE_INTERNAL_VOID_OK: original 9 filters, 12-column list, view action, payment/case links and payment-detail page")
    refund_audit_contract = [
        '"finance-internal-refund-audit": "请款单审批"',
        'api.get("/finance/fees/refund-review-candidates")',
        'const isInternalRefundFee = (fee: Fee) =>',
        '? ["请选择", ...paymentStatuses]',
        'source: "refundReviewFees"',
        'initialView === "finance-internal-refund-audit"\n                ? { routeField1: "待审批" }',
        'initialView === "finance-internal-refund-audit"\n          ? paymentStatus(row)',
        'configuredRows.some((row) => row.status === "待审批")',
    ]
    missing_refund_audit = [token for token in refund_audit_contract if token not in FINANCE]
    assert not missing_refund_audit, f"internal commission refund review lost original-page contract: {missing_refund_audit}"
    for token in (
        '/finance/fees/refund-review-candidates',
        '"is_refund": body.fee_type == "内部费用" and amount < 0',
        '内部提成退费审批通过',
        '内部提成退费审批驳回',
    ):
        assert token in MAIN, f"internal commission refund review API contract missing: {token}"
    print("FINANCE_INTERNAL_REFUND_AUDIT_OK: original 9 filters/status options, negative-request isolation, selectable pending rows and real review flow")
    payment_package_contract = [
        '"finance-internal-payment": "待付款列表"',
        'options: ["请选择", "待付款", "已付款"]',
        'content: "请选择提成."',
        'content: "请选择同一收款人的提成进行打包付款."',
        'api.post("/finance/payment-packages/preview"',
        'api.post("/finance/payment-packages"',
        '<h5>付款单打印</h5>',
        '提交并打印',
        '上海申浩律师事务所',
        '提成付款申请单',
        '提示:选择同一收款进行打包付款.',
        '"finance-internal-payment",\n                    "finance-internal-writeoff",\n                    "finance-internal-query",\n                    "finance-internal-done",\n                    ...internalApprovalRoutes',
    ]
    missing_payment_package = [token for token in payment_package_contract if token not in FINANCE]
    assert not missing_payment_package, f"internal payment package page lost original-page contract: {missing_payment_package}"
    for token in (
        '/finance/payment-packages/preview',
        '/finance/payment-packages", status_code=status.HTTP_201_CREATED',
        '仅待付款提成可以打包付款',
        '请选择同一收款人的提成进行打包付款',
        'action="创建付款包"',
        'action="打包付款"',
        '/finance/payment-packages/{{package_id}}',
        '"撤销打包付款"',
        '付款包必须使用打包付款专用入口创建',
        'GENERIC_RECORD_DELETABLE_MODULES = {"report"}',
        '该业务记录不能通过通用入口物理删除，请使用专用撤销、作废或冲正流程',
    ):
        assert token in MAIN, f"internal payment package API contract missing: {token}"
    for token in (
        '.finance-original-internal-payment .finance-original-query-grid',
        '.finance-original-payment-footer',
        '.finance-payment-package-print',
        '.finance-payment-print-signatures',
        '@media print',
    ):
        assert token in FINANCE_CSS, f"internal payment package measured CSS contract missing: {token}"
    print("FINANCE_INTERNAL_PAYMENT_OK: original 9 filters, 13 columns, payment summary, 15-row paging, same-payee packaging and print preview")
    writeoff_contract = [
        '"finance-internal-writeoff": "付款单-核销"',
        'source: "paymentPackages"',
        '"付款包号码",\n            "收款人",\n            "付款总金额",\n            "付款状态",\n            "付款日期",\n            "付款单据号",\n            "备注"',
        'title="付款核销"',
        'label="付款打包号"',
        'label="请确认付款金额"',
        'label="请输入付款日期"',
        'label="请选择付款方式"',
        'label="请输入付款单据号"',
        'label="请输入付款备注"',
        'api.post(\n        `/finance/payment-packages/${paymentPackageWriteoffTarget.id}/writeoff`',
        'message.success("核销成功.")',
        'className="finance-payment-package-summary"',
        'setPaymentPackageDetail(row)',
        'initialView === "finance-internal-done" ? (',
        '>\n        查看\n      </Button>',
    ]
    missing_writeoff = [token for token in writeoff_contract if token not in FINANCE]
    assert not missing_writeoff, f"internal payment writeoff page lost original-page contract: {missing_writeoff}"
    for token in (
        '/finance/payment-packages/{{package_id}}/writeoff',
        '仅待核销付款包可以核销',
        '确认付款金额必须等于付款包金额',
        'action="付款核销"',
        'action="付款包核销"',
        '已核销付款包必须显式冲正后才能撤销',
        'action = "冲正已核销付款包"',
    ):
        assert token in MAIN, f"internal payment package writeoff API contract missing: {token}"
    for token in (
        '.finance-original-payment-packages .finance-original-query-grid',
        '.finance-original-payment-packages .finance-payment-package-summary > td',
        '.finance-payment-package-writeoff-modal .ant-modal-content',
    ):
        assert token in FINANCE_CSS, f"internal payment package writeoff CSS contract missing: {token}"
    print("FINANCE_INTERNAL_WRITEOFF_OK: original 5 filters, 8 columns, amount summary, 15-row paging, dedicated writeoff modal/API and print detail")
    done_contract = [
        '"finance-internal-done": "付款单-查询"',
        'options: ["请选择", "待核销", "已付款"],\n      defaultValue: "请选择"',
        'disabled: initialView === "finance-internal-writeoff"',
        'initialView === "finance-internal-done" ? (',
        '>\n        查看\n      </Button>',
        'className="finance-payment-package-grand-total"',
        'className="finance-payment-package-summary"',
        'setPaymentPackageDetail(row)',
    ]
    missing_done = [token for token in done_contract if token not in FINANCE]
    assert not missing_done, f"internal paid package query page lost original-page contract: {missing_done}"
    assert 'initialView === "finance-internal-done"\n      ? "已付款"' not in FINANCE, "paid package query must default to all package statuses"
    assert 'if (initialView === "finance-internal-done")\n      rows = rows.filter' not in FINANCE, "paid package query must not silently discard pending packages"
    compact_finance_css = re.sub(r"\s+", " ", FINANCE_CSS)
    for token in (
        '.finance-original-payment-packages .finance-payment-package-grand-total > td',
        '.finance-original-payment-packages .finance-payment-package-summary > td',
        '.finance-payment-package-print',
    ):
        assert token in compact_finance_css, f"internal paid package query CSS contract missing: {token}"
    print("FINANCE_INTERNAL_DONE_OK: original all-status default, 5 filters, 8 columns, global/page totals, 15-row paging and two read-only print entries")
    query_contract = [
        '"finance-internal-query": "请款单列表"',
        '"finance-internal-query": {',
        '"案件名称",\n        "付款日期",\n        "申请人",\n        ""',
        '["finance-internal-void", "finance-internal-query"].includes(',
        '"finance-internal-query",\n        ].includes(initialView) && header === "请款单号"',
        '"finance-internal-query",\n        ].includes(initialView) && header === "案件编号"',
        'const isInternalHistoryList = [',
        '<h5>申请付款</h5>',
        '返回请款单列表',
        'className="finance-internal-list-summary"',
    ]
    missing_query = [token for token in query_contract if token not in FINANCE]
    assert not missing_query, f"internal payment query page lost original-page contract: {missing_query}"
    for token in (
        '.finance-original-internal-list .finance-original-query-grid',
        '.finance-original-internal-list .finance-original-table-wrap',
        '.finance-original-internal-list .finance-internal-list-summary > td',
    ):
        assert token in FINANCE_CSS, f"internal payment query CSS contract missing: {token}"
    print("FINANCE_INTERNAL_QUERY_OK: original 9 filters, 12-column list, amount summary, 15-row paging and three real read-only entries")
    internal_detail_contract = [
        '"finance-internal-detail": "内部费用查询"',
        '"finance-internal-company": "内部费用查询"',
        'const isInternalDetailRoute = [',
        'api.get("/finance/internal-fees"',
        'api.get("/finance/internal-fees/export"',
        'control: "multi"',
        'readOnly: initialView === "finance-internal-detail"',
        '"内部费用类型",\n            "金额",\n            "收款人",\n            "支付状态",\n            ""',
        'anchor.download = `内部费用明细-${dayjs().format("YYYY-MM-DD")}.xls`',
        'isInternalDetailRoute && header === "案号"',
        'onNavigate?.("case-company")',
    ]
    missing_internal_detail = [token for token in internal_detail_contract if token not in FINANCE]
    assert not missing_internal_detail, f"internal fee detail page lost original-page contract: {missing_internal_detail}"
    for token in (
        '.finance-original-internal-detail .finance-original-query-grid',
        '.finance-original-internal-detail .finance-original-table-wrap',
        '.finance-original-internal-detail .finance-internal-detail-grand-total > td',
        '.finance-original-internal-detail .finance-internal-detail-summary > td',
        '.finance-internal-tree-picker',
    ):
        assert token in compact_finance_css, f"internal fee detail CSS contract missing: {token}"
    for token in (
        '@app.get(f"{settings.api_prefix}/finance/internal-fees")',
        '@app.get(f"{settings.api_prefix}/finance/internal-fees/export")',
        'scope: str = Query("company", pattern="^(mine|company)$")',
        'media_type="application/vnd.ms-excel"',
    ):
        assert token in MAIN, f"internal fee detail API contract missing: {token}"
    print("FINANCE_INTERNAL_DETAIL_OK: personal/company scopes, 12 filters, 14 columns plus placeholder, totals, 15-row server paging, case links and real Excel export")
    invoice_mine_contract = [
        'const invoiceMineFields = [...invoiceBaseFields, f("案件编号")]',
        '"finance-invoice-mine": {',
        'fields: invoiceMineFields',
        'const isInvoiceMineRoute = initialView === "finance-invoice-mine"',
        'api.get("/finance/invoices"',
        'api.get("/finance/invoices/export"',
        '请选择需要导出的发票.',
        'isInvoiceCompanyRoute ? "公司开票" : "我的开票"',
        'finance-invoice-grand-total',
        'finance-invoice-page-total',
        'setInvoiceDetail(row)',
        '/withdraw`',
        '<h5>{invoiceProcess ? "开票处理" : "开票信息"}</h5>',
        '返回我的开票',
    ]
    missing_invoice_mine = [token for token in invoice_mine_contract if token not in FINANCE]
    assert not missing_invoice_mine, f"my invoice page lost original-page contract: {missing_invoice_mine}"
    for token in (
        '.finance-original-invoice-mine .finance-original-query-grid',
        '.finance-original-invoice-mine .finance-invoice-grand-total > td',
        '.finance-original-invoice-mine .finance-invoice-page-total > td',
        '.finance-original-invoice-mine .finance-invoice-cancelled-row > td:nth-child(n + 3)',
        '.finance-invoice-detail-page',
        '.finance-invoice-detail-table',
    ):
        assert token in compact_finance_css, f"my invoice CSS contract missing: {token}"
    for token in (
        '@app.get(f"{settings.api_prefix}/finance/invoices")',
        '@app.get(f"{settings.api_prefix}/finance/invoices/export")',
        '@app.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/withdraw")',
        'media_type="application/vnd.ms-excel"',
        'action="撤回发票申请"',
    ):
        assert token in MAIN, f"my invoice API contract missing: {token}"
    invoice_mine_config = re.search(r'"finance-invoice-mine": \{(.*?)\n    \},', FINANCE, re.S)
    assert invoice_mine_config and invoice_mine_config.group(1).count('"') >= 22, "my invoice must keep ten named columns plus the original blank placeholder"
    print("FINANCE_INVOICE_MINE_OK: 8 filters, 10 columns plus placeholder, active-only global/page totals, 15-row server paging, view/withdraw, cancellation strike-through and real Excel export")
    invoice_pending_contract = [
        'const isInvoicePendingRoute = initialView === "finance-invoice-pending"',
        'scope: "pending"',
        'applicant: query.routeField7 || ""',
        'invoicePendingOperation',
        '<h5>{invoiceProcess ? "开票处理" : "开票信息"}</h5>',
        'finance-invoice-process-box',
        '请输入发票号码.',
        '请输入驳回原因.',
        '/reject-issue`',
        '返回待处理开票',
    ]
    missing_invoice_pending = [token for token in invoice_pending_contract if token not in FINANCE]
    assert not missing_invoice_pending, f"pending invoice page lost original-page contract: {missing_invoice_pending}"
    for token in (
        '.finance-original-invoice-pending .finance-original-query-grid',
        '.finance-original-invoice-pending .finance-invoice-grand-total > td',
        '.finance-original-invoice-pending .finance-invoice-page-total > td',
        '.finance-invoice-process-form',
        '.finance-invoice-process-actions',
    ):
        assert token in compact_finance_css, f"pending invoice CSS contract missing: {token}"
    for token in (
        'scope: str = Query("company", pattern="^(mine|company|pending)$")',
        '@app.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/reject-issue")',
        'action="开票驳回"',
        '"recipient": body.invoice_holder.strip()',
        '"invoiced_opinion": body.comment.strip()',
    ):
        assert token in MAIN, f"pending invoice API contract missing: {token}"
    print("FINANCE_INVOICE_PENDING_OK: 9 filters, 8 columns plus placeholder, totals, 15-row server paging, real Excel export and full issue/reject page")
    invoice_company_contract = [
        'const isInvoiceCompanyRoute = initialView === "finance-invoice-company"',
        'const invoiceCompanyParams = (',
        'scope: "company"',
        'const loadInvoiceCompany = async (',
        'invoiceCompanyOperation',
        '修改发票号',
        '修改发票日期',
        '请输入新发票号码.',
        '请输入发票申请日期.',
        '请输入发票开票日期.',
        '请输入作废原因.',
        'finance-invoice-cancel-box',
        '返回公司开票',
        'anchor.download = `${isInvoicePendingRoute ? "待处理开票" : isInvoiceCompanyRoute ? "公司开票" : "我的开票"}',
    ]
    missing_invoice_company = [token for token in invoice_company_contract if token not in FINANCE]
    assert not missing_invoice_company, f"company invoice page lost original-page contract: {missing_invoice_company}"
    invoice_company_config = re.search(r'"finance-invoice-company": \{(.*?)\n    \},', FINANCE, re.S)
    assert invoice_company_config and 'export: true' in invoice_company_config.group(1), "company invoice must use the real export flow"
    assert invoice_company_config.group(1).count('"') >= 26, "company invoice must keep eleven named columns plus the original blank placeholder"
    for token in (
        '.finance-original-invoice-company .finance-original-query-grid',
        '.finance-original-invoice-company .finance-invoice-grand-total > td',
        '.finance-original-invoice-company .finance-invoice-page-total > td',
        '.finance-invoice-cancel-box',
    ):
        assert token in compact_finance_css, f"company invoice CSS contract missing: {token}"
    for token in (
        '@app.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/change-number")',
        '@app.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/change-date")',
        'action="修改发票号"',
        'action="修改发票日期"',
        'sheet_name = "待处理开票" if scope == "pending" else "公司开票" if scope == "company" else "我的开票"',
    ):
        assert token in MAIN, f"company invoice API contract missing: {token}"
    print("FINANCE_INVOICE_COMPANY_OK: 9 filters, 11 columns plus placeholder, totals, 15-row server paging, four row actions, full cancel page, number/date mutation APIs and real Excel export")
    invoice_unissued_contract = [
        'const isInvoiceUnissuedRoute = [',
        'const invoiceUnissuedParams = (',
        'const loadInvoiceUnissued = async (',
        'api.get("/finance/case-fees/invoice-status"',
        'source: "unissuedFees"',
        'finance-original-invoice-unissued',
        'finance-invoice-unissued-grand-total',
        'finance-invoice-unissued-page-total',
        'void exportInvoiceUnissued(key === "selected")',
        'onClick: ({ key }) => runSettlementMoreAction(key)',
        'routeField6: "未开票"',
        'routeField12: ["律师代理费"]',
        'invoiceUnissuedColumnWidths',
        'tableLayout={isInvoiceUnissuedRoute ? "fixed" : undefined}',
        '更多操作',
    ]
    missing_invoice_unissued = [token for token in invoice_unissued_contract if token not in FINANCE]
    assert not missing_invoice_unissued, f"unissued invoice page lost original-page contract: {missing_invoice_unissued}"
    unissued_route_config = re.search(
        r'\["finance-invoice-unissued", "finance-invoice-company-unissued"\]\.map\(\s*\(route\) => \[\s*route,\s*\{(.*?)\n\s*\},\s*\],',
        FINANCE,
        re.S,
    )
    assert unissued_route_config and 'source: "unissuedFees"' in unissued_route_config.group(1), "unissued invoice routes must use the dedicated case-fee source"
    for header in ("案号", "客户", "案件阶段", "助理", "开庭律师", "法院案号", "费用类型", "金额", "开票日期", "开票金额", "发票查看", "到账时间", "到账金额", "到账单位", "付款时间", "付款金额", "法院名称", "付款状态"):
        assert f'"{header}"' in unissued_route_config.group(1), f"unissued invoice page is missing header {header}"
    for token in (
        '.finance-original-invoice-unissued .finance-original-query-grid',
        '.finance-original-invoice-unissued .finance-original-query-actions',
        '.finance-invoice-unissued-grand-total',
        '.finance-invoice-unissued-page-total',
        '.finance-original-invoice-unissued .finance-original-table-wrap .ant-table-cell',
    ):
        assert token in compact_finance_css, f"unissued invoice CSS contract missing: {token}"
    for token in (
        '@app.get(f"{settings.api_prefix}/finance/case-fees/invoice-status")',
        '@app.get(f"{settings.api_prefix}/finance/case-fees/invoice-status/export")',
        'case_fee_ids: list[int] = Field(default_factory=list, max_length=100)',
        'if scope == "mine":',
        'fee_conditions.append(BusinessRecord.owner == identity["username"])',
        'BusinessRecord.module == "finance"',
        'BusinessRecord.module == "invoice", BusinessRecord.status == "已开票"',
        '"invoice_record_id": latest_invoice.id if latest_invoice else None',
        'filename = f"{\'公司未开票\' if scope == \'company\' else \'未开票\'}-{date.today()}.xls"',
    ):
        assert token in MAIN, f"unissued invoice API contract missing: {token}"
    print("FINANCE_INVOICE_UNISSUED_OK: distinct mine/company scopes, 15 filters, 18 named columns plus placeholder, four totals, 15-row server paging, case-fee/invoice/receipt/payment joins, real Excel export and ten more-action entries")
    settlement_pending_contract = [
        'const isGeneralSettlementPendingRoute =',
        'initialView === "finance-settlement-pending"',
        'const generalSettlementParams = (',
        '"/finance/general-settlements/pending"',
        'source: "generalSettlements"',
        'generalSettlementOperation',
        'title="查看分配记录"',
        '? "同意结算"',
        ': "申请结算"',
        'title="导出结算清单"',
        '回退结算审核备注:',
        'finance-settlement-detail-table',
        'void exportGeneralSettlement("receipt")',
        'void exportGeneralSettlement("case")',
        'pageSize: 10',
    ]
    missing_settlement_pending = [token for token in settlement_pending_contract if token not in FINANCE]
    assert not missing_settlement_pending, f"general settlement pending page lost original-page contract: {missing_settlement_pending}"
    settlement_pending_config = re.search(r'"finance-settlement-pending": \{(.*?)\n    \},', FINANCE, re.S)
    assert settlement_pending_config and 'source: "generalSettlements"' in settlement_pending_config.group(1), "settlement pending must use its dedicated receipt source"
    for header in ("操作", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额", ""):
        assert f'"{header}"' in settlement_pending_config.group(1), f"settlement pending page is missing header {header or 'placeholder'}"
    for token in (
        '.finance-original-settlement-pending .finance-original-query-grid',
        '.finance-settlement-grand-total',
        '.finance-settlement-context',
        '.finance-settlement-review-note',
        '.finance-settlement-detail-table',
        '.finance-settlement-footer',
    ):
        assert token in compact_finance_css, f"settlement pending CSS contract missing: {token}"
    for token in (
        '@app.get(f"{settings.api_prefix}/finance/general-settlements/pending")',
        '@app.post(f"{settings.api_prefix}/finance/general-settlements/apply"',
        '@app.get(f"{settings.api_prefix}/finance/general-settlements/export")',
        'BusinessRecord.module == "finance_settlement"',
        'action="申请结算"',
        '结算申请必须使用结算管理专用入口创建',
        'media_type="application/vnd.ms-excel"',
    ):
        assert token in MAIN, f"settlement pending API contract missing: {token}"
    print("FINANCE_SETTLEMENT_PENDING_OK: original 10 filters, 14 named columns plus placeholder, totals, inline allocation details, 10-row server paging, dedicated application flow and three real Excel exports")
    settlement_audit_config = re.search(r'"finance-settlement-audit": \{(.*?)\n    \},', FINANCE, re.S)
    assert settlement_audit_config and 'source: "generalSettlements"' in settlement_audit_config.group(1), "settlement audit must use dedicated application rows"
    for header in ("操作", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额", ""):
        assert f'"{header}"' in settlement_audit_config.group(1), f"settlement audit page is missing header {header or 'placeholder'}"
    for token in (
        'const isGeneralSettlementAuditRoute =',
        'initialView === "finance-settlement-audit"',
        '"/finance/general-settlements/applications"',
        '"/finance/general-settlements/applications/review"',
        'finance-settlement-audit-context',
        'generalSettlementReviewTargets',
        'generalSettlementReviewApproved',
        '"同意结算"',
        '"拒绝结算"',
        'okText={generalSettlementReviewApproved ? "同意" : "提交"}',
        'application_ids: selectedIds.join(",")',
    ):
        assert token in FINANCE, f"settlement audit page contract missing: {token}"
    for token in (
        '.finance-original-settlement-audit .finance-original-query-grid',
        '.finance-original-settlement-audit .finance-original-table-wrap',
        '.finance-settlement-audit-context',
        '.finance-settlement-review-field',
    ):
        assert token in compact_finance_css, f"settlement audit CSS contract missing: {token}"
    for token in (
        '@app.get(f"{settings.api_prefix}/finance/general-settlements/applications")',
        '@app.post(f"{settings.api_prefix}/finance/general-settlements/applications/review")',
        'target_status = "待付款" if body.approved else "已拒绝"',
        'action = "同意结算" if body.approved else "拒绝结算"',
        '"reviewer": identity["username"]',
        'application_ids: str = ""',
    ):
        assert token in MAIN, f"settlement audit API contract missing: {token}"
    print("FINANCE_SETTLEMENT_AUDIT_OK: original 13 filters, 14 named columns plus placeholder, submission context, 10-row server paging, single/batch approve/reject and three real Excel exports")
    settlement_payment_config = re.search(r'"finance-settlement-payment": \{(.*?)\n    \},', FINANCE, re.S)
    assert settlement_payment_config and 'source: "generalSettlements"' in settlement_payment_config.group(1), "settlement payment must use dedicated application rows"
    for header in ("操作", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额", ""):
        assert f'"{header}"' in settlement_payment_config.group(1), f"settlement payment page is missing header {header or 'placeholder'}"
    for token in (
        'const isGeneralSettlementPaymentRoute =',
        'initialView === "finance-settlement-payment"',
        '? "待付款"',
        ': "待审批"',
        'generalSettlementPaymentTargets',
        'finance-settlement-payment-context',
        'title="回退结算"',
        'title="标记已支付"',
        '"/finance/general-settlements/applications/payment"',
        '? "标记已支付"',
        ': "回退结算"',
    ):
        assert token in FINANCE, f"settlement payment page contract missing: {token}"
    for token in (
        '.finance-settlement-payment-context',
        '.finance-settlement-payment-context em',
        '.finance-original-settlement-audit .finance-original-query-grid',
        '.finance-settlement-footer',
    ):
        assert token in compact_finance_css, f"settlement payment CSS contract missing: {token}"
    for token in (
        '@app.post(f"{settings.api_prefix}/finance/general-settlements/applications/payment")',
        'target_status = "已付款"',
        'target_status = "已退回"',
        'action = "标记已支付"',
        'action = "回退结算"',
        'detail="请输入审核备注."',
        '"paid_by": identity["username"]',
        '"rollback_by": identity["username"]',
    ):
        assert token in MAIN, f"settlement payment API contract missing: {token}"
    print("FINANCE_SETTLEMENT_PAYMENT_OK: original 13 filters, 14 named columns plus placeholder, audit/submission context, four row actions, 10-row paging, rollback, mark-paid and three real Excel exports")
    settlement_paid_config = re.search(r'"finance-settlement-paid": \{(.*?)\n    \},', FINANCE, re.S)
    assert settlement_paid_config and 'source: "generalSettlements"' in settlement_paid_config.group(1), "settlement paid must use dedicated application rows"
    for header in ("操作", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额", ""):
        assert f'"{header}"' in settlement_paid_config.group(1), f"settlement paid page is missing header {header or 'placeholder'}"
    for token in (
        'const isGeneralSettlementPaidRoute =',
        'initialView === "finance-settlement-paid"',
        '? "已付款"',
        'paid_from: paidRange?.[0]?.format?.("YYYY-MM-DD")',
        'paid_to: paidRange?.[1]?.format?.("YYYY-MM-DD")',
        'if (isFeeQueryRoute || isGeneralSettlementRoute || isInternalDetailRoute',
        'finance-original-settlement-paid',
        '付款日期:',
        'title="回退结算"',
        '"finance-settlement-paid",',
    ):
        assert token in FINANCE, f"settlement paid page contract missing: {token}"
    for token in (
        '.finance-original-settlement-paid .finance-original-query-grid',
        '.finance-original-settlement-paid .finance-original-field:nth-child(14)',
        'grid-column: 4',
        '.finance-original-settlement-paid .finance-settlement-payment-context',
    ):
        assert token in compact_finance_css, f"settlement paid CSS contract missing: {token}"
    for token in (
        'paid_from: date | None = None, paid_to: date | None = None',
        '(paid_from, paid_to, "付款")',
        'date_in_range(data.get("paid_at"), paid_from, paid_to)',
        'record.status not in {"待付款", "已付款"}',
        'record.status == "已付款" and body.action == "paid"',
        'from_status=previous_status',
    ):
        assert token in MAIN, f"settlement paid API contract missing: {token}"
    print("FINANCE_SETTLEMENT_PAID_OK: original 14 filters, 14 named columns plus placeholder, paid context, three row actions, 10-row paging, paid-date filtering, rollback and three real Excel exports")
    settlement_rejected_config = re.search(r'"finance-settlement-refused": \{(.*?)\n    \},', FINANCE, re.S)
    assert settlement_rejected_config and 'source: "generalSettlements"' in settlement_rejected_config.group(1), "settlement rejected must use dedicated application rows"
    for header in ("操作", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额", ""):
        assert f'"{header}"' in settlement_rejected_config.group(1), f"settlement rejected page is missing header {header or 'placeholder'}"
    for token in (
        'const isGeneralSettlementRejectedRoute =',
        'initialView === "finance-settlement-refused"',
        '? "已拒绝,已退回,已驳回"',
        'generalSettlementReapplyTargets',
        'title="重新申请结算"',
        '"重新申请"',
        'finance-settlement-rejected-context',
        'hideRejectedTotal',
        '"/finance/general-settlements/applications/reapply"',
        'message.warning("请输入备注.")',
    ):
        assert token in FINANCE, f"settlement rejected page contract missing: {token}"
    for token in (
        '.finance-settlement-rejected-context',
        '.finance-settlement-rejected-context em',
        'color: red',
        'grid-template-columns: 260px 220px 520px minmax(600px, 1fr)',
    ):
        assert token in compact_finance_css, f"settlement rejected CSS contract missing: {token}"
    for token in (
        'class FinanceSettlementReapplyInput(BaseModel):',
        'application_statuses = {item.strip() for item in application_status.split(",") if item.strip()}',
        'BusinessRecord.status.in_(application_statuses)',
        '@app.post(f"{settings.api_prefix}/finance/general-settlements/applications/reapply")',
        'allowed_from = {"已拒绝", "已驳回", "已退回"}',
        'action="重新申请结算"',
        'to_status="待审批"',
        '"reapplied_by": identity["username"]',
    ):
        assert token in MAIN, f"settlement rejected API contract missing: {token}"
    print("FINANCE_SETTLEMENT_REJECTED_OK: original 13 filters, 14 named columns plus placeholder, red audit context, three row actions, 10-row paging, real reapply and three Excel exports")
    for token in (
        'const isFeeQueryRoute = initialView === "finance-fee-query";',
        'const feeQueryParams = (',
        'const loadFeeQuery = async (',
        'api.get("/finance/fees/query"',
        'source: "feeQuery"',
        'clear: true',
        'export: true',
        'void loadFeeQuery(next, 1, feeQueryMeta.pageSize)',
        'const exportFeeQuery = async (selectedOnly: boolean) =>',
        'api.get("/finance/fees/query/export"',
        '{ key: "selected", label: "导出选中" }',
        '{ key: "all", label: "导出全部" }',
        'void exportFeeQuery(key === "selected")',
        '导出选中',
        '导出全部',
    ):
        assert token in FINANCE, f"finance fee query page contract missing: {token}"
    assert (
        'name="case_no"\n              rules={[{ required: true, message: "请选择或填写关联案号" }]}'
        in FINANCE
    ), "finance fee creation must require a case number before the backend approval guard"
    assert (
        'isFeeQueryRoute?feeQueryMeta.pageSize' in NORMALIZED_FINANCE
    ), "finance fee query must use its dedicated server-side page size"
    assert (
        '"finance-fee-query",...internalApprovalRoutes,].includes(initialView)?[10,15,20,50,100,200]:undefined'
        in NORMALIZED_FINANCE
    ), "finance fee query must expose the original six page-size options"
    for token in (
        'async def _fee_query_rows(',
        '@app.get(f"{settings.api_prefix}/finance/fees/query")',
        'async def query_finance_fees(',
        '@app.get(f"{settings.api_prefix}/finance/fees/query/export")',
        'async def export_finance_fee_query(',
        'media_type="application/vnd.ms-excel"',
    ):
        assert token in MAIN, f"finance fee query API contract missing: {token}"
    print("FINANCE_FEE_QUERY_OK: dedicated server query, real Excel export, six page sizes and selected/all footer exports")
    for token in (
        'const isArchiveSettlementPendingRoute =',
        'initialView === "finance-archive-fee-pending"',
        '? "archiveSettlements"',
        '"/finance/archive-settlements/pending"',
        'archiveSettlementColumnWidths',
        'archiveSettlementPendingOperation',
        'title="新建任务"',
        '"请选择需要导出的归档费."',
        '"导出选中"',
        'archiveSettlementMeta.totals.receipt_amount',
        'archiveSettlementMeta.totals.archive_fee_amount',
        'pageSize: 10',
    ):
        assert token in FINANCE, f"archive settlement pending page contract missing: {token}"
    for header in ("操作", "案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间", ""):
        assert f'"{header}"' in FINANCE, f"archive settlement pending page is missing header {header or 'placeholder'}"
    for token in (
        '.finance-original-archive-pending .finance-original-query-grid',
        'grid-template-columns: 220px 220px 220px 300px',
        '.finance-archive-settlement-grand-total',
        '.finance-archive-settlement-footer',
    ):
        assert token in compact_finance_css, f"archive settlement pending CSS contract missing: {token}"
    for token in (
        'async def _pending_archive_settlement_rows(',
        'BusinessRecord.module == "finance_settlement"',
        'BusinessRecord.status == "已付款"',
        'if not require_archived and linked_case.status == "已归档":',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/pending")',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/export")',
        '"archive_fee_amount": archive_fee if can_view_amount else None',
        'media_type="application/vnd.ms-excel"',
    ):
        assert token in MAIN, f"archive settlement pending API contract missing: {token}"
    print("FINANCE_ARCHIVE_PENDING_OK: original 11 filters, 13 named columns plus placeholder, two global totals, task/case entries, 10-row paging and selected Excel export")
    for token in (
        'const isArchiveSettlementPaymentRoute =',
        'initialView === "finance-archive-fee-payment"',
        '"/finance/archive-settlements/payment"',
        'title="同意支付"',
        'title="拒绝支付"',
        'title={archiveSettlementReviewApproved ? "同意支付" : "拒绝支付"}',
        'finance-archive-payment-context',
        '归档审核人:',
        '归档申请人:',
        '归档审核时间:',
        '归档提交时间:',
        '归档号:',
        '"同意结算"',
        '"拒绝结算"',
    ):
        assert token in FINANCE, f"archive settlement payment page contract missing: {token}"
    for token in (
        '.finance-archive-payment-context',
        'grid-template-columns: 395px 405px 590px minmax(497px, 1fr)',
        '.finance-original-archive-pending .ant-table-expanded-row > td',
    ):
        assert token in compact_finance_css, f"archive settlement payment CSS contract missing: {token}"
    for token in (
        'class ArchiveSettlementPaymentReviewInput(BaseModel):',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/payment")',
        '@app.post(f"{settings.api_prefix}/finance/archive-settlements/payment/review")',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/payment/export")',
        'BusinessRecord.module == "finance_archive_settlement"',
        'if require_archived and linked_case.status != "已归档":',
        'action="归档费同意支付" if body.approved else "归档费拒绝支付"',
        '"source_application_id": data.get("application_id")',
    ):
        assert token in MAIN, f"archive settlement payment API contract missing: {token}"
    print("FINANCE_ARCHIVE_PAYMENT_OK: original 12 filters, 13 named columns plus placeholder, archive audit context, three row/batch actions, 10-row paging, dedicated review flow and selected Excel export")
    for token in (
        'const isArchiveSettlementPaidRoute =',
        'initialView === "finance-archive-fee-paid"',
        '"/finance/archive-settlements/paid"',
        'title="回滚归档费"',
        '回滚归档费结算',
        'isArchiveSettlementRejectedRoute ? "回滚归档费" : "回滚支付"',
        '归档费审核人:',
        '归档费审核时间:',
        '归档费审核备注:',
        '归档费支付状态:',
        '归档费支付日期',
    ):
        assert token in FINANCE, f"archive settlement paid page contract missing: {token}"
    for token in (
        '.finance-original-archive-paid .finance-original-query-grid',
        '.finance-original-archive-paid .finance-original-query-actions',
        '.finance-original-archive-paid .finance-archive-payment-context',
        'min-height: 69px',
    ):
        assert token in compact_finance_css, f"archive settlement paid CSS contract missing: {token}"
    for token in (
        'class ArchiveSettlementRollbackInput(BaseModel):',
        'async def _archive_settlement_decision_rows(',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/paid")',
        '@app.post(f"{settings.api_prefix}/finance/archive-settlements/paid/rollback")',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/paid/export")',
        'record.status = "已回滚"',
        'action="回滚归档费支付"',
        '"archive_payment_rollback_comment": body.comment.strip()',
    ):
        assert token in MAIN, f"archive settlement paid API contract missing: {token}"
    print("FINANCE_ARCHIVE_PAID_OK: original 13 filters, 13 named columns plus placeholder, three-line archive/payment audit context, row/batch rollback, 10-row paging and selected Excel export")
    for token in (
        'const isArchiveSettlementRejectedRoute =',
        'initialView === "finance-archive-fee-refused"',
        '"/finance/archive-settlements/rejected"',
        'archiveSettlementRejectedColumnWidths',
        'title="回滚归档费"',
        'openArchiveSettlementReapply(',
        'title="重新申请"',
        '请选择案件.',
        'finance-archive-rejected-status',
        'reviewed_from:',
        'submitted_from:',
    ):
        assert token in FINANCE, f"archive settlement rejected page contract missing: {token}"
    for token in (
        '.finance-original-archive-rejected .finance-original-query-grid',
        'grid-template-columns: 220px 220px 220px 260px',
        '.finance-original-archive-rejected .finance-original-query-actions',
        'left: 77px',
        'grid-template-columns: 180px 269px 252px minmax(1044px, 1fr)',
        '.finance-archive-rejected-status',
    ):
        assert token in compact_finance_css, f"archive settlement rejected CSS contract missing: {token}"
    for token in (
        'class ArchiveSettlementRejectedActionInput(BaseModel):',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/rejected")',
        '@app.post(f"{settings.api_prefix}/finance/archive-settlements/rejected/rollback")',
        '@app.post(f"{settings.api_prefix}/finance/archive-settlements/rejected/reapply")',
        '@app.get(f"{settings.api_prefix}/finance/archive-settlements/rejected/export")',
        'action="回滚归档费拒绝"',
        'action="重新申请归档费"',
        'from_status="已拒绝", to_status="已回滚"',
        'detail="请先回滚或重新申请关联归档费，再回退结算"',
    ):
        assert token in MAIN, f"archive settlement rejected API contract missing: {token}"
    print("FINANCE_ARCHIVE_REJECTED_OK: original 12 filters, 14 named columns plus selection/placeholder, two totals, three-line rejected context, row rollback, batch reapply, 10-row paging and selected Excel export")
    normalized_styles = re.sub(r"\s+", "", STYLES)
    independent_scroll_contract = [
        'className="app-body"',
        '.app-shell{height:100vh;height:100dvh;overflow:hidden;}',
        '.app-body{height:calc(100vh-50px);height:calc(100dvh-50px);min-height:0;flex:11auto;overflow:hidden;}',
        '.sidebar{height:100%;min-height:0;background:#222d32!important;overflow:hidden;}',
        '.sidebar>.ant-layout-sider-children{height:100%;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;}',
        '.content{height:100%;min-width:0;min-height:0;padding:015px30px;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable;}',
    ]
    missing_independent_scroll = [
        token for token in independent_scroll_contract
        if token not in (APP if token == 'className="app-body"' else normalized_styles)
    ]
    assert not missing_independent_scroll, f"independent shell scrolling contract missing: {missing_independent_scroll}"
    print("INDEPENDENT_SCROLL_OK: fixed viewport shell with separate stable-gutter sidebar and content scroll containers")
    assert all(token in APP for token in ("lazyWithVersionRecovery", "sunhold:chunk-reload:", "reloadAppShell()", "class PageLoadBoundary", "页面资源加载失败")), "lazy page chunks must recover once after a version deployment and render a visible fallback on repeated failure"
    assert 'location = /index.html' in WEB_NGINX and 'Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always' in WEB_NGINX, "the application shell must not be cached across hashed-asset deployments"
    print("VERSIONED_ASSET_RECOVERY_OK: no-store application shell, one-shot lazy chunk reload and visible repeated-failure fallback")
    print("REPORT_LAYOUT_OK: 6 routes, execution views keep 10 original charts")


if __name__ == "__main__":
    main()

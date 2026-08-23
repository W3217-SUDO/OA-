import test from 'node:test'
import assert from 'node:assert/strict'
import { access, readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const workspaceRoot = path.resolve(process.cwd(), '..', '..', '..')
const entries = await readdir(workspaceRoot, { withFileTypes: true })
let oldRepo = ''
for (const entry of entries) {
  if (!entry.isDirectory()) continue
  const candidate = path.join(workspaceRoot, entry.name)
  try { await access(path.join(candidate, '.codegraph')); oldRepo = candidate; break } catch {}
  try { await access(path.join(candidate, 'SH.CRM.WEB', '.codegraph')); oldRepo = path.join(candidate, 'SH.CRM.WEB'); break } catch {}
}
if (!oldRepo) throw new Error('old source repository with .codegraph not found')
const oldController = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerController.cs'), 'utf8')
const oldView = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Views', 'Customer', 'CustomerList.cshtml'), 'utf8')
const oldCustomerView = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Views', 'Customer', 'Customer.cshtml'), 'utf8')
const oldContactsView = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Views', 'CustomerContacts', 'ContactsList.cshtml'), 'utf8')
const oldFileView = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Views', 'CustomerFile', 'CustomerFileUpload.cshtml'), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const localApi = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('legacy customer list normalizes zero page inputs to first page and default size', () => {
  assert.match(oldController, /PageNo == 0[\s\S]*PageNo = 1/)
  assert.match(oldController, /PageSize == 0[\s\S]*PageSize = 15/)
  assert.match(localApi, /page: int = Query\(1, ge=0\)/)
  assert.match(localApi, /page_size: int = Query\(15, ge=0, le=200\)/)
  assert.match(localApi, /page = page or 1/)
  assert.match(localApi, /page_size = page_size or 15/)
})

test('legacy customer page and local page expose all ten scoped lists plus public pool', () => {
  for (const id of ['6001001', '6001002', '6001003', '6001004', '6001005', '6001006', '6001007', '6001008', '6001009', '6001010']) {
    assert.match(oldController, new RegExp(`PageId_${id}`))
  }
  assert.match(oldController, /PageId_6001011/)
  for (const key of ['customer-mine', 'customer-recycle', 'customer-dept', 'customer-dept-recycle', 'customer-company', 'customer-public', 'customer-shared', 'customer-recent-contact', 'customer-recent-update', 'customer-company-recycle']) {
    assert.match(localPage, new RegExp(`"${key}"`))
  }
})

test('customer list keeps legacy six page-size choices and first-page defaults', () => {
  assert.match(oldController, /model\.SearchCondition\.PageSize = 15/)
  assert.match(localPage, /const \[page, setPage\] = useState\(1\)/)
  assert.match(localPage, /const \[pageSize, setPageSize\] = useState\(15\)/)
  for (const size of [10, 15, 20, 50, 100, 200]) assert.match(localPage, new RegExp(`\\b${size}\\b`))
})

test('customer list maps legacy scope filters and server-side permission boundaries', () => {
  assert.match(oldController, /PageId_6001003[\s\S]*DepartmentId/)
  assert.match(oldController, /PageId_6001004[\s\S]*IsActived = false/)
  assert.match(oldController, /PageId_6001005[\s\S]*CompanyId/)
  assert.match(oldController, /PageId_6001010[\s\S]*CompanyId[\s\S]*IsActived = false/)
  assert.match(oldController, /PageId_6001006[\s\S]*IsOpened = true/)
  assert.match(localApi, /scope in \{"department", "department_recycle"\}/)
  assert.match(localApi, /scope in \{"company", "company_recycle"\}/)
  assert.match(localApi, /scope == "public"/)
  assert.match(localApi, /status ==/)
})

test('customer list keeps legacy empty-state, selection guard, pager jump and read-only detail entry points', () => {
  assert.match(oldView, /no-data|none-data|符合条件/)
  assert.match(localPage, /没有查询到符合条件的记录/)
  assert.match(localPage, /const requireSingleSelected = \(\)/)
  assert.match(localPage, /setSelectedRowKeys\(\[\]\)/)
  assert.match(localPage, /const goToCustomerPage = \(target: number\)/)
  assert.match(localPage, /onPressEnter=\{\(\) => goToCustomerPage\(Number\(jumpPage/)
  assert.match(localPage, /const openDetail = async/)
  assert.match(localPage, /setDetailPageOpen\(isReadOnlyCustomerList\)/)
})

test('department, recycle, company and public legacy action matrices remain explicit', () => {
  const actions = localPage.slice(localPage.indexOf('const originalActionItems'), localPage.indexOf('const runOriginalAction'))
  assert.match(actions, /customer-dept"[\s\S]*key: "assign"/)
  assert.match(actions, /customer-company"[\s\S]*key: "assign"/)
  assert.match(actions, /customer-dept-recycle.*customer-company-recycle.*key: "restore"/s)
  assert.match(actions, /customer-public"[\s\S]*key: "claim"/)
})

test('detail view keeps the legacy modal fields and a close/return affordance', () => {
  assert.match(oldCustomerView, /id="customerModal"/)
  assert.match(oldCustomerView, /CustomerBasic\.CustomerName/)
  assert.match(oldCustomerView, /CustomerBasic\.CustomerNo/)
  assert.match(oldCustomerView, /btnCustomerCancle/)
  assert.match(localPage, /customer-view-page/)
  assert.match(localPage, /serial_no/)
  assert.match(localPage, /setDetailPageOpen\(false\)/)
})

test('contact list preserves legacy columns, empty state and create/edit path', () => {
  assert.match(oldContactsView, /tblContactsList/)
  assert.match(oldContactsView, /ContactsList/)
  assert.match(oldContactsView, /btnCustomerContactsCreate/)
  assert.match(localPage, /customer-contact-table/)
  assert.match(localPage, /contacts \|\| \[\]/)
  assert.match(localPage, /\/customers\/\$\{contacts\.id\}\/contacts/)
})

test('customer document upload/download keeps legacy file affordances and scoped attachment routes', () => {
  assert.match(oldFileView, /id="customerFileUploadModal"/)
  assert.match(oldFileView, /id="flCustomerFile"/)
  assert.match(oldFileView, /btnCustomerFileUpload/)
  assert.match(localPage, /const \[attachments, setAttachments\]/)
  assert.match(localPage, /api\.post\("\/attachments"/)
  assert.match(localPage, /\/attachments\/\$\{file\.id\}\/download/)
})

test('recycle, restore and public-pool transitions keep legacy controller actions and local routes', () => {
  assert.match(oldController, /CustomerRestore\(long customerId\)/)
  assert.match(oldController, /CustomerOpen\(long customerId\)/)
  assert.match(oldController, /CustomerClose\(long customerId\)/)
  assert.match(localPage, /const action = async \(r: Customer, name: string\)/)
  assert.match(localPage, /`\/customers\/\$\{r\.id\}\/\$\{name\}`/)
  assert.match(localPage, /if \(\["recycle", "restore"\]\.includes\(key\)\)/)
  assert.match(localPage, /key === "claim"/)
})

test('permission and failure paths remain explicit at both old controller and local API/UI boundaries', () => {
  assert.match(oldController, /\[CheckUserLogin\]/)
  assert.match(oldController, /NoPermission\.html\?/) 
  assert.match(localApi, /HTTPException\(status_code=403/)
  assert.match(localPage, /error\?\.response\?\.data\?\.detail/)
})

test('manager filter lock follows legacy personal/shared/recent page matrix', () => {
  assert.match(oldView, /PageId_6001001|PageId_6001002/)
  assert.match(localPage, /const managerLocked = \[/)
  for (const key of ['customer-mine', 'customer-recycle', 'customer-shared', 'customer-recent-contact', 'customer-recent-update']) {
    assert.match(localPage, new RegExp(`"${key}"`))
  }
  assert.match(localPage, /disabled=\{managerLocked\}/)
})

test('list totals and detail lookup retain explicit DTO projections', () => {
  for (const field of ['TotalPaidCaseOfficeFeeAmount', 'TotalCashedCaseOfficeFeeAmount', 'TotalUnCashedCaseOfficeFeeAmount', 'TotalDeficitCaseOfficeFeeAmount', 'TotalCaseNonOfficeFeeAmount', 'TotalCaseCommissionFeeAmount', 'TotalInvoicedAmount']) {
    assert.match(oldController, new RegExp(field))
  }
  assert.match(localApi, /"summary": \{/)
  assert.match(localApi, /agency_fee_due/)
  assert.match(localApi, /official_fee_unreceived/)
  assert.match(oldController, /ViewCustomer\(string customerNo\)/)
  assert.match(localPage, /api\.get\(/)
  assert.match(localPage, /targetId/)
})

test('pager boundary and selection reset are deterministic', () => {
  assert.match(localPage, /Math\.min\(Math\.max\(1, target\), customerPageCount\)/)
  assert.match(localPage, /setJumpPage\(String\(next\)\)/)
  assert.match(localPage, /setSelectedRowKeys\(\[\]\)/)
  assert.match(localApi, /page_items = candidate_rows\[\(page - 1\) \* page_size : page \* page_size\]/)
})

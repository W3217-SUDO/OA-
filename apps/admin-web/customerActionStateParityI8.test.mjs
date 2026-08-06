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
const oldAssignment = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerAssignmentController.cs'), 'utf8')
const oldShare = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerShareController.cs'), 'utf8')
const oldScript = await readFile(path.join(oldRepo, 'Scripts', 'CRM', 'Customer', 'CRM.Customer.js'), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('legacy range scope IDs and local customer view mapping remain complete', () => {
  for (const pageId of ['PageId_6001001', 'PageId_6001002', 'PageId_6001003', 'PageId_6001004', 'PageId_6001005', 'PageId_6001006', 'PageId_6001007', 'PageId_6001008', 'PageId_6001009', 'PageId_6001010', 'PageId_6001011']) assert.match(oldController, new RegExp(pageId))
  for (const key of ['customer-mine', 'customer-recycle', 'customer-dept', 'customer-dept-recycle', 'customer-company', 'customer-company-recycle', 'customer-public', 'customer-shared', 'customer-recent-contact', 'customer-recent-update']) assert.match(localPage, new RegExp(`"${key}"`))
})

test('legacy delete uses confirmation and local recycle keeps an explicit confirmation modal', () => {
  assert.match(oldScript, /Customer\.Delete[\s\S]*showModalConfirmDialog/s)
  assert.match(oldController, /CustomerDelete\(long customerId\)/)
  assert.match(localPage, /const recycleCustomer = \(row: Customer\)/)
  assert.match(localPage, /Modal\.confirm\(/)
  assert.match(localPage, /确认删除客户/s)
})

test('restore/public transitions map old endpoints to local action dispatch', () => {
  for (const action of ['CustomerRestore', 'CustomerOpen', 'CustomerClose']) assert.match(oldController, new RegExp(`${action}\\(long customerId\\)`))
  for (const route of ['claim', 'release', 'recycle', 'restore']) assert.match(localPage, new RegExp(`/customers/\\$\\{[^}]+\\}/\\$\\{(?:name|key)\\}`))
  assert.match(localPage, /if \(key === "release"\) releaseCustomer\(target\)/)
  assert.match(localPage, /title: `确认将客户“\$\{confirmation\.title\}”释放到公海？`/)
  for (const view of ['customer-mine', 'customer-dept', 'customer-company']) {
    assert.match(localPage, new RegExp(`initialView === "${view}"`))
  }
})

test('public customer actions hide unusable edit from non-admin users', () => {
  assert.match(localPage, /initialView === "customer-public"[\s\S]*profile\.role === "admin"[\s\S]*\{ key: "edit", label: "客户编辑" \}[\s\S]*\{ key: "claim", label: "拾回" \}/)
  assert.match(localPage, /: \[\{ key: "claim", label: "拾回" \}\]/)
})

test('assignment payload and UI modal retain the legacy customer-owner transfer flow', () => {
  assert.match(oldAssignment, /CustomerAssigning\(long customerId, string assigningCustomerOwner\)/)
  assert.match(oldAssignment, /CustomerOwnerChange\(customerIds, assigningCustomerOwner\)/)
  assert.match(localPage, /const assignCustomer = async \(\)/)
  assert.match(localPage, /\/customers\/\$\{assigning\.id\}\/managers/)
  assert.match(localPage, /managers: \[values\.manager\]/)
  assert.match(localPage, /open=\{Boolean\(assigning\)\}/)
})

test('share payload and UI modal retain recipient/comment semantics', () => {
  assert.match(oldShare, /CustomerSharing\(long customerId, List<string> sharedObjects\)/)
  assert.match(oldShare, /CustomerSharing\(customerId, sharedObjects\)/)
  assert.match(localPage, /const share = async \(\)/)
  assert.match(localPage, /\/customers\/\$\{sharing\.id\}\/share/)
  assert.match(localPage, /recipients: v\.recipients/)
  assert.match(localPage, /comment: v\.comment \|\| ""/)
  assert.match(localPage, /open=\{Boolean\(sharing\)\}/)
  assert.match(localPage, /name="recipients"[\s\S]*filterOption=\{matchesDirectoryOption\}/)
})

test('legacy action failures surface server messages and local handlers keep API detail fallback', () => {
  assert.match(oldScript, /showModalMessageBox\(response\.Message\)/)
  assert.match(localPage, /error\?\.response\?\.data\?\.detail \|\| "操作失败"/)
  assert.match(localPage, /error\?\.response\?\.data\?\.detail \|\| "客户分配失败"/)
  assert.match(localPage, /error\?\.response\?\.data\?\.detail \|\| "共享失败"/)
})

test('successful status actions clear stale row selection before refreshing the list', () => {
  const action = localPage.slice(localPage.indexOf('const action = async'), localPage.indexOf('const share = async'))
  assert.match(action, /setSelectedRowKeys\(\[\]\)/)
  assert.match(action, /await load\(\)/)
})

test('successful sharing clears stale row selection before refreshing the list', () => {
  const share = localPage.slice(localPage.indexOf('const share = async'), localPage.indexOf('const submitLevelChange'))
  assert.match(share, /setSelectedRowKeys\(\[\]\)/)
  assert.match(share, /await load\(\)/)
})

test('successful delete confirmation clears selection and refreshes the current range', () => {
  const recycle = localPage.slice(localPage.indexOf('const recycleCustomer'), localPage.indexOf('const originalActionItems'))
  assert.match(recycle, /Modal\.confirm\(/)
  assert.match(recycle, /setSelectedRowKeys\(\[\]\)/)
  assert.match(recycle, /await load\(\)/)
})

test('detail navigation remains scoped and supports explicit return without stale selection', () => {
  assert.match(oldScript, /Customer\.View\(customerId\)/)
  assert.match(localPage, /const openDetail = async \(r: Customer, tab = "contacts"\)/)
  assert.match(localPage, /setDetailPageOpen\(isReadOnlyCustomerList\)/)
  assert.match(localPage, /setDetailPageOpen\(false\)/)
})

test('permission gates remain visible for detail mutations while read-only downloads stay available', () => {
  assert.match(oldController, /\[CheckUserLogin\]/)
  assert.match(oldAssignment, /\[CheckUserLogin\]/)
  assert.match(oldShare, /\[CheckUserLogin\]/)
  assert.match(localPage, /const canManageCurrentCustomer = Boolean\(contacts && \(/)
  assert.match(localPage, /canManageCurrentCustomer && detailTab === "documents"/)
  assert.match(localPage, /downloadDocument\(row\)/)
})

test('selection guard prevents multi-row or empty-row mutations while pagination keeps page context', () => {
  assert.match(localPage, /const requireSingleSelected = \(\)/)
  assert.match(localPage, /selectedRowKeys\.length !== 1/)
  assert.match(localPage, /const goToCustomerPage = \(target: number\)/)
  assert.match(localPage, /setSelectedRowKeys\(\[\]\)/)
  assert.match(localPage, /page_size: pageSize/)
})

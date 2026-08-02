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
const oldContactsView = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Views', 'CustomerContacts', 'ContactsList.cshtml'), 'utf8')
const oldContactsScript = await readFile(path.join(oldRepo, 'Scripts', 'CRM', 'Customer', 'Contacts.js'), 'utf8')
const oldCustomerScript = await readFile(path.join(oldRepo, 'Scripts', 'CRM', 'Customer', 'CRM.Customer.js'), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')

test('legacy scope matrix and local menu scope keys remain explicit', () => {
  for (const pageId of ['PageId_6001001', 'PageId_6001002', 'PageId_6001003', 'PageId_6001004', 'PageId_6001005', 'PageId_6001010', 'PageId_6001006', 'PageId_6001007', 'PageId_6001008', 'PageId_6001009']) assert.match(oldController, new RegExp(pageId))
  for (const key of ['customer-mine', 'customer-recycle', 'customer-dept', 'customer-dept-recycle', 'customer-company', 'customer-company-recycle', 'customer-public', 'customer-shared', 'customer-recent-contact', 'customer-recent-update']) assert.match(localPage, new RegExp(`"${key}"`))
})

test('legacy scope ownership and local manager filter lock stay visible in the UI', () => {
  assert.match(oldController, /PageId_6001001[\s\S]*UserIds[\s\S]*GetUserId/s)
  assert.match(oldController, /PageId_6001003[\s\S]*DepartmentId[\s\S]*GetDepartmentId/s)
  assert.match(oldController, /PageId_6001005[\s\S]*CompanyId[\s\S]*GetCompanyId/s)
  assert.match(localPage, /const managerLocked = \[/)
  assert.match(localPage, /disabled=\{managerLocked\}/)
})

test('range-specific actions keep legacy personal, department/company, recycle and public affordances', () => {
  assert.match(localPage, /initialView === "customer-mine"[\s\S]*key: "share"/)
  assert.match(localPage, /initialView === "customer-dept"[\s\S]*key: "assign"/)
  assert.match(localPage, /initialView === "customer-company"[\s\S]*key: "assign"/)
  assert.match(localPage, /customer-dept-recycle.*customer-company-recycle[\s\S]*key: "restore"/s)
  assert.match(localPage, /initialView === "customer-public"[\s\S]*key: "claim"/)
})

test('read-only customer details hide contact/document mutations unless owner-manager permission is present', () => {
  assert.match(localPage, /const canManageCurrentCustomer = Boolean\(contacts && \(/)
  assert.match(localPage, /canManageCurrentCustomer \? <Space[\s\S]*上传照片/s)
  assert.match(localPage, /canManageCurrentCustomer[\s\S]*openContactEdit\(row\)/)
  assert.match(localPage, /canManageCurrentCustomer && detailTab === "documents"/)
})

test('legacy contact empty/create path and required-name validation remain actionable', () => {
  assert.match(oldContactsView, /btnCustomerContactsCreate/)
  assert.match(oldContactsScript, /Contacts_MobilePhone[\s\S]*isMobile/)
  assert.match(oldContactsScript, /showModalMessageBox\(/)
  assert.match(localPage, /openNewEditor\("contact"\)/)
  assert.match(localPage, /name="name"/)
  assert.match(localPage, /required\s*:/)
})

test('legacy action failures surface response messages and local mutation handlers keep detail fallback', () => {
  assert.match(oldCustomerScript, /showModalMessageBox\(response\.Message\)/)
  assert.match(oldContactsScript, /showModalMessageBox\(response\.Message\)/)
  assert.match(localPage, /message\.error\(error\?\.response\?\.data\?\.detail \|\| "删除失败"\)/)
})

test('document download failure preserves the API detail instead of dropping it', () => {
  assert.match(localPage, /const downloadDocument = async \(file: Attachment\)/)
  assert.match(localPage, /downloadDocument[\s\S]*catch \(error: any\)[\s\S]*error\?\.response\?\.data\?\.detail \|\| "下载失败"/s)
})

test('detail lookup failures stay visible to users and leave the page recoverable', () => {
  assert.match(localPage, /const openDetail = async \(r: Customer, tab = "contacts"\)/)
  assert.match(localPage, /openDetail[\s\S]*catch \(error: any\)[\s\S]*客户详情加载失败/s)
})

test('assignment, share, recycle/restore and claim failures keep server detail fallback', () => {
  for (const fallback of ['客户分配失败', '共享失败', '操作失败']) assert.match(localPage, new RegExp(`error\\?\\.response\\?\\.data\\?\\.detail \\|\\| "${fallback}"`))
  assert.match(localPage, /\/customers\/\$\{assigning\.id\}\/managers/)
  assert.match(localPage, /\/customers\/\$\{sharing\.id\}\/share/)
  assert.match(localPage, /\/customers\/\$\{r\.id\}\/\$\{name\}/)
})

test('document mutation controls are permission-gated while download remains read-only', () => {
  assert.match(localPage, /canManageCurrentCustomer && detailTab === "documents"/)
  assert.match(localPage, /downloadDocument\(row\)/)
  assert.match(localPage, /const deleteDocument = async \(id: number\)/)
})

test('contact photo and contact edit failures preserve server detail feedback', () => {
  assert.match(localPage, /const uploadContactPhoto = async[\s\S]*error\?\.response\?\.data\?\.detail/s)
  assert.match(localPage, /const viewContactPhoto = async[\s\S]*联系人照片加载失败/s)
  assert.match(localPage, /const updateContact = async[\s\S]*error\?\.response\?\.data\?\.detail/s)
})

test('selection guard and explicit scope action dispatch prevent accidental cross-row mutations', () => {
  assert.match(localPage, /const requireSingleSelected = \(\)/)
  assert.match(localPage, /selectedRowKeys\.length !== 1/)
  assert.match(localPage, /if \(!target\) return/)
  assert.match(localPage, /if \(\["release", "recycle", "restore"\]\.includes\(key\)\)/)
})

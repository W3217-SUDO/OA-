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

const oldContacts = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerContactsController .cs'), 'utf8')
const oldFiles = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerFileController.cs'), 'utf8')
const oldCustomer = await readFile(path.join(oldRepo, 'Areas', 'CRM', 'Controllers', 'CustomerController.cs'), 'utf8')
const localPage = await readFile(new URL('./src/CustomerCenterPage.tsx', import.meta.url), 'utf8')
const localApi = await readFile(new URL('../api-server/app/main.py', import.meta.url), 'utf8')

test('contact list and mutation actions keep the legacy endpoint matrix', () => {
  for (const action of ['GetContactsList', 'CreateUpdate', 'ContactsCreateUpdate', 'SetDefatultContacts', 'SetActivedContacts', 'ContactsPhoto']) {
    assert.match(oldContacts, new RegExp(`(?:public|private)[^\\n]*[A-Za-z<> ,]*${action}\\s*\\(`))
  }
  assert.match(localApi, /customers\/\{\{customer_id\}\}\/contacts/)
  assert.match(localApi, /customers\/\{\{customer_id\}\}\/contacts\/\{\{contact_id\}\}\/photo/)
  for (const handler of ['addContact', 'openContactEdit', 'deleteContact', 'uploadContactPhoto']) assert.match(localPage, new RegExp(`const ${handler}`))
})

test('contact defaults and primary/active flags remain explicit', () => {
  for (const field of ['IsActived = true', 'IsContacted = true', 'IsPeopleBASE = true', 'IsReceivedEmail = true']) assert.match(oldContacts, new RegExp(field))
  for (const field of ['is_valid', 'is_primary', 'contact_status']) assert.match(localApi, new RegExp(field))
  assert.match(localPage, /设为主要联系人/)
  assert.match(localPage, /有效联系人/)
})

test('contact failure paths preserve old query/save failures and local HTTP boundaries', () => {
  assert.match(oldContacts, /查询联系人失败\./)
  assert.match(oldContacts, /保存失败！/)
  assert.match(localApi, /status_code=404/)
  assert.match(localApi, /status_code=409/)
  assert.match(localApi, /status_code=422/)
  assert.match(localPage, /error\?\.response\?\.data\?\.detail/)
})

test('contact photo upload/download has a constrained local file contract', () => {
  assert.match(oldContacts, /ContactsPhoto\s*\(/)
  assert.match(localPage, /accept="\.jpg,\.jpeg,\.png,\.gif,\.webp"/)
  assert.match(localApi, /photo\/download/)
  assert.match(localApi, /\.jpg.*\.jpeg.*\.png.*\.gif.*\.webp/s)
  assert.match(localApi, /10 \* 1024 \* 1024/)
})

test('customer file upload keeps no-file/empty/type checks and list/download affordances', () => {
  assert.match(oldFiles, /CustomerFileUploading\s*\(/)
  assert.match(oldFiles, /Request\.Files == null|Request\.Files\.Count == 0/)
  assert.match(oldFiles, /ContentLength == 0/)
  assert.match(oldFiles, /CheckFileType\(/)
  assert.match(localApi, /\/attachments\"/)
  assert.match(localApi, /attachments\/\{\{attachment_id\}\}\/download/)
  assert.match(localApi, /attachments\/\{\{attachment_id\}\}\"/)
  for (const handler of ['uploadDocument', 'downloadDocument', 'deleteDocument']) assert.match(localPage, new RegExp(`const ${handler}`))
})

test('customer documents retain empty-state and read/download/delete UI paths', () => {
  assert.match(localPage, /客户文档/)
  assert.match(localPage, /没有查询到客户文件/)
  assert.match(localPage, /onClick=\{\(\) => downloadDocument\(/)
  assert.match(localPage, /onConfirm=\{\(\) => deleteDocument\(/)
  assert.match(localPage, /上传客户文档|上传客户文件/)
})

test('recycle, restore and public-pool state transitions retain old actions and local guards', () => {
  for (const action of ['CustomerRestore', 'CustomerOpen', 'CustomerClose']) assert.match(oldCustomer, new RegExp(`${action}\\s*\\(`))
  for (const route of ['claim', 'release', 'recycle', 'restore']) assert.match(localApi, new RegExp(`customers/\\{\\{customer_id\\}\\}/${route}`))
  assert.match(localApi, /status == .*公海|公海.*status ==/s)
  assert.match(localPage, /\["release", "recycle", "restore"\]/)
})

test('legacy login gate and local owner/manager checks are both explicit', () => {
  assert.match(oldContacts, /\[CheckUserLogin\]/)
  assert.match(oldFiles, /\[CheckUserLogin\]/)
  assert.match(localApi, /_require_record_owner_or_manager/)
  assert.match(localApi, /HTTPException\(status_code=403/)
  assert.match(localPage, /canManageCurrentCustomer/)
})

test('contact and document mutations emit customer audit/workflow events', () => {
  assert.match(localApi, /_customer_event\(customer, .*联系人/s)
  assert.match(localApi, /action=.*上传客户文档/s)
  assert.match(localApi, /action=.*删除客户联系人/s)
})

test('contact/document counters and stable empty collections stay renderable', () => {
  assert.match(localPage, /contacts\.data\.contacts \|\| \[\]/)
  assert.match(localPage, /attachments/)
  assert.match(localPage, /dataSource=\{attachments\}/)
  assert.match(localPage, /dataSource=\{contacts(?:\?|\.)\.data\.contacts \|\| \[\]\}/)
})

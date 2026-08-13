import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'

const files=[
  'SealCenterPage.tsx',
  'AuditLogPage.tsx',
  'CommunicationLogPage.tsx',
  'MessageCenterPage.tsx',
  'AgentDocumentPage.tsx',
  'IprCenterPage.tsx',
  'HrCenterPage.tsx',
]
const sources=Object.fromEntries(await Promise.all(files.map(async file=>[file,await readFile(new URL(`./src/${file}`,import.meta.url),'utf8')])))

test('fourth batch renders personnel through display-name fields with a stable missing-name label',()=>{
  for(const [file,source] of Object.entries(sources)){
    assert.match(source,/姓名待维护/,`${file} must expose the shared missing-name wording`)
    assert.doesNotMatch(source,/hasChinese|isChinese|\\u4e00/,`${file} must accept English display names`)
  }
  assert.match(sources['SealCenterPage.tsx'],/owner_display_name/)
  assert.match(sources['SealCenterPage.tsx'],/operator_display_name/)
  assert.match(sources['SealCenterPage.tsx'],/uploader_display_name/)
  assert.match(sources['AuditLogPage.tsx'],/operator_display_name/)
  assert.match(sources['CommunicationLogPage.tsx'],/operator_display_name/)
  assert.match(sources['MessageCenterPage.tsx'],/sender_display_name/)
  assert.match(sources['MessageCenterPage.tsx'],/recipient_display_name/)
  assert.match(sources['AgentDocumentPage.tsx'],/confirmed_by_display_name/)
  assert.match(sources['AgentDocumentPage.tsx'],/creator_display_name/)
  assert.match(sources['IprCenterPage.tsx'],/created_by_display_name/)
  assert.match(sources['IprCenterPage.tsx'],/operator_display_name/)
  assert.match(sources['IprCenterPage.tsx'],/uploader_display_name/)
  assert.match(sources['HrCenterPage.tsx'],/person_display_name/)
  assert.match(sources['HrCenterPage.tsx'],/created_by_display_name/)
  assert.match(sources['HrCenterPage.tsx'],/uploader_display_name/)
})

test('message recipient selector keeps username only as the option value',()=>{
  const source=sources['MessageCenterPage.tsx']
  assert.match(source,/value:user\.username,label:`\$\{personDisplayName\(user\.display_name\)\}/)
  assert.doesNotMatch(source,/label:`\$\{user\.display_name\}（\$\{user\.username\}/)
})

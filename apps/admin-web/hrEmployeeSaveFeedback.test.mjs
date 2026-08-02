import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

test('non-employee account keeps credential controls required by the save path', () => {
  assert.ok(source.includes("['username','用户名*','input']"), 'employee form must include username')
  assert.ok(source.includes("['password','密码*','input']"), 'employee form must include password')
  assert.ok(!source.includes("basicFields.filter(([key])=>accountType==='员工账号'||!['username','password'].includes(key)).map"), 'account type must not hide credentials that saveEmployee always requires')
})

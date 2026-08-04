import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

const openResetStart = source.indexOf('const openPasswordReset=')
const openResetEnd = source.indexOf('const savePasswordReset=', openResetStart)
const openResetBlock = source.slice(openResetStart, openResetEnd)
const saveResetStart = source.indexOf('const savePasswordReset=')
const saveResetEnd = source.indexOf('const columns:', saveResetStart)
const saveResetBlock = source.slice(saveResetStart, saveResetEnd)

test('HR employee password action uses reset-password wording', () => {
  assert.ok(source.includes('>重置密码</Button>'), 'row action should say 重置密码')
  assert.ok(source.includes('title={') && source.includes('重置密码：'), 'modal title should say 重置密码')
  assert.ok(!source.includes('>修改密码</Button>'), 'row action must not say 修改密码')
  assert.ok(!source.includes('修改密码：'), 'modal title must not say 修改密码')
})

test('HR employee password action calls the real reset endpoint and keeps forced-change contract', () => {
  assert.ok(source.includes('/system/users/'), 'HR reset flow should look up system users')
  assert.ok(source.includes('/reset-password'), 'HR reset flow should call the reset-password endpoint')
  assert.ok(source.includes('new_password:value.new_password'), 'HR reset flow should post the new password')
  assert.ok(source.includes('密码已重置，该员工下次登录必须修改密码'))
  assert.ok(source.includes('重置后该员工下次登录必须修改密码'))
})

test('HR employee password action blocks current-account self reset before posting', () => {
  assert.ok(source.includes('currentUsername'), 'HR reset flow should track current login username')
  assert.ok(openResetBlock.includes('resettingUsername===currentUsername'), 'open reset should block current account')
  assert.ok(openResetBlock.includes('不能重置当前登录账号密码'))
  assert.ok(saveResetBlock.includes('resettingUsername===currentUsername'), 'save reset should re-check current account')
  assert.ok(saveResetBlock.includes('不能重置当前登录账号密码'))
  assert.ok(
    saveResetBlock.indexOf('resettingUsername===currentUsername') < saveResetBlock.indexOf('/reset-password'),
    'self-reset guard must run before posting to reset-password',
  )
})

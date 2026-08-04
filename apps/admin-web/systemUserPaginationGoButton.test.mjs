import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(
  fileURLToPath(new URL('./src/SystemCenterPage.tsx', import.meta.url)),
  'utf8',
)

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = source.indexOf(endNeedle, start)
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

test('system user pagination keeps the legacy explicit GO jump button', () => {
  const usersBlock = block(
    '} else if (initialView === "system-users")',
    '} else if (initialView === "system-roles")',
  )

  assert.ok(
    usersBlock.includes('showQuickJumper: { goButton: "GO" }'),
    'system user pagination should retain the legacy cPaging GO button instead of Enter-only jump input',
  )
})

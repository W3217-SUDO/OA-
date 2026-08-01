import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const source = await readFile(fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)), 'utf8')

test('exposes the legacy employee selection and guarded delete-selected flow', () => {
  assert.match(source, /rowSelection/)
  assert.match(source, /删除选中/)
  assert.match(source, /batch-deletion-impact/)
  assert.match(source, /\/hr\/employees\/batch/)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

async function loadCustomerStatusLabel() {
  let source
  try {
    source = await readFile(new URL('./src/customerStatusLabel.ts', import.meta.url), 'utf8')
  } catch {
    assert.fail('customer status label normalization is missing')
  }

  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  })
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
}

test('active customer with an unset stage is shown as normal', async () => {
  const { customerStatusLabel } = await loadCustomerStatusLabel()

  assert.equal(customerStatusLabel('', 'customer-mine'), '正常')
})

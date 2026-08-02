import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('./src/CustomerConflictPage.tsx', import.meta.url), 'utf8')

test('editing a no-match conflict query keeps its notice until the next search', () => {
  const changeHandler = source.match(/onChange=\{\(event\) => \{[\s\S]*?\}\}/)?.[0] ?? ''

  assert.match(changeHandler, /setName\(event\.target\.value\);/)
  assert.doesNotMatch(changeHandler, /resetResult\(\)/)
})

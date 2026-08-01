import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/InvestigationCenterPage.tsx', import.meta.url), 'utf8')

test('published investigation list keeps tasks created by the current owner when publisher metadata is absent', () => {
  assert.match(source, /names\.includes\(String\(row\.data\.publisher\|\|row\.owner\|\|''\)\)/)
})

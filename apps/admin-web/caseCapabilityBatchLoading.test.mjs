import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('case list loads row capabilities through one batch request', () => {
  assert.match(source, /api\.get\("\/cases\/action-capabilities"/);
  assert.match(source, /record_ids: uniqueRows\.map\(\(row\) => row\.id\)\.join\(","\)/);
  assert.doesNotMatch(source, /uniqueRows\.map\(async \(row\)[\s\S]{0,300}api\.get\(`\/cases\/\$\{row\.id\}\/action-capabilities`\)/);
});

test('case detail retains its single-record capability check', () => {
  assert.match(source, /api\.get\(`\/cases\/\$\{row\.id\}\/action-capabilities`\)/);
});

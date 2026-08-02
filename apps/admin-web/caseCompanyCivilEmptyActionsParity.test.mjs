import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/CaseCenterPage.tsx', import.meta.url), 'utf8');

test('company civil empty results hide the action toolbar like the legacy list', () => {
  const match = source.match(
    /export const shouldShowCaseListActions = \(rowCount: number\) => ([^;]+);/,
  );
  assert.ok(match, 'CaseCenterPage should define the empty-result action visibility contract');

  const shouldShowCaseListActions = new Function('rowCount', `return (${match[1]});`);
  assert.equal(shouldShowCaseListActions(0), false);
  assert.equal(shouldShowCaseListActions(1), true);
  assert.match(
    source,
    /\{shouldShowCaseListActions\(counselListMode\?counselCases\.length:originalCases\.length\)&&<div className="case-bottom-actions">/,
  );
});

import test from 'node:test';
import assert from 'node:assert/strict';

import { buildCaseCounselSearchPayload } from './src/caseCounselSearchParity.mjs';

test('buildCaseCounselSearchPayload normalizes the counsel search DTO at runtime', () => {
  const formatted = { format: (pattern) => (pattern === 'YYYY-MM-DD' ? '2026-08-03' : 'unexpected') };
  const payload = buildCaseCounselSearchPayload(
    {
      customer: '  Acme  ',
      serial_no: '  C-001 ',
      keyword: '  contract  ',
      counsel_range: [formatted, null],
      counsel_type: '  annual  ',
      status: '  服务中 ',
      handling_lawyer: '  Lawyer A ',
      assistant: '  Assistant B ',
      document_name: '  engagement.pdf ',
      sort_order: 'case_no_desc',
    },
    'department',
    3,
    15,
    { selected_only: true, selected_ids: [7, 8] },
  );

  assert.deepEqual(payload, {
    scope: 'department',
    customer: 'Acme',
    serial_no: 'C-001',
    keyword: 'contract',
    counsel_start: '2026-08-03',
    counsel_end: null,
    counsel_type: 'annual',
    case_status: '服务中',
    handling_lawyer: 'Lawyer A',
    assistant: 'Assistant B',
    document_name: 'engagement.pdf',
    sort_order: 'case_no_desc',
    page: 3,
    page_size: 15,
    selected_only: true,
    selected_ids: [7, 8],
  });
});

test('buildCaseCounselSearchPayload accepts string dates and the case_status alias', () => {
  assert.deepEqual(
    buildCaseCounselSearchPayload(
      { counsel_start: ' 2026-01-01 ', counsel_end: '2026-12-31', case_status: ' 在办 ' },
      'mine',
      1,
      10,
    ),
    {
      scope: 'mine',
      customer: '',
      serial_no: '',
      keyword: '',
      counsel_start: '2026-01-01',
      counsel_end: '2026-12-31',
      counsel_type: '',
      case_status: '在办',
      handling_lawyer: '',
      assistant: '',
      document_name: '',
      sort_order: 'updated_desc',
      page: 1,
      page_size: 10,
    },
  );
});

test('buildCaseCounselSearchPayload uses safe defaults for invalid scope, sort, page, and size', () => {
  const payload = buildCaseCounselSearchPayload(
    { customer: null, counsel_range: [null, undefined], sort_order: 'unknown' },
    'all-users',
    0,
    999,
  );

  assert.equal(payload.scope, 'company');
  assert.equal(payload.sort_order, 'updated_desc');
  assert.equal(payload.page, 1);
  assert.equal(payload.page_size, 200);
  assert.equal(payload.customer, '');
  assert.equal(payload.counsel_start, null);
  assert.equal(payload.counsel_end, null);
});

test('buildCaseCounselSearchPayload preserves the local selected export controls without overriding DTO fields', () => {
  const payload = buildCaseCounselSearchPayload(
    { page: '9', page_size: '99', sort_order: 'case_no_asc' },
    'company',
    2,
    15,
    { selected_only: false, selected_ids: [], page: 4, page_size: 20 },
  );

  assert.equal(payload.page, 2);
  assert.equal(payload.page_size, 15);
  assert.equal(payload.sort_order, 'case_no_asc');
  assert.equal(payload.selected_only, false);
  assert.deepEqual(payload.selected_ids, []);
});

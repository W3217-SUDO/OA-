const ALLOWED_SCOPES = new Set(['mine', 'department', 'company']);
const ALLOWED_SORTS = new Set(['updated_desc', 'case_no_asc', 'case_no_desc']);
const CORE_KEYS = new Set([
  'scope',
  'customer',
  'serial_no',
  'keyword',
  'counsel_start',
  'counsel_end',
  'counsel_type',
  'case_status',
  'handling_lawyer',
  'assistant',
  'document_name',
  'sort_order',
  'page',
  'page_size',
]);

const normalizeText = (value) => String(value ?? '').trim();

const normalizeDate = (value) => {
  if (value == null || value === '') return null;
  if (typeof value === 'object' && typeof value.format === 'function') {
    return normalizeText(value.format('YYYY-MM-DD')) || null;
  }
  return normalizeText(value) || null;
};

const normalizeInteger = (value, fallback, minimum, maximum) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  const integer = Math.trunc(numeric);
  return Math.min(maximum, Math.max(minimum, integer));
};

export const buildCaseCounselSearchPayload = (
  values = {},
  scope = 'company',
  page = 1,
  pageSize = 10,
  extra = {},
) => {
  const input = values && typeof values === 'object' ? values : {};
  const range = Array.isArray(input.counsel_range) ? input.counsel_range : null;
  const extras = extra && typeof extra === 'object'
    ? Object.fromEntries(Object.entries(extra).filter(([key]) => !CORE_KEYS.has(key)))
    : {};

  return {
    scope: ALLOWED_SCOPES.has(scope) ? scope : 'company',
    customer: normalizeText(input.customer),
    serial_no: normalizeText(input.serial_no),
    keyword: normalizeText(input.keyword),
    counsel_start: normalizeDate(range ? range[0] : input.counsel_start),
    counsel_end: normalizeDate(range ? range[1] : input.counsel_end),
    counsel_type: normalizeText(input.counsel_type),
    case_status: normalizeText(input.status ?? input.case_status),
    handling_lawyer: normalizeText(input.handling_lawyer),
    assistant: normalizeText(input.assistant),
    document_name: normalizeText(input.document_name),
    sort_order: ALLOWED_SORTS.has(input.sort_order) ? input.sort_order : 'updated_desc',
    page: normalizeInteger(page, 1, 1, 1000000),
    page_size: normalizeInteger(pageSize, 10, 1, 200),
    ...extras,
  };
};

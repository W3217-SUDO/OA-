const ALLOWED_SCOPES = new Set(["mine", "department", "company"]);
const ALLOWED_SORTS = new Set(["updated_desc", "case_no_asc", "case_no_desc"]);
const LOGIC_ALIASES = new Map([
  ["and", "and"],
  ["intersection", "and"],
  ["交集", "and"],
  ["or", "or"],
  ["union", "or"],
  ["并集", "or"],
]);

const normalizeText = (value) => String(value ?? "").trim();

const normalizeDate = (value) => {
  if (value == null || value === "") return null;
  if (typeof value === "object" && typeof value.format === "function") {
    return normalizeText(value.format("YYYY-MM-DD")) || null;
  }
  return normalizeText(value) || null;
};

const normalizeRangeDate = (range, index, fallback) => normalizeDate(Array.isArray(range) ? range[index] : fallback);

const normalizeInteger = (value, fallback, minimum, maximum) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.min(maximum, Math.max(minimum, Math.trunc(numeric)));
};

const normalizeList = (value) => (Array.isArray(value)
  ? [...new Set(value.map(normalizeText).filter(Boolean))]
  : []);

const normalizeBoolean = (value) => value === true || value === "true" || value === 1;

const normalizeLogic = (value) => LOGIC_ALIASES.get(normalizeText(value).toLowerCase()) || "and";

export const normalizePhaseCounts = (value) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).flatMap(([key, count]) => {
      const normalizedKey = normalizeText(key);
      const numericCount = Number(count);
      return normalizedKey && Number.isFinite(numericCount) && numericCount >= 0
        ? [[normalizedKey, Math.trunc(numericCount)]]
        : [];
    }),
  );
};

export const LEGACY_CASE_PHASE_GROUPS = ["一审阶段", "二审阶段", "再审阶段", "执行阶段", "归档阶段"];

const LEGACY_PHASE_CHILDREN = {
  "一审阶段": ["一审立案受理", "一审补充证据", "一审准备开庭", "一审再次开庭", "一审庭后待判", "一审等待上诉", "一审上诉准备", "一审和解中", "一审和解结案", "一审判决结案", "一审待客户回款"],
  "二审阶段": ["二审立案受理", "二审补充证据", "二审准备开庭", "二审再次开庭", "二审庭后待判", "二审等待上诉", "二审上诉准备", "二审和解中", "二审和解结案", "二审判决结案", "二审待客户回款"],
  "再审阶段": ["再审立案受理", "再审补充证据", "再审准备开庭", "再审再次开庭", "再审庭后待判", "再审等待上诉", "再审上诉准备", "再审和解中", "再审和解结案", "再审判决结案", "再审待客户回款"],
  "执行阶段": ["执行立案", "执行准备", "执行中", "执行和解", "执行终结本次", "执行终结", "执行待客户回款"],
  "归档阶段": ["归档中", "归档审核", "已归档", "亏损归档", "亏损归档审核", "亏损归档拒绝"],
};

const LEGACY_PHASE_DISPLAY_ALIASES = new Map([
  ["一审", "一审立案受理"],
  ["二审", "二审立案受理"],
  ["再审", "再审立案受理"],
]);

const legacyCasePhaseGroupFor = (value) => {
  const name = normalizeText(value);
  if (name.includes("一审")) return "一审阶段";
  if (name.includes("二审")) return "二审阶段";
  if (name.includes("再审")) return "再审阶段";
  if (name.includes("执行")) return "执行阶段";
  if (name.includes("归档") || ["亏损内审", "亏损审核", "亏损归档", "已归档"].includes(name)) return "归档阶段";
  return "";
};

export const buildLegacyCasePhaseTree = (items = [], catalog = [], phaseCounts = {}) => {
  const counts = normalizePhaseCounts(phaseCounts);
  const catalogOptions = Array.isArray(catalog) ? catalog : [];
  const groupNames = new Set(LEGACY_CASE_PHASE_GROUPS);

  return items.map((item) => {
    if (!groupNames.has(item.label)) return { ...item, children: [] };

    const candidates = [
      ...(LEGACY_PHASE_CHILDREN[item.label] || []).map((phase, index) => ({
        label: phase,
        value: phase,
        sortOrder: index,
      })),
      ...catalogOptions.map((option) => ({
        label: LEGACY_PHASE_DISPLAY_ALIASES.get(normalizeText(option.name || option.canonical_name)) || normalizeText(option.name || option.canonical_name),
        value: normalizeText(option.canonical_name || option.name),
        sortOrder: 1000 + Number(option.sort_order || 0),
      })),
      ...Object.keys(counts).map((phase, index) => ({ label: phase, value: phase, sortOrder: 100000 + index })),
    ];
    const children = candidates
      .filter((candidate) => candidate.value && candidate.value !== item.value && legacyCasePhaseGroupFor(candidate.value) === item.label)
      .sort((left, right) => left.sortOrder - right.sortOrder)
      .map((candidate) => ({
        label: candidate.label,
        value: candidate.value,
        count: Number(counts[candidate.value] || counts[candidate.label] || 0),
      }))
      .filter((child, index, all) => all.findIndex((candidate) => candidate.label === child.label) === index);
    const directCount = Number(counts[item.value] ?? item.count ?? 0);
    return {
      ...item,
      count: directCount + children.reduce((total, child) => total + child.count, 0),
      children,
    };
  });
};

export const parseOrdinarySearchResult = (data = {}, fallbackPage = 1, fallbackPageSize = 15) => {
  const input = data && typeof data === "object" ? data : {};
  const numericTotal = Number(input.total);
  return {
    items: Array.isArray(input.items) ? input.items : [],
    total: Number.isFinite(numericTotal) && numericTotal >= 0 ? Math.trunc(numericTotal) : 0,
    page: normalizeInteger(input.page, fallbackPage, 1, 1000000),
    pageSize: normalizeInteger(input.page_size, fallbackPageSize, 1, 200),
    phaseCounts: normalizePhaseCounts(input.phase_counts),
  };
};

export const createLatestRequestGuard = () => {
  let latestRequestId = 0;
  return {
    begin: () => {
      latestRequestId += 1;
      return latestRequestId;
    },
    isLatest: (requestId) => requestId === latestRequestId,
  };
};

export const buildCaseOrdinarySearchPayload = (
  values = {},
  scope = "company",
  caseTypes = [],
  page = 1,
  pageSize = 15,
) => {
  const input = values && typeof values === "object" ? values : {};
  const counselRange = Array.isArray(input.counsel_range) ? input.counsel_range : null;
  const sourceRange = Array.isArray(input.source_range) ? input.source_range : null;
  const hearingRange = Array.isArray(input.hearing_range) ? input.hearing_range : null;

  return {
    scope: ALLOWED_SCOPES.has(scope) ? scope : "company",
    case_types: normalizeList(caseTypes),
    customer_id: normalizeInteger(input.customer_id, 0, 0, 2147483647) || null,
    customer_no: normalizeText(input.customer_no),
    customer: normalizeText(input.customer),
    serial_no: normalizeText(input.serial_no),
    keyword: normalizeText(input.keyword),
    counsel_start: normalizeDate(counselRange ? counselRange[0] : input.counsel_start),
    counsel_end: normalizeDate(counselRange ? counselRange[1] : input.counsel_end),
    counsel_type: normalizeText(input.counsel_type),
    case_status: normalizeText(input.status ?? input.case_status),
    handling_lawyer: normalizeText(input.handling_lawyer),
    assistant: normalizeText(input.assistant),
    document_name: normalizeText(input.document_name),
    plaintiff: normalizeText(input.plaintiff),
    prosecutor: normalizeText(input.prosecutor),
    defendant: normalizeText(input.defendant),
    evidence_org: normalizeText(input.evidence_org),
    notary_no: normalizeText(input.notary_no),
    hearing_lawyer: normalizeText(input.hearing_lawyer),
    investigator: normalizeText(input.investigator),
    court: normalizeText(input.court),
    source_from: normalizeRangeDate(sourceRange, 0, input.source_from),
    source_to: normalizeRangeDate(sourceRange, 1, input.source_to),
    channel: normalizeText(input.channel),
    warehouse: normalizeText(input.warehouse),
    hearing_from: normalizeRangeDate(hearingRange, 0, input.hearing_from),
    hearing_to: normalizeRangeDate(hearingRange, 1, input.hearing_to),
    area: normalizeText(input.area),
    location: normalizeText(input.location),
    log_content: normalizeText(input.log_content),
    sort_order: ALLOWED_SORTS.has(input.sort_order) ? input.sort_order : "updated_desc",
    page: normalizeInteger(page, 1, 1, 1000000),
    page_size: normalizeInteger(pageSize, 15, 1, 200),
    advanced_logic: normalizeLogic(input.advanced_logic),
    assisted_response_user: normalizeText(input.assisted_response_user),
    assisted_response_user_not: normalizeBoolean(input.assisted_response_user_not),
    assisted_request_date_from: normalizeDate(input.assisted_request_date_from),
    assisted_request_date_to: normalizeDate(input.assisted_request_date_to),
    assisted_request_date_not: normalizeBoolean(input.assisted_request_date_not),
    assisted_response_date_from: normalizeDate(input.assisted_response_date_from),
    assisted_response_date_to: normalizeDate(input.assisted_response_date_to),
    assisted_response_date_not: normalizeBoolean(input.assisted_response_date_not),
    finance_inform_date_from: normalizeDate(input.finance_inform_date_from),
    finance_inform_date_to: normalizeDate(input.finance_inform_date_to),
    finance_inform_date_not: normalizeBoolean(input.finance_inform_date_not),
    finance_gained_date_from: normalizeDate(input.finance_gained_date_from),
    finance_gained_date_to: normalizeDate(input.finance_gained_date_to),
    finance_gained_date_not: normalizeBoolean(input.finance_gained_date_not),
    finance_response_user: normalizeText(input.finance_response_user),
    finance_response_user_not: normalizeBoolean(input.finance_response_user_not),
    finance_bill_no: normalizeText(input.finance_bill_no),
    finance_bill_no_not: normalizeBoolean(input.finance_bill_no_not),
    finance_bill_statuses: normalizeList(input.finance_bill_statuses),
    finance_bill_status_not: normalizeBoolean(input.finance_bill_status_not),
    finance_bill_date_from: normalizeDate(input.finance_bill_date_from),
    finance_bill_date_to: normalizeDate(input.finance_bill_date_to),
    finance_bill_date_not: normalizeBoolean(input.finance_bill_date_not),
    finance_fee_type_ids: normalizeList(input.finance_fee_type_ids),
    finance_fee_type_not: normalizeBoolean(input.finance_fee_type_not),
    file_uploading_user: normalizeText(input.file_uploading_user),
    file_uploading_user_not: normalizeBoolean(input.file_uploading_user_not),
    file_uploading_time_from: normalizeDate(input.file_uploading_time_from),
    file_uploading_time_to: normalizeDate(input.file_uploading_time_to),
    file_uploading_time_not: normalizeBoolean(input.file_uploading_time_not),
    file_type_ids: normalizeList(input.file_type_ids),
    file_type_not: normalizeBoolean(input.file_type_not),
  };
};

export const ordinaryCaseTypesForView = (view = "") => {
  const route = String(view || "");
  if (route.includes("civil")) return ["民事争议", "民事案件"];
  if (route.includes("criminal")) return ["刑事案件"];
  if (route.includes("administrative")) return ["行政案件及国家赔偿"];
  if (route.includes("arbitration")) return ["仲裁"];
  return [];
};

export const ordinaryCustomerIdForView = (view = "") => {
  const match = String(view || "").match(/-customer-(\d+)$/);
  const customerId = Number(match?.[1] || 0);
  return Number.isSafeInteger(customerId) && customerId > 0 ? customerId : 0;
};

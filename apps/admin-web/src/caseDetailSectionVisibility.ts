const EMPTY_DETAIL_VALUES = new Set(["", "-", "—", "null", "none", "undefined"]);

const FIRST_COURT_FIELDS = [
  "first_court_name",
  "first_instance_court",
  "court",
  "first_court_courtroom",
  "courtroom",
  "first_court_case_no",
  "first_instance_case_no",
  "court_case_no",
  "first_court_filing_date",
  "filing_date",
  "first_court_hearing_date",
  "hearing_date",
  "first_court_judgment_date",
  "judgment_date",
];

const SECOND_COURT_FIELDS = [
  "second_court_name",
  "second_instance_court",
  "second_court_courtroom",
  "second_court_case_no",
  "second_instance_case_no",
  "second_court_filing_date",
  "second_court_hearing_date",
];

const EXECUTION_COURT_FIELDS = [
  "execution_court_name",
  "execution_court_courtroom",
  "execution_court_case_no",
  "execution_court_filing_date",
  "execution_court_hearing_date",
  "effective_date",
];

const ARCHIVE_FIELDS = [
  "archive_type",
  "archive_submitter",
  "archive_submitter_display_name",
  "archive_submitted_at",
  "archive_submit_comment",
  "archive_internal_reviewer",
  "archive_internal_reviewer_display_name",
  "archive_internal_reviewed_at",
  "archive_internal_review_comment",
  "archive_reviewer",
  "archive_reviewer_display_name",
  "archive_reviewed_at",
  "archived_at",
  "archive_review_comment",
  "archive_reject_reason",
  "archive_no",
];

const INACTIVE_ARCHIVE_STATUSES = new Set(["未提交", "not_submitted", "not-submitted", "draft"]);

type CaseDetailData = Record<string, unknown>;

function hasMeaningfulCaseDetailValue(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (Array.isArray(value)) return value.some(hasMeaningfulCaseDetailValue);
  if (typeof value === "object") return Object.values(value).some(hasMeaningfulCaseDetailValue);
  return !EMPTY_DETAIL_VALUES.has(String(value).trim().toLowerCase());
}

function hasAnyCaseDetailField(data: CaseDetailData, fields: string[]) {
  return fields.some((field) => hasMeaningfulCaseDetailValue(data[field]));
}

function hasSubmittedArchiveStatus(value: unknown): boolean {
  if (!hasMeaningfulCaseDetailValue(value)) return false;
  return !INACTIVE_ARCHIVE_STATUSES.has(String(value).trim().toLowerCase());
}

export function getCaseDetailSectionVisibility(data: CaseDetailData = {}, status = "") {
  const firstCourt = hasAnyCaseDetailField(data, FIRST_COURT_FIELDS);
  const secondCourt = hasAnyCaseDetailField(data, SECOND_COURT_FIELDS);
  const executionCourt = hasAnyCaseDetailField(data, EXECUTION_COURT_FIELDS);
  const archive =
    hasAnyCaseDetailField(data, ARCHIVE_FIELDS) ||
    hasSubmittedArchiveStatus(data.archive_status) ||
    status.includes("归档");

  return {
    firstCourt,
    secondCourt,
    executionCourt,
    court: firstCourt || secondCourt || executionCourt,
    archive,
  };
}

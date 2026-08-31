export const COLLECTED_CLUE_STATUSES = Object.freeze(["已取证", "已转案件"]);

export function clueCaseNo(row) {
  const data = row?.data || {};
  return String(data.case_no || data.converted_case_no || "").trim();
}

export function clueInvestigatorSearchText(row, projectedDisplayName = "") {
  const data = row?.data || {};
  return [
    row?.owner,
    row?.owner_display_name,
    data.investigator,
    data.investigator_display_name,
    projectedDisplayName,
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(" ");
}

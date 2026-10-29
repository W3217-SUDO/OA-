import type { ArchiveSettlementTarget, HistoricalSettlementIdentity, SettlementSourceCounts } from "./types";

export function settlementSourceCounts(source: SettlementSourceCounts): SettlementSourceCounts {
  return {
    unknown_phase_total: source.unknown_phase_total,
    unknown_eligibility_total: source.unknown_eligibility_total,
    unknown_date_total: source.unknown_date_total,
  };
}

export function settlementSourceMessage(source: SettlementSourceCounts): string {
  const labels: [keyof SettlementSourceCounts, string][] = [
    ["unknown_phase_total", "案件阶段待核"],
    ["unknown_eligibility_total", "结算条件待核"],
    ["unknown_date_total", "原日期待核"],
  ];
  return labels.flatMap(([key, label]) => {
    const count = source[key];
    return count != null && count > 0 ? [`${label} ${count} 条`] : [];
  }).join("；");
}

export function isHistoricalSettlement(row: HistoricalSettlementIdentity): boolean {
  return row.source === "legacy" || row.historical === true || row.read_only === true;
}

/** 历史结算（legacy-normal / legacy-archive）由后端在办理时承接为现代记录（BUG20261028009/010）；缺有效编号的历史行仍不能办理。 */
export function requireWritableSettlements(rows: ArchiveSettlementTarget[]): void {
  if (rows.some(row => isHistoricalSettlement(row) && !/^legacy-(normal|archive):[1-9]\d*$/.test(String(row.id)))) {
    throw new Error("历史结算记录缺少来源编号，不能办理审批、支付、回退、重提或删除");
  }
}

/** 归档费办理目标：决定记录编号与历史归档费编号分开提交。 */
export function archiveRecordTargets(rows: { id: string | number }[]) {
  const record_ids: number[] = [];
  const projection_ids: string[] = [];
  for (const row of rows) {
    if (typeof row.id === "string" && /^legacy-archive:[1-9]\d*$/.test(row.id)) projection_ids.push(row.id);
    else record_ids.push(Number(row.id));
  }
  return { record_ids, projection_ids };
}

/** 普通结算办理目标：现代申请编号与历史结算编号分开提交。 */
export function settlementTargets(rows: { id: string | number }[]) {
  const application_ids: number[] = [];
  const projection_ids: string[] = [];
  for (const row of rows) {
    if (typeof row.id === "string" && /^legacy-normal:[1-9]\d*$/.test(row.id)) projection_ids.push(row.id);
    else application_ids.push(Number(row.id));
  }
  return { application_ids, projection_ids };
}

export function settlementExportIds(ids: (string | number)[], modernKey: "ids" | "application_ids") {
  const modern: (string | number)[] = [];
  const historical: string[] = [];
  for (const id of ids) {
    if (typeof id === "string" && /^legacy-(normal|archive):[1-9]\d*$/.test(id)) historical.push(id);
    else modern.push(id);
  }
  return {
    ...(modern.length ? { [modernKey]: modern.join(",") } : {}),
    ...(historical.length ? { projection_ids: historical.join(",") } : {}),
  };
}

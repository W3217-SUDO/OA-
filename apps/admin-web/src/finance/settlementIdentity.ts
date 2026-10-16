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

/** 历史投影标识不能进入现代审批、付款或撤回请求。 */
export function requireWritableSettlements(rows: ArchiveSettlementTarget[]): void {
  if (rows.some(row => isHistoricalSettlement(row) || /^legacy-(normal|archive):/.test(String(row.id)))) {
    throw new Error("历史结算记录只读，不能办理审批、支付、回退、重提或删除");
  }
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

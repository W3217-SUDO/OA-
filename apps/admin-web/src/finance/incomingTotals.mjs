const amountFields = {
  回款金额: "amount",
  已分金额: "allocated_amount",
  未分金额: "remaining_amount",
  已分官费: "assigned_official_fee",
  已分代理费: "assigned_agency_fee",
  已分其他费用: "assigned_other_fee",
};

export function incomingTotals(rows) {
  const hidden = rows.some((row) => row.amount === null);
  return Object.fromEntries(Object.entries(amountFields).map(([header, field]) => [
    header,
    hidden ? null : rows.reduce((total, row) => total + Math.round(Number(row[field] || 0) * 100), 0) / 100,
  ]));
}

/** 501294（陶国南 11-03）：案件详情里的线索号一个一个可点；能对上线索记录编号的带上编号。 */
export type CaseClueLink = { serial_no: string; id?: number };

const split = (value: unknown): string[] => (Array.isArray(value) ? value : [value])
  .flatMap((item) => String(item ?? "").split(/[,，;；、|\s]+/))
  .map((item) => item.trim())
  .filter(Boolean);

export function caseClueLinks(data: Record<string, unknown>): CaseClueLink[] {
  const listed = split(data.investigation_clue_nos).length ? split(data.investigation_clue_nos) : split(data.clue_nos);
  const nos = [...new Set(listed.length ? listed : split(data.investigation_clue || data.clue_no || data.source_clue_no))];
  const ids = (Array.isArray(data.investigation_clue_ids) ? data.investigation_clue_ids : [])
    .map((item) => Number(item)).filter((item) => Number.isInteger(item) && item > 0);
  const single = Number(data.clue_record_id || data.investigation_clue_id || data.clue_id) || undefined;
  return nos.map((serial_no, index) => ({
    serial_no,
    // 线索编号和线索号一一对应时按顺序配对；只有一条时用案件上的线索编号；对不上的点开时按线索号去查。
    id: ids.length === nos.length ? ids[index] : nos.length === 1 ? single : undefined,
  }));
}

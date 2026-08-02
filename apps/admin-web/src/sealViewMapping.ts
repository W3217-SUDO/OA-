export type SealViewSpec = { view: 'my' | 'audit' | 'all' | 'assets'; statuses: string[] };

const STATUS = {
  draft: '\u8349\u7a3f', pending: '\u5f85\u5ba1\u6279', stamping: '\u5f85\u7528\u5370',
  used: '\u5df2\u7528\u5370', archived: '\u5df2\u5f52\u6863', refused: '\u5df2\u62d2\u7edd', withdrawn: '\u5df2\u64a4\u56de',
};
export const sealViewMapping: Record<string, SealViewSpec> = {
  'seal-my': { view: 'my', statuses: [] },
  'seal-my-pending': { view: 'my', statuses: [STATUS.pending] },
  'seal-my-stamping': { view: 'my', statuses: [STATUS.stamping] },
  'seal-my-used': { view: 'my', statuses: [STATUS.used, STATUS.archived] },
  'seal-my-refused': { view: 'my', statuses: [STATUS.refused] },
  'seal-my-withdrawn': { view: 'my', statuses: [STATUS.withdrawn] },
  'seal-audit-pending': { view: 'audit', statuses: [STATUS.pending] },
  'seal-audit': { view: 'audit', statuses: [] },
  'seal-audit-stamping': { view: 'audit', statuses: [STATUS.stamping] },
  'seal-audit-refused': { view: 'audit', statuses: [STATUS.refused] },
  'seal-admin-pending': { view: 'all', statuses: [STATUS.stamping] },
  'seal-admin-used': { view: 'all', statuses: [STATUS.used] },
  'seal-admin': { view: 'all', statuses: [] },
};
export function sealViewSpec(route: string): SealViewSpec {
  if (sealViewMapping[route]) return sealViewMapping[route];
  if (route.startsWith('seal-audit-')) return { view: 'audit', statuses: [] };
  if (route.startsWith('seal-admin-')) return { view: 'all', statuses: [] };
  if (route.startsWith('seal-my-')) return { view: 'my', statuses: [] };
  return { view: 'my', statuses: [] };
}

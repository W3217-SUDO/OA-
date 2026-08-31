export const COLLECTED_CLUE_STATUSES: readonly string[];

export type CollectedClueRow = {
  owner?: string;
  owner_display_name?: string;
  data?: Record<string, unknown>;
};

export function clueCaseNo(row: CollectedClueRow): string;

export function clueInvestigatorSearchText(
  row: CollectedClueRow,
  projectedDisplayName?: string,
): string;

export type ParameterRelationItem = {
  id?: number;
  code?: string;
  name?: string;
  value?: string;
  label?: string;
};

export type ParameterRelation = {
  sources: ParameterRelationItem[];
  targets: ParameterRelationItem[];
  relations: Record<string, number[]>;
};

export type RelationCandidate = ParameterRelationItem;

export function filterCaseFileTypesForCaseType<T extends RelationCandidate>(
  caseType: string,
  fileTypes: T[],
  relation?: ParameterRelation | null,
): T[];

export function filterCasePhasesForCaseType<T extends RelationCandidate>(
  caseType: string,
  phases: T[],
  relation?: ParameterRelation | null,
): T[];

export const FEE_SUBTYPE_TO_TYPE: Record<string, string>;
export const LEGACY_OFFICIAL_FEE_SUBTYPES: string[];

export function filterFeeSubtypesForFileType(
  fileType: string,
  subtypes: string[],
  relation?: ParameterRelation | null,
): string[];

export function getRelatedTargetIds(
  sourceValue: string,
  relation?: ParameterRelation | null,
): number[];

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
export const LEGACY_THIRD_PARTY_FEE_SUBTYPES: string[];
export const LEGACY_AGENCY_FEE_SUBTYPES: string[];
export const PLATFORM_AGENCY_FEE_SUBTYPE: string;
export function agencyFeeSubtypesForScope(scope: unknown): string[];
export function normalizeFeeSubtypeForScope(scope: unknown, subtype: unknown): string;
export const LEGACY_OTHER_FEE_SUBTYPES: string[];

export function filterFeeSubtypesForFileType(
  fileType: string,
  subtypes: string[],
  relation?: ParameterRelation | null,
): string[];

export function getRelatedTargetIds(
  sourceValue: string,
  relation?: ParameterRelation | null,
): number[];

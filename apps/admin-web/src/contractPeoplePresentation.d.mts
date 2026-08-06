export const PERSON_NAME_PLACEHOLDER: string;

export function isChinesePersonName(value: unknown): boolean;

export function displayChinesePersonName(
  value: unknown,
  directory?: Array<{ username?: unknown; display_name?: unknown }>,
): string;

export function displayChinesePersonNames(
  values: unknown,
  directory?: Array<{ username?: unknown; display_name?: unknown }>,
): string;

export function buildChinesePersonOptions<T>(
  users?: T[],
  predicate?: (user: T) => boolean,
  options?: { allowNonChinese?: boolean },
): Array<{ value: string; label: string }>;

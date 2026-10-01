import dayjs from "dayjs";
import type { Dayjs } from "dayjs";

export type FinanceOriginalQuery = Record<string, unknown>;

export function dateQueryRange(value: unknown): [Dayjs | null, Dayjs | null] | undefined {
  if (!Array.isArray(value)) return undefined;
  return [dayjs.isDayjs(value[0]) ? value[0] : null, dayjs.isDayjs(value[1]) ? value[1] : null];
}

export function queryArray(value: unknown): readonly unknown[] | undefined {
  return Array.isArray(value) ? value : undefined;
}

export function amountQueryRange(value: unknown): [number | null, number | null] | undefined {
  if (!Array.isArray(value)) return undefined;
  return [typeof value[0] === "number" ? value[0] : null, typeof value[1] === "number" ? value[1] : null];
}

export function queryTextValue(value: unknown): string | number | undefined {
  return typeof value === "string" || typeof value === "number" ? value : undefined;
}

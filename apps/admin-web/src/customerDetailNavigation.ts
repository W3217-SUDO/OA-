import { api } from "./api";

export type CustomerDetailNavigationContext = {
  id?: number;
  serial_no?: string;
  title?: string;
  at: number;
};

const STORAGE_KEY = "sunhold:customer-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export type ResolvedCustomerDetailTarget = {
  id: number;
  serial_no: string;
  title: string;
};

/**
 * Resolves a customer through the same protected records API that powers the
 * detail view. Callers must resolve before routing so an obsolete text-only
 * relationship cannot silently land on an unrelated customer list.
 */
export const resolveCustomerDetailTarget = async (target: {
  id?: number;
  serial_no?: string;
  title?: string;
}): Promise<ResolvedCustomerDetailTarget | null> => {
  const targetId = Number(target.id || 0);
  if (targetId) {
    try {
      const { data } = await api.get(`/records/${targetId}`);
      if (data.module === "customer") {
        return { id: Number(data.id), serial_no: String(data.serial_no || ""), title: String(data.title || "") };
      }
    } catch {
      // Try stable identifiers below; access is always checked by the API.
    }
  }
  const serialNo = String(target.serial_no || "").trim();
  const title = String(target.title || "").trim();
  for (const keyword of [...new Set([serialNo, title].filter(Boolean))]) {
    try {
      const { data } = await api.get("/records", { params: { module: "customer", keyword, page_size: 100 } });
      const row = (data.items || []).find((item: any) =>
        (serialNo && item.serial_no === serialNo) || (title && item.title === title),
      );
      if (row) return { id: Number(row.id), serial_no: String(row.serial_no || ""), title: String(row.title || "") };
    } catch {
      // Continue to the other stable identifier before reporting a miss.
    }
  }
  return null;
};

export const rememberCustomerDetailTarget = (target: { id?: number; serial_no?: string; title?: string }) => {
  const serialNo = String(target.serial_no || "").trim();
  const title = String(target.title || "").trim();
  const id = Number(target.id || 0) || undefined;
  if (!serialNo && !title && !id) return false;
  sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ id, serial_no: serialNo || undefined, title: title || undefined, at: Date.now() }),
  );
  return true;
};

export const consumeCustomerDetailTarget = (): CustomerDetailNavigationContext | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as CustomerDetailNavigationContext;
    if (!parsed || (!parsed.id && !parsed.serial_no && !parsed.title)) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

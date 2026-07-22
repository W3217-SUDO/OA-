export type CustomerDetailNavigationContext = {
  id?: number;
  serial_no?: string;
  title?: string;
  at: number;
};

const STORAGE_KEY = "sunhold:customer-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

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

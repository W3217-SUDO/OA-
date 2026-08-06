export type CustomerRelationNavigationContext = {
  id?: number;
  serial_no?: string;
  title?: string;
  target: "contracts" | "civil-cases";
  at: number;
};

const STORAGE_KEY = "sunhold:customer-relation-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberCustomerRelationTarget = (target: { id?: number; serial_no?: string; title?: string; target: "contracts" | "civil-cases" }) => {
  const serialNo = String(target.serial_no || "").trim();
  const title = String(target.title || "").trim();
  const id = Number(target.id || 0) || undefined;
  if (!serialNo && !title && !id) return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id, serial_no: serialNo || undefined, title: title || undefined, target: target.target, at: Date.now() }));
  return true;
};

export const consumeCustomerRelationTarget = (): CustomerRelationNavigationContext | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as CustomerRelationNavigationContext;
    if (!parsed || !["contracts", "civil-cases"].includes(parsed.target) || (!parsed.id && !parsed.serial_no && !parsed.title)) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

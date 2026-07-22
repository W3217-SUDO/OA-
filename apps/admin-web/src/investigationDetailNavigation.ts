export type InvestigationDetailNavigationContext = {
  id?: number;
  serial_no?: string;
  module?: string;
  at: number;
};

const STORAGE_KEY = "sunhold:investigation-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberInvestigationDetailTarget = (target: { id?: number; serial_no?: string; module?: string }) => {
  const serialNo = String(target.serial_no || "").trim();
  const module = String(target.module || "").trim();
  const id = Number(target.id || 0) || undefined;
  if (!serialNo && !id) return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id, serial_no: serialNo || undefined, module: module || undefined, at: Date.now() }));
  return true;
};

export const consumeInvestigationDetailTarget = (): InvestigationDetailNavigationContext | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as InvestigationDetailNavigationContext;
    if (!parsed || (!parsed.id && !parsed.serial_no)) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

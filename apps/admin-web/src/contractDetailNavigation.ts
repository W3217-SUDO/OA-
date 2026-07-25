export type ContractDetailNavigationContext = {
  id?: number;
  serial_no?: string;
  at: number;
};

const STORAGE_KEY = "sunhold:contract-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;
export const CONTRACT_DETAIL_TARGET_EVENT = "sunhold:contract-detail-target";

export const rememberContractDetailTarget = (target: { id?: number; serial_no?: string }) => {
  const serialNo = String(target.serial_no || "").trim();
  const id = Number(target.id || 0) || undefined;
  if (!serialNo && !id) return false;
  const context: ContractDetailNavigationContext = { id, serial_no: serialNo || undefined, at: Date.now() };
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(context));
  } catch {
    // The application-level event below remains the primary same-tab path.
  }
  window.dispatchEvent(new CustomEvent(CONTRACT_DETAIL_TARGET_EVENT, { detail: context }));
  return true;
};

export const clearContractDetailTarget = () => {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage is only a reload fallback; no action is required when unavailable.
  }
};

export const consumeContractDetailTarget = (): ContractDetailNavigationContext | null => {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(STORAGE_KEY);
    const parsed = JSON.parse(raw) as ContractDetailNavigationContext;
    if (!parsed || (!parsed.id && !parsed.serial_no)) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

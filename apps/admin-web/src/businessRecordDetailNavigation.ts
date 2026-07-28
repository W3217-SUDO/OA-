export type BusinessRecordDetailModule = "finance" | "seal" | "document" | "warehouse" | "hr";

export type BusinessRecordDetailNavigationContext = {
  id: number;
  module: BusinessRecordDetailModule;
  at: number;
};

const STORAGE_KEY = "sunhold:business-record-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberBusinessRecordDetailTarget = (target: {
  id?: number;
  module: BusinessRecordDetailModule;
}) => {
  const id = Number(target.id || 0);
  if (!id) return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id, module: target.module, at: Date.now() }));
  return true;
};

export const consumeBusinessRecordDetailTarget = (module: BusinessRecordDetailModule): BusinessRecordDetailNavigationContext | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as BusinessRecordDetailNavigationContext;
    if (!parsed || !parsed.id || parsed.module !== module) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

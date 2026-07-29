export type BusinessRecordDetailModule = "finance" | "invoice" | "refund" | "finance_package" | "finance_settlement" | "finance_archive_settlement" | "seal" | "document" | "warehouse" | "hr";

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

export const consumeBusinessRecordDetailTarget = (module: BusinessRecordDetailModule | BusinessRecordDetailModule[]): BusinessRecordDetailNavigationContext | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as BusinessRecordDetailNavigationContext;
    const modules = Array.isArray(module) ? module : [module];
    if (!parsed || !parsed.id || !modules.includes(parsed.module)) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

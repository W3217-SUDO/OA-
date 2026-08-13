export type BusinessRecordDetailModule = "finance" | "invoice" | "refund" | "finance_package" | "finance_settlement" | "finance_archive_settlement" | "seal" | "document" | "warehouse" | "hr";

export type BusinessRecordDetailAction = "view" | "create_invoice" | "create_refund";

export type BusinessRecordDetailNavigationContext = {
  id: number;
  module: BusinessRecordDetailModule;
  action?: BusinessRecordDetailAction;
  at: number;
};

const STORAGE_KEY = "sunhold:business-record-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberBusinessRecordDetailTarget = (target: {
  id?: number;
  module: BusinessRecordDetailModule;
  action?: BusinessRecordDetailAction;
}) => {
  const id = Number(target.id || 0);
  if (!id) return false;
  const action = target.action || "view";
  if (!["view", "create_invoice", "create_refund"].includes(action)) return false;
  if (action !== "view" && target.module !== "finance") return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id, module: target.module, action, at: Date.now() }));
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
    const action = parsed.action || "view";
    if (!["view", "create_invoice", "create_refund"].includes(action)) return null;
    if (action !== "view" && parsed.module !== "finance") return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return { ...parsed, action };
  } catch {
    return null;
  }
};

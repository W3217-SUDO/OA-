export type TaskDetailNavigationContext = {
  id?: number;
  serial_no?: string;
  at: number;
};

const STORAGE_KEY = "sunhold:task-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberTaskDetailTarget = (target: { id?: number; serial_no?: string }) => {
  const serialNo = String(target.serial_no || "").trim();
  const id = Number(target.id || 0) || undefined;
  if (!serialNo && !id) return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id, serial_no: serialNo || undefined, at: Date.now() }));
  return true;
};

export const consumeTaskDetailTarget = (): TaskDetailNavigationContext | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as TaskDetailNavigationContext;
    if (!parsed || (!parsed.id && !parsed.serial_no)) return null;
    if (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
};

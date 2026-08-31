const STORAGE_KEY = "sunhold:incoming-payment-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberIncomingPaymentDetailTarget = (id: number) => {
  const normalizedId = Number(id || 0);
  if (!normalizedId) return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id: normalizedId, at: Date.now() }));
  return true;
};

export const consumeIncomingPaymentDetailTarget = (): number | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const parsed = JSON.parse(raw) as { id?: number; at?: number };
    const id = Number(parsed.id || 0);
    if (!id || (parsed.at && Date.now() - Number(parsed.at) > MAX_AGE_MS)) return null;
    return id;
  } catch {
    return null;
  }
};

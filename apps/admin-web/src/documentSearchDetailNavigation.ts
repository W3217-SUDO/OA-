export type DocumentSearchDetailKind = "attachment" | "template";

type DocumentSearchDetailTarget = {
  id: number;
  kind: DocumentSearchDetailKind;
  at: number;
};

const STORAGE_KEY = "sunhold:document-search-detail-context";
const MAX_AGE_MS = 60 * 60 * 1000;

export const rememberDocumentSearchDetailTarget = (target: {
  id?: number;
  kind: DocumentSearchDetailKind;
}) => {
  const id = Number(target.id || 0);
  if (!id) return false;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id, kind: target.kind, at: Date.now() }));
  return true;
};

export const consumeDocumentSearchDetailTarget = (): DocumentSearchDetailTarget | null => {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(STORAGE_KEY);
  try {
    const target = JSON.parse(raw) as DocumentSearchDetailTarget;
    if (!target?.id || !["attachment", "template"].includes(target.kind)) return null;
    if (Date.now() - Number(target.at || 0) > MAX_AGE_MS) return null;
    return target;
  } catch {
    return null;
  }
};

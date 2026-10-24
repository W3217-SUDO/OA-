// 反馈草稿：文字和勾选的页面存 localStorage，截图/附件存 IndexedDB（File 可直接结构化克隆）。
// 浏览器禁用存储时静默降级，表单照常可用。
export type FeedbackDraft = { description: string; pageKeys: string[]; files: File[]; savedAt: number };

const DB_NAME = "sunhold-feedback-draft";
const STORE = "files";

function draftOwner() {
  try { return String(JSON.parse(localStorage.getItem("user") || "{}").username || "anonymous"); }
  catch { return "anonymous"; }
}
const textKey = () => `sunhold:feedback-draft:${draftOwner()}`;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb();
  try {
    return await new Promise<T>((resolve, reject) => {
      const request = run(db.transaction(STORE, mode).objectStore(STORE));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export async function loadFeedbackDraft(): Promise<FeedbackDraft | null> {
  let text: Omit<FeedbackDraft, "files"> | null = null;
  try { text = JSON.parse(localStorage.getItem(textKey()) || "null"); } catch { text = null; }
  let files: File[] = [];
  try { files = (await withStore<File[] | undefined>("readonly", (store) => store.get(draftOwner()))) || []; }
  catch { files = []; }
  if (!text && !files.length) return null;
  return { description: text?.description || "", pageKeys: text?.pageKeys || [], files, savedAt: text?.savedAt || Date.now() };
}

export async function saveFeedbackDraft(draft: Omit<FeedbackDraft, "savedAt">): Promise<number> {
  const savedAt = Date.now();
  try {
    localStorage.setItem(textKey(), JSON.stringify({ description: draft.description, pageKeys: draft.pageKeys, savedAt }));
  } catch { /* 存储不可用时只是不保存草稿 */ }
  try {
    if (draft.files.length) await withStore("readwrite", (store) => store.put(draft.files, draftOwner()));
    else await withStore("readwrite", (store) => store.delete(draftOwner()));
  } catch { /* 同上 */ }
  return savedAt;
}

export async function clearFeedbackDraft() {
  try { localStorage.removeItem(textKey()); } catch { /* ignore */ }
  try { await withStore("readwrite", (store) => store.delete(draftOwner())); } catch { /* ignore */ }
}

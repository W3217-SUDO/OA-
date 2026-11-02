// 反馈草稿：文字和勾选的页面存 localStorage，截图/附件存 IndexedDB（File 可直接结构化克隆）。
// 浏览器禁用存储时静默降级，表单照常可用。
// sourceRoute 记下草稿是从哪个页面进来写的：换了来源页再进来时，只恢复文字和文件，页面和按钮按新的来源页重选。
export type FeedbackDraft = {
  description: string; pageKeys: string[]; controls: string[]; sourceRoute: string; files: File[]; savedAt: number;
};

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

/** 有没提交的草稿（同步判断，用来决定回到“问题反馈”时先打开填写页；BUG20261102002）。 */
export function hasFeedbackDraft(): boolean {
  try {
    const text = JSON.parse(localStorage.getItem(textKey()) || "null");
    return Boolean(text && (String(text.description || "").trim() || text.hasFiles));
  } catch { return false; }
}

export async function loadFeedbackDraft(): Promise<FeedbackDraft | null> {
  let text: Omit<FeedbackDraft, "files"> | null = null;
  try { text = JSON.parse(localStorage.getItem(textKey()) || "null"); } catch { text = null; }
  let files: File[] = [];
  try { files = (await withStore<File[] | undefined>("readonly", (store) => store.get(draftOwner()))) || []; }
  catch { files = []; }
  if (!text && !files.length) return null;
  return {
    description: text?.description || "", pageKeys: text?.pageKeys || [], controls: text?.controls || [],
    sourceRoute: text?.sourceRoute || "", files, savedAt: text?.savedAt || Date.now(),
  };
}

export async function saveFeedbackDraft(draft: Omit<FeedbackDraft, "savedAt">): Promise<number> {
  const savedAt = Date.now();
  try {
    const { files: _files, ...text } = draft;
    localStorage.setItem(textKey(), JSON.stringify({ ...text, hasFiles: draft.files.length > 0, savedAt }));
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

// 问题详情“处理和沟通”的回复草稿：按单号分开存，切走再回来、关掉详情再打开都还在；发送成功后清空（BUG20261102002，高勤兰 11-02）。
const replyTextKey = (feedbackId: number) => `sunhold:feedback-reply-draft:${draftOwner()}:${feedbackId}`;
const replyFilesKey = (feedbackId: number) => `${draftOwner()}:reply:${feedbackId}`;

export type FeedbackReplyDraft = { text: string; files: File[] };

export async function loadFeedbackReplyDraft(feedbackId: number): Promise<FeedbackReplyDraft | null> {
  let text = "";
  try { text = String(JSON.parse(localStorage.getItem(replyTextKey(feedbackId)) || "null")?.text || ""); } catch { text = ""; }
  let files: File[] = [];
  try { files = (await withStore<File[] | undefined>("readonly", (store) => store.get(replyFilesKey(feedbackId)))) || []; }
  catch { files = []; }
  return text || files.length ? { text, files } : null;
}

export async function saveFeedbackReplyDraft(feedbackId: number, text: string, files: File[]) {
  try { localStorage.setItem(replyTextKey(feedbackId), JSON.stringify({ text, savedAt: Date.now() })); } catch { /* 存储不可用时只是不保存草稿 */ }
  try {
    if (files.length) await withStore("readwrite", (store) => store.put(files, replyFilesKey(feedbackId)));
    else await withStore("readwrite", (store) => store.delete(replyFilesKey(feedbackId)));
  } catch { /* 同上 */ }
}

export async function clearFeedbackReplyDraft(feedbackId: number) {
  try { localStorage.removeItem(replyTextKey(feedbackId)); } catch { /* ignore */ }
  try { await withStore("readwrite", (store) => store.delete(replyFilesKey(feedbackId))); } catch { /* ignore */ }
}

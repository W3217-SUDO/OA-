import test from 'node:test';
import assert from 'node:assert/strict';

// BUG20261102002（高勤兰 11-02）：有没提交的反馈草稿时，回到“问题反馈”先打开填写页。
const store = new Map();
globalThis.localStorage = { getItem: (key) => store.get(key) ?? null, setItem: (key, value) => store.set(key, String(value)), removeItem: (key) => store.delete(key) };
globalThis.indexedDB = { open() { const request = {}; queueMicrotask(() => request.onerror?.()); return request; } };
const { hasFeedbackDraft, saveFeedbackDraft, clearFeedbackDraft } = await import('../src/feedback/draft.ts');

test('draft text or attachments mean the page reopens on the form', async () => {
  store.set('user', JSON.stringify({ username: 'gaoqinlan' }));
  assert.equal(hasFeedbackDraft(), false);
  await saveFeedbackDraft({ description: '右键菜单灰色', pageKeys: ['ipr-patent'], controls: [], sourceRoute: 'ipr-patent', files: [] });
  assert.equal(hasFeedbackDraft(), true);
  await saveFeedbackDraft({ description: '  ', pageKeys: [], controls: [], sourceRoute: '', files: [new Blob(['x'])] });
  assert.equal(hasFeedbackDraft(), true);
  await clearFeedbackDraft();
  assert.equal(hasFeedbackDraft(), false);
});

test('reply drafts are kept per ticket and cleared separately', async () => {
  const { loadFeedbackReplyDraft, saveFeedbackReplyDraft, clearFeedbackReplyDraft } = await import('../src/feedback/draft.ts');
  store.set('user', JSON.stringify({ username: 'gaoqinlan' }));
  await saveFeedbackReplyDraft(500923, '写了一半的回复', []);
  await saveFeedbackReplyDraft(500929, '另一张单', []);
  assert.equal((await loadFeedbackReplyDraft(500923))?.text, '写了一半的回复');
  assert.equal((await loadFeedbackReplyDraft(500929))?.text, '另一张单');
  await clearFeedbackReplyDraft(500923);
  assert.equal(await loadFeedbackReplyDraft(500923), null);
  assert.equal((await loadFeedbackReplyDraft(500929))?.text, '另一张单');
});

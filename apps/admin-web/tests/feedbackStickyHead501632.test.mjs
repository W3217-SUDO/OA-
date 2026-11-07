import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// BUG20261105023（tgn 11-05）：“我的反馈”页头和页签吸顶，只滚动下面的列表和详情；不用钉钉 Chrome 100 不认的写法。
const css = readFileSync(new URL('../src/feedback/feedback.css', import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const page = readFileSync(new URL('../src/feedback/FeedbackPage.tsx', import.meta.url), 'utf8');
const nav = readFileSync(new URL('../src/feedback/navigation.ts', import.meta.url), 'utf8');

test('feedback page head sticks to the top of the page scroller', () => {
  const rule = css.match(/\.feedback-page-card > \.ant-card-head \{([^}]*)\}/);
  assert.ok(rule, 'sticky rule exists');
  assert.match(rule[1], /position: sticky/);
  assert.match(rule[1], /top: 0/);
  assert.match(rule[1], /background:/);
  assert.doesNotMatch(css, /:has\(|dvh|color-mix|@container/);
});

test('clicking a tab, including the current one, returns to its list at the top', () => {
  assert.match(page, /ant-segmented-item-selected/);
  assert.match(page, /scrollFeedbackToTop\(headRef\.current\)/);
  assert.match(nav, /closest\("\.page-workbench"\)\?\.scrollTo\(0, 0\)/);
  assert.match(nav, /closest\("\.feedback-page-card"\)\?\.querySelector\(":scope > \.ant-card-body"\)\?\.scrollTo\(0, 0\)/);
});

test('only 返回列表 sticks under the measured page head; status/withdraw/delete scroll with the feedback', () => {
  const detail = readFileSync(new URL('../src/feedback/FeedbackDetail.tsx', import.meta.url), 'utf8');
  const rule = css.match(/\.feedback-page-card \.feedback-detail-back \{([^}]*)\}/);
  assert.ok(rule, 'sticky toolbar rule exists');
  assert.match(rule[1], /position: sticky/);
  assert.match(rule[1], /top: var\(--feedback-head-h/);
  assert.match(page, /ResizeObserver/);
  assert.match(page, /--feedback-head-h/);
  assert.doesNotMatch(css, /\.feedback-detail-head \{[^}]*position: sticky/);
  assert.match(detail, /feedback-detail-back">\s*<Button[\s\S]*?>返回列表<\/Button>\s*<\/div>/);
  assert.match(detail, /scrollFeedbackToTop\(event\.currentTarget\); onBack\(\)/);
});

test('问题反馈 page drops the page title block so 我的反馈 tabs are the top row', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /active !== "ai-chat" && active !== FEEDBACK_ROUTE && <div className="page-head">/);
});

// 陶威 11-07：手机钉钉（华为等机型 UC U4 内核）滚动容器里的 sticky 不可靠，页头被内容盖住。
// 手机上改成卡片占满高度、页头在正常排版里、只有内容区滚动；桌面规则不变。
test('on phones the page head stays out of the scroller: card fills the height and only its body scrolls', () => {
  const media = css.match(/@media \(max-width: 991px\) \{([\s\S]*)\}\s*$/);
  assert.ok(media, 'phone media block exists');
  const block = media[1];
  const sel = '\\.page-workbench > \\.workspace-page:not\\(\\.is-cached\\) > \\.feedback-page-card\\.feedback-page-card\\.feedback-page-card';
  const card = block.match(new RegExp(sel + ' \\{([^}]*)\\}'));
  assert.ok(card, 'card rule');
  assert.match(card[1], /display: flex !important/);
  assert.match(card[1], /flex-direction: column/);
  assert.match(card[1], /height: 100% !important/);
  assert.match(card[1], /overflow: hidden !important/);
  const head = block.match(new RegExp(sel + ' > \\.ant-card-head \\{([^}]*)\\}'));
  assert.ok(head, 'head rule');
  assert.match(head[1], /position: relative/);
  assert.match(head[1], /flex: 0 0 auto/);
  const body = block.match(new RegExp(sel + ' > \\.ant-card-body \\{([^}]*)\\}'));
  assert.ok(body, 'body rule');
  assert.match(body[1], /overflow-y: auto !important/);
  assert.match(body[1], /min-height: 0/);
  assert.match(block, /\.feedback-page-card \.feedback-detail-back \{ top: -14px; \}/);
  assert.match(block, /\.feedback-page-card \.feedback-chat-composer \{ bottom: -14px; \}/);
  // 桌面的整页 sticky 规则还在。
  assert.match(css, /\.feedback-page-card > \.ant-card-head \{[^}]*position: sticky/);
});

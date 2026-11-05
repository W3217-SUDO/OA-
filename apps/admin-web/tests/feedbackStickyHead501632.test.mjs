import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// BUG20261105023（tgn 11-05）：“我的反馈”页头和页签吸顶，只滚动下面的列表和详情；不用钉钉 Chrome 100 不认的写法。
const css = readFileSync(new URL('../src/feedback/feedback.css', import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const page = readFileSync(new URL('../src/feedback/FeedbackPage.tsx', import.meta.url), 'utf8');

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
  assert.match(page, /closest\("\.page-workbench"\)/);
  assert.match(page, /scrollTop = 0/);
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
  assert.match(detail, /closest\("\.page-workbench"\)\?\.scrollTo\(0, 0\); onBack\(\)/);
});

test('问题反馈 page drops the page title block so 我的反馈 tabs are the top row', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /active !== "ai-chat" && active !== FEEDBACK_ROUTE && <div className="page-head">/);
});

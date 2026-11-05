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

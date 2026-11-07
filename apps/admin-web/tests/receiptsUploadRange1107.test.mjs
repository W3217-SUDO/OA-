import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// 陶威 11-07：公司收文默认当天，却整包取回全所收文再在浏览器里筛，一直“正在加载”。上传日期要交给后端筛。
const page = readFileSync(new URL('../src/aws/DocumentCenterPage.tsx', import.meta.url), 'utf8');

test('收文台取数带上上传日期起止', () => {
  assert.match(page, /api\.get\("\/documents\/receipts", \{\s*params: \{ scope, \.\.\.\(range \? \{ uploaded_from: range\[0\]\.format\("YYYY-MM-DD"\), uploaded_to: range\[1\]\.format\("YYYY-MM-DD"\) \} : \{\}\) \}/);
});

test('上传日期变了（含搜具体字段放开日期、清空条件）就重新取', () => {
  assert.match(page, /const receiptRangeKey = receiptQuery\.upload_range/);
  assert.match(page, /if \(loadedReceiptRange\.current === receiptRangeKey\) return;[\s\S]*?void load\(\);\s*\}, \[receiptRangeKey\]\);/);
});

test('被顶替的旧取数不关加载状态', () => {
  assert.match(page, /if \(seq !== receiptLoadSeq\.current\) \{\s*superseded = true;\s*return;\s*\}/);
  assert.match(page, /finally \{\s*if \(!superseded\) setLoading\(false\);\s*\}/);
});

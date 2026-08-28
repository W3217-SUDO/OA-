import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 8 uses the legacy fee empty state for both fee scopes", () => {
  assert.match(page, /没有查询到费用信息。/);
  assert.match(page, /locale=\{\{emptyText:renderCaseFeeEmptyState\("律所"\)\}\}/);
  assert.match(page, /locale=\{\{emptyText:renderCaseFeeEmptyState\("平台"\)\}\}/);
  assert.match(page, /\["官费","第三方费用","代理费","其他费用"\]\.map\(subtype=>/);
  assert.match(page, />新增\{subtype\}<\/Button>/);
});

test("row 8 keeps bottom actions only when fee rows exist", () => {
  assert.match(page, /firmFeeRows\.length>0&&<Space className="case-legacy-bottom-actions">/);
  assert.match(page, /platformFeeRows\.length>0&&<Space className="case-legacy-bottom-actions">/);
});

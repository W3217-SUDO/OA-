import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../api-server/app/main.py", import.meta.url), "utf8");

test("contract list keeps CSV export and adds real Excel export", () => {
  assert.match(page, /api\.get\("\/records\/export-excel"/);
  assert.match(page, /signed_at_start/);
  assert.match(page, /contract_body: query\.contract_body/);
  assert.match(page, /link\.download = "合同资料\.xls"/);
  assert.match(page, /导出Excel/);
  assert.match(page, /api\.get\("\/records\/export"/);
  assert.match(page, /导出CSV/);
  assert.match(api, /records\/export-excel/);
  assert.match(api, /signed_at_start: str/);
  assert.match(api, /if record_type and data\.get\("type"\) != record_type/);
  assert.match(api, /_excel_response\(f"\{module\}-\{date\.today\(\)\}\.xls"/);
});

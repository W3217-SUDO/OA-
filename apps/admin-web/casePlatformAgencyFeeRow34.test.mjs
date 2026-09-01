import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { feeTypeTreeData, selectableFeeTypes } from "./src/feeTypeHierarchy.mjs";

const catalog = [
  { id: 1, code: "AGENCY", name: "代理费", selectable: false, is_active: true, expense_scopes: ["律所", "平台"] },
  { id: 2, code: "WITNESS", parent_code: "AGENCY", name: "律师见证费", base_fee_type: "代理费", selectable: true, is_active: true, expense_scopes: ["律所", "平台"] },
  { id: 3, code: "PLATFORM", parent_code: "AGENCY", name: "平台代理费", base_fee_type: "代理费", selectable: true, is_active: true, expense_scopes: ["平台"] },
  { id: 4, code: "PLATFORM_MIGRATED", parent_code: "AGENCY", name: "平台代理费", base_fee_type: "代理费", selectable: true, is_active: true, expense_scopes: ["平台"] },
];

test("9.1 row 34 platform agency picker contains exactly the legacy platform agency type", () => {
  assert.deepEqual(selectableFeeTypes(catalog, "平台", "agency").map((item) => item.name), ["平台代理费"]);
  assert.deepEqual(feeTypeTreeData(catalog, "平台", "agency"), [{
    value: 1,
    title: "代理费",
    selectable: false,
    children: [{ value: 3, title: "平台代理费", selectable: true, children: undefined }],
  }]);
});

test("9.1 row 34 does not leak the platform-only subtype into law-firm agency fees", () => {
  assert.deepEqual(selectableFeeTypes(catalog, "律所", "agency").map((item) => item.name), ["律师见证费"]);
});

test("9.1 row 34 keeps the fee-type trigger wide enough for horizontal Chinese labels", () => {
  const css = readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");
  const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
  assert.match(css, /grid-template-columns:82px 95px 130px 65px/);
  assert.match(css, /min-width:614px/);
  assert.equal((page.match(/popupMatchSelectWidth=\{180\}/g) || []).length, 2);
});

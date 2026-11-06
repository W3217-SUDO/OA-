import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");
const css = readFileSync(new URL("../src/case-center.css", import.meta.url), "utf8");

test("501662 platform agency drawer hides 所属线索 column and cell", () => {
  assert.match(page, /const platformAgencyFeeDraft = activeFeeContractScope === "平台" && feeSubtypePreset === "agency";/);
  assert.match(page, /\{!platformAgencyFeeDraft && <span>所属线索<\/span>\}/);
  assert.match(page, /\{!platformAgencyFeeDraft && <Form\.Item noStyle shouldUpdate=\{\(prev, next\) => prev\.items\?\.\[field\.name\]\?\.expense_subtype/);
});

test("501662 contract cell shows the full contract number only", () => {
  assert.match(page, /labelRender=\{\(selected\) => String\(feeContractOptions\.find\(\(item\) => item\.value === selected\.value\)\?\.label \?\? selected\.label \?\? ""\)\.split\("｜"\)\[0\]\}/);
  assert.match(css, /\.case-fee-entry-table-full-contract \.case-fee-entry-head,\.case-fee-entry-table-full-contract \.case-fee-entry-row\{grid-template-columns:82px 160px 130px 65px/);
  assert.match(css, /\.case-fee-entry-table-with-clue\.case-fee-entry-table-full-contract \.case-fee-entry-head,.*grid-template-columns:82px 160px 130px 110px/);
});

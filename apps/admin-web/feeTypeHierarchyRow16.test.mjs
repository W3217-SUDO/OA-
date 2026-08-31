import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  feeTypeSelection,
  feeTypeTreeData,
  initialFeeTypeId,
  selectableFeeTypes,
} from "./src/feeTypeHierarchy.mjs";

const catalog = [
  { id: 1, code: "OFFICIAL", name: "official", parent_code: "", base_fee_type: "official-base", expense_scopes: ["firm"], is_active: true, selectable: false },
  { id: 2, code: "160000", name: "litigation", parent_code: "OFFICIAL", base_fee_type: "official-base", expense_scopes: ["firm"], is_active: true, selectable: false },
  { id: 3, code: "160001", name: "first-instance", parent_code: "160000", base_fee_type: "official-base", expense_scopes: ["firm"], is_active: true, selectable: true },
  { id: 4, code: "160002", name: "inactive", parent_code: "160000", base_fee_type: "official-base", expense_scopes: ["firm"], is_active: false, selectable: true },
];

test("fee hierarchy keeps ancestors visible but only leaves selectable", () => {
  const tree = feeTypeTreeData(catalog, "firm");
  assert.equal(tree.length, 1);
  assert.equal(tree[0].selectable, false);
  assert.equal(tree[0].children[0].selectable, false);
  assert.deepEqual(tree[0].children[0].children.map((item) => item.value), [3]);
  assert.deepEqual(selectableFeeTypes(catalog, "firm").map((item) => item.id), [3]);
});

test("selection and initial value resolve the authoritative master id", () => {
  assert.equal(initialFeeTypeId(catalog, "firm", "", "first-instance"), 3);
  assert.equal(feeTypeSelection(catalog, 3).base_fee_type, "official-base");
  assert.equal(initialFeeTypeId(catalog, "platform"), undefined);
});

test("system and case pages consume the same hierarchical fee master", () => {
  const systemPage = readFileSync(new URL("./src/SystemCenterPage.tsx", import.meta.url), "utf8");
  const casePage = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
  assert.match(systemPage, /feeTypeTreeRows\(visibleParameters\)/);
  assert.match(systemPage, /fee_type:\s*\[\{ key: "parent_code", label: "\u4e0a\u7ea7\u8d39\u7528\u7c7b\u578b"/u);
  assert.match(casePage, /category: "fee_type"/);
  assert.match(casePage, /name=\{\[field\.name, "fee_type_id"\]\}/);
  assert.match(casePage, /TreeSelect[\s\S]*treeData=\{feeTypeTreeOptions\}/);
  assert.equal((casePage.match(/TreeSelect showSearch treeNodeFilterProp="title"/g) || []).length, 4);
  assert.match(casePage, /fee_type_id:values\.fee_type_id/);
});

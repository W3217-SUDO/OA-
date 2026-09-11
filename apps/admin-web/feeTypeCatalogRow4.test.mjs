import assert from "node:assert/strict";
import test from "node:test";
import { feeTypeTreeData, selectableFeeTypes } from "./src/feeTypeHierarchy.mjs";

const legacyCatalog = [
  { id: 1, code: "OFFICIAL", name: "官方费用", parent_code: "", base_fee_type: "官方费用", expense_scopes: ["律所", "平台"], is_active: true, selectable: false },
  { id: 2, code: "11010010", name: "差旅费", parent_code: "OFFICIAL", base_fee_type: "官方费用", expense_scopes: ["律所", "平台"], is_active: true, selectable: true },
  { id: 3, code: "INTERNAL", name: "内部费用", parent_code: "", base_fee_type: "内部费用", expense_scopes: ["内部"], is_active: true, selectable: false },
  { id: 4, code: "1104010", name: "产品购买费", parent_code: "INTERNAL", base_fee_type: "内部费用", expense_scopes: ["内部"], is_active: true, selectable: true },
];

test("legacy fee type leaves are available to all matching case-fee scopes", () => {
  assert.deepEqual(selectableFeeTypes(legacyCatalog, "律所").map((item) => item.name), ["差旅费"]);
  assert.deepEqual(selectableFeeTypes(legacyCatalog, "平台").map((item) => item.name), ["差旅费"]);
  assert.deepEqual(selectableFeeTypes(legacyCatalog, "内部").map((item) => item.name), ["产品购买费"]);
  const tree = feeTypeTreeData(legacyCatalog, "律所");
  assert.equal(tree[0].children[0].title, "差旅费");
});

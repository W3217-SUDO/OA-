import test from "node:test";
import assert from "node:assert/strict";
import { buildWarehouseLocationOptions, resolveCaseWarehouseLocationIds } from "./caseWarehouseLocationParity.mjs";

const catalog = [{
  id: 1,
  name: "上海一仓",
  is_active: true,
  locations: [
    { id: 11, name: "9-4", is_active: true },
    { id: 12, name: "停用位", is_active: false },
  ],
}, {
  id: 2,
  name: "停用仓",
  is_active: false,
  locations: [{ id: 21, name: "A-01", is_active: true }],
}];

test("warehouse location options contain only active master data", () => {
  assert.deepEqual(buildWarehouseLocationOptions(catalog), [{
    value: 11,
    label: "上海一仓（9-4）",
    warehouseId: 1,
    warehouseName: "上海一仓",
    locationName: "9-4",
  }]);
});

test("stored structured location ids take precedence", () => {
  assert.deepEqual(resolveCaseWarehouseLocationIds({ warehouse_location_ids: [11, "11"] }, buildWarehouseLocationOptions(catalog)), [11]);
});

test("legacy comma-separated warehouse text maps back to master locations", () => {
  assert.deepEqual(resolveCaseWarehouseLocationIds({ deposit_address: "上海一仓(9-4)" }, buildWarehouseLocationOptions(catalog)), [11]);
});

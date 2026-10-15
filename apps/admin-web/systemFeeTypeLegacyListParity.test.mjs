import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const constants = readFileSync(
  new URL("./src/system/constants.ts", import.meta.url),
  "utf8",
);
const page = readFileSync(
  new URL("./src/system/SystemParameterManagement.tsx", import.meta.url),
  "utf8",
);

test("fee type maintenance list uses legacy BAS_Case_FeeType rows", () => {
  assert.match(constants, /export function feeTypeLegacyRows\(rows: ParameterRow\[\]\)/);
  assert.match(constants, /row\.category === "fee_type"/);
  assert.match(constants, /row\.extra\.legacy_id !== undefined/);
  assert.match(constants, /row\.extra\.legacy_id !== null/);
  assert.match(page, /feeTypeLegacyRows\(parameters\)\.filter/);
});

test("legacy fee list keeps negative placeholder IDs visible to maintenance", () => {
  const helperStart = constants.indexOf("export function feeTypeLegacyRows");
  const helperEnd = constants.indexOf("export function feeTypeGroupOptions", helperStart);
  const helper = constants.slice(helperStart, helperEnd);
  const implementation = helper.replace(
    "export function feeTypeLegacyRows(rows: ParameterRow[]): ParameterRow[]",
    "function feeTypeLegacyRows(rows)",
  );
  const feeTypeLegacyRows = Function(`${implementation}; return feeTypeLegacyRows;`)();
  const rows = [
    { id: 1, category: "fee_type", code: "LEGACY-FEE-GROUP-1", name: "官费", extra: {}, sort_order: 1 },
    { id: 2, category: "fee_type", code: "LEGACY-FEE--100", name: "请选择官费", extra: { legacy_id: -100 }, sort_order: 2 },
    { id: 3, category: "fee_type", code: "LEGACY-FEE-11040030", name: "文书提成", extra: { legacy_id: 11040030 }, sort_order: 3 },
    { id: 4, category: "fee_type", code: "NEW-FEE", name: "临时费用", extra: {}, sort_order: 4 },
  ];
  assert.deepEqual(feeTypeLegacyRows(rows).map((row) => row.extra.legacy_id), [-100, 11040030]);
  assert.doesNotMatch(helper, /legacy_id\s*[<>]=?\s*0/);
});

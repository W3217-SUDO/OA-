import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

const sliceBetween = (text, startMarker, endMarker, label) => {
  const start = text.indexOf(startMarker);
  assert.notEqual(start, -1, label + " start marker should exist");
  const end = text.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, label + " end marker should exist");
  return text.slice(start, end);
};

const detailExportSource = sliceBetween(
  source,
  "  const exportContractDetailExcel = async (contract: Contract) => {",
  "  const needSelected =",
  "contract detail export helper",
);

const detailModalSource = sliceBetween(
  source,
  "      <Modal\n        width={isContractDetailView ? \"100%\" : 860}",
  "      <Modal open={Boolean(objectEditing)}",
  "contract detail modal",
);

test("contract detail restores the legacy ExportToExcel entry from ContractInfo", () => {
  assert.match(
    detailExportSource,
    /api\.get\(`\/contracts\/\$\{contract\.id\}\/export`, \{[\s\S]*responseType: "blob"/,
    "detail export should call the exact opened contract export endpoint",
  );
  assert.match(
    detailExportSource,
    /link\.download = \(contract\.serial_no \|\| contract\.title \|\| "合同详情"\) \+ "\.xls";/,
    "the downloaded detail export should be named from the opened contract",
  );
  assert.match(
    detailModalSource,
    /tabBarExtraContent=\{<Button onClick=\{\(\) => void exportContractDetailExcel\(viewing\)\}>导出Excel<\/Button>\}/,
    "the contract detail tab bar should expose the old 导出Excel action on the right",
  );
});

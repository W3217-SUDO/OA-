import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

const sliceBetween = (text, startMarker, endMarker, label) => {
  const start = text.indexOf(startMarker);
  assert.notEqual(start, -1, `${label} start marker should exist`);
  const end = text.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, `${label} end marker should exist`);
  return text.slice(start, end);
};

test("seal list exposes a direct legacy approval-flow shortcut", () => {
  const shortcutSource = sliceBetween(
    source,
    "  const openAuditList = async (row: SealRow) => {",
    "  const downloadAttachment",
    "approval flow shortcut",
  );
  const appColumnsSource = sliceBetween(
    source,
    "  const appColumns = [",
    "  const assetColumns = [",
    "seal list columns",
  );

  assert.match(
    shortcutSource,
    /await openDetail\(row\);[\s\S]*setAuditListOpen\(true\);/,
    "the shortcut should load the row detail history before opening the approval-flow modal",
  );
  assert.match(
    appColumnsSource,
    /onClick=\{\(\) => void openAuditList\(r\)\}[\s\S]*审批流程/,
    "each seal row should expose the legacy approval-flow modal directly from the list",
  );
});

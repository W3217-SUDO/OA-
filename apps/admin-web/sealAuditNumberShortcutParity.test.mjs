import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/SealCenterPage.tsx", import.meta.url), "utf8");

const sliceBetween = (text, startMarker, endMarker, label) => {
  const start = text.indexOf(startMarker);
  assert.notEqual(start, -1, `${label} start marker should exist`);
  const end = text.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, `${label} end marker should exist`);
  return text.slice(start, end);
};

const shortcutSource = sliceBetween(source, "  const openSealNumber = (row: SealRow) => {", "  const downloadAttachment", "seal number shortcut");
const appColumnsSource = sliceBetween(source, "  const appColumns = [", "  return (", "seal list columns");

test("seal audit number opens the approval modal like the legacy pending-audit list", () => {
  assert.match(
    shortcutSource,
    /tab === "audit" && canSealAction\("approve", row\)/,
    "audit list numbers should only shortcut when approval is actually allowed",
  );
  assert.match(
    shortcutSource,
    /setAction\(\{ type: "approve", row \}\);[\s\S]*actionForm\.resetFields\(\);[\s\S]*return;/,
    "allowed audit number clicks should open the approval modal directly",
  );
  assert.match(
    shortcutSource,
    /void openDetail\(row\);/,
    "non-audit or unauthorized number clicks should continue to open the detail page",
  );
  assert.match(
    appColumnsSource,
    /onClick=\{\(\) => openSealNumber\(r\)\}/,
    "the list number column should route through the legacy shortcut handler",
  );
});

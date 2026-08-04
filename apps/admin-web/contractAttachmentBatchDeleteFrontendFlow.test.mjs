import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

const sliceBetween = (source, startMarker, endMarker, label) => {
  const start = source.indexOf(startMarker);
  assert.notEqual(start, -1, label + " start marker should exist");
  const end = source.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, label + " end marker should exist");
  return source.slice(start, end);
};

const batchDeleteSource = sliceBetween(
  contractCenterSource,
  "  const batchDeleteViewingAttachments = async () => {",
  "  const submit = async () => {",
  "batchDeleteViewingAttachments",
);

const attachmentTabSource = sliceBetween(
  contractCenterSource,
  'key: "attachments",',
  'key: "approvals",',
  "contract detail attachment tab",
);

test("contract attachment batch delete warns on empty selection before calling the API", () => {
  assert.match(
    batchDeleteSource,
    /if \(!deletePlan\.length\) \{[\s\S]*message\.warning\("请先选择要删除的合同附件"\);[\s\S]*return;[\s\S]*\}/,
    "empty batch delete selection must show a user-visible warning instead of silently returning",
  );
});

test("contract attachment batch delete uses a confirmation step for the destructive action", () => {
  assert.match(
    batchDeleteSource,
    /Modal\.confirm\(\{[\s\S]*title:\s*"确认批量删除合同附件？"[\s\S]*okText:\s*"确认删除"[\s\S]*onOk:\s*async \(\) =>/,
    "batch delete must require explicit confirmation before deleting selected attachments",
  );
  assert.match(
    attachmentTabSource,
    /onClick=\{\(\) => void batchDeleteViewingAttachments\(\)\}/,
    "the batch delete button should route through the guarded confirmation handler",
  );
});

test("contract attachment batch delete preserves backend failure messages and failed selections", () => {
  assert.match(
    batchDeleteSource,
    /if \(summary\.failed\.length\) \{[\s\S]*message\.error\([\s\S]*summary\.failed\.map\(\(item\) => item\.message\)\.join\("；"\)[\s\S]*\);[\s\S]*return;[\s\S]*\}/,
    "any failed delete must surface the backend failure messages as an error",
  );
  assert.match(
    batchDeleteSource,
    /setSelectedAttachmentKeys\(summary\.failed\.map\(\(item\) => item\.id\)\.filter\(Boolean\)\);/,
    "failed attachment ids should remain selected so the user can see what did not delete",
  );
  assert.match(
    batchDeleteSource,
    /if \(summary\.deleted\) await reloadViewingAttachments\(target\);[\s\S]*setSelectedAttachmentKeys\(\[\]\);[\s\S]*message\.success/,
    "selection should only clear after a fully successful delete batch refreshes the attachment list",
  );
});

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

test("seal create queues local files and uploads them to the saved draft", () => {
  const createApplication = sliceBetween(
    source,
    "  const createApplication = async () => {",
    "  const openApplication = (row?: SealRow) => {",
    "seal create flow",
  );
  const createModalStart = source.indexOf("open={createOpen}");
  assert.notEqual(createModalStart, -1, "seal create modal should exist");
  const createModalEnd = source.indexOf("open={assetOpen}", createModalStart);
  assert.notEqual(createModalEnd, -1, "next modal should exist");
  const createModal = source.slice(createModalStart, createModalEnd);

  assert.match(
    source,
    /const \[pendingCreateFiles, setPendingCreateFiles\] = useState<File\[\]>\(\[\]\);/,
    "create/edit flow should retain files selected before a draft record exists",
  );
  assert.match(
    createApplication,
    /const savedApplication = response\.data as SealRow;[\s\S]*?uploadSealFiles\(pendingCreateFiles, savedApplication\)/,
    "the create response record id must drive the existing draft attachment upload endpoint",
  );
  assert.match(
    createApplication,
    /setPendingCreateFiles\(\[\]\);[\s\S]*?await openDetail\(savedApplication\);/,
    "successful queued-file creation should clear the queue and enter the draft detail",
  );
  assert.match(
    createModal,
    /<Upload[\s\S]*?multiple[\s\S]*?setPendingCreateFiles[\s\S]*?待上传附件/,
    "the create modal should expose multi-file selection and queued-file feedback before saving",
  );
  assert.match(
    source,
    /const uploadSealFiles = async \(files: File\[\], target: SealRow \| null = detail\)/,
    "queued files must reuse the existing persisted-draft upload handler instead of inventing a temporary endpoint",
  );
});

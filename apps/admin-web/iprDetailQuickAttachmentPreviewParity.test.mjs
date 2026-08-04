import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /\{attachments\.length\s*\?\s*attachments\.map\(\(item\) => \([\s\S]*?previewAttachment\(item\)[\s\S]*?downloadAttachment\(item\)[\s\S]*?\)\)\s*:\s*"暂无案件附件"\}/,
  "The IPR detail quick attachment list should offer both preview and download actions.",
);

console.log("ipr detail quick attachment preview parity: PASS");

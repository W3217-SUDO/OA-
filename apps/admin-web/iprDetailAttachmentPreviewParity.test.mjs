import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /const previewAttachment = async \(item: Attachment\) => \{[\s\S]*?window\.open\(/,
  "IPR detail attachments should have a preview action using the existing authorized blob endpoint.",
);

assert.match(
  center,
  /const previewAttachment = async \(item: Attachment\) => \{[\s\S]*?api\.get\(`\/attachments\/\$\{item\.id\}\/download`,[\s\S]*?responseType: "blob"/,
  "IPR attachment preview should reuse the existing authorized blob endpoint.",
);

assert.match(
  center,
  /dataIndex: "original_name",[\s\S]*?previewAttachment\(row\)[\s\S]*?downloadAttachment\(row\)/,
  "IPR detail attachment rows should expose both preview and download actions.",
);

console.log("ipr detail attachment preview parity: PASS");

import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /title: "回执文件",[\s\S]*?row\.receipt \? \([\s\S]*?previewAttachment\(row\.receipt!\)[\s\S]*?downloadAttachment\(row\.receipt!\)/,
  "IPR assisted-fee receipt rows should expose both legacy-style preview and download actions.",
);

console.log("ipr assisted-fee receipt preview parity: PASS");

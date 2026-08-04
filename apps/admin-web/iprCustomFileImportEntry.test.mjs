import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const importPage = fs.readFileSync(new URL("./src/IprCustomFileImportPage.tsx", import.meta.url), "utf8");

assert.match(app, /key: "ipr-custom-file-import", label:/);
assert.match(app, /route === "ipr-custom-file-import"/);
assert.match(importPage, /\/ipr\/case-files\/custom-import-batches/);
assert.match(importPage, /\/ipr\/case-files\/custom-import-candidates\/\$\{editing\.id\}/);
assert.match(
  center,
  /onNavigate\?\.\("ipr-custom-file-import"\)/,
  "IPR center toolbar should expose the existing custom case-file import page.",
);
assert.match(
  center,
  /<Button[^>]*onClick=\{\(\) => onNavigate\?\.\("ipr-custom-file-import"\)\}[^>]*>[\s\S]{1,80}<\/Button>/,
  "IPR center custom import entry should be a visible button, not only a hidden route.",
);

console.log("ipr custom file import entry: PASS");

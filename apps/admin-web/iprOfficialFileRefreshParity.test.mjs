import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");

assert.match(
  page,
  /<Button onClick=\{\(\)=>void load\(\)\}>刷新<\/Button>/,
  "The official-file toolbar should provide a refresh action that reloads the current server-side list.",
);

console.log("ipr official file refresh parity: PASS");

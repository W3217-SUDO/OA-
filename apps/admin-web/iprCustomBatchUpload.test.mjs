import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/IprCustomFileImportPage.tsx", import.meta.url), "utf8");
assert.match(source, /\/ipr\/cases\/files\/batch-upload/);
assert.match(source, /case_ids/);
assert.match(source, /跨案件批量上传/);
assert.match(source, /任一案件校验失败时整批不写入/);
assert.match(source, /至少选择一个在办案件/);
console.log("ipr custom batch upload: PASS");

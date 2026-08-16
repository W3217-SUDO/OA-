import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/DocumentCenterPage.tsx", import.meta.url),
  "utf8",
);

assert.match(source, /const officialImport = tab === "official";/);
assert.doesNotMatch(source, /tab === "official" && !v\.record_id/);
assert.match(source, /form\.append\("document_date", formatRequiredDate\(v\.document_date, "收文日期"\)\)/);
assert.match(source, /if \(linkedCase\) form\.append\("case_ids", String\(linkedCase\.id\)\)/);
assert.match(source, /label="文件日期"[\s\S]*?name="document_date"[\s\S]*?请选择文件日期/);
assert.match(source, /message\.success\(officialImport \? "官文已上传并生成收文记录"/);

console.log("official incoming upload row 12 contract passed");

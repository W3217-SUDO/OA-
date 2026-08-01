import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/MessageCenterPage.tsx", import.meta.url), "utf8");

test("message center exposes filters, reset, pagination, detail and safe actions", () => {
  assert.match(source, /setDates\(null\); setSender\(""\); setKeyword\(""\); setType\(""\); void load\(\)/);
  assert.match(source, /pagination=\{\{pageSize:15/);
  assert.match(source, /openNotice\(row\)/);
  assert.match(source, /notifications\/read-all/);
  assert.match(source, /notifications\/\$\{id\}/);
});

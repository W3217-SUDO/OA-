// 陶国南 11-04 调解协议书：可留空的字段不算缺；赔偿金额大写自动生成、不单独填；多个当事人逐行填。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const modal = fs.readFileSync(new URL("../src/legal/CaseWordTemplateModal.tsx", import.meta.url), "utf8");

test("可留空、自动生成、多行字段", () => {
  assert.match(modal, /filter\(field => !field\.optional && !field\.derived && !String\(edited\[field\.key\] \|\| ""\)\.trim\(\)\)/);
  assert.match(modal, /\(preview\?\.fields \|\| \[\]\)\.filter\(field => !field\.derived\)\.map/);
  assert.match(modal, /<Input value=\{field\.value\} disabled placeholder="随上面的金额自动生成，刷新预览后更新" \/>/);
  assert.match(modal, /<Input\.TextArea value=\{edited\[field\.key\]\} autoSize=\{\{ minRows: 2, maxRows: 6 \}\} placeholder="每位当事人一行"/);
});

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, "src", "HrCenterPage.tsx"), "utf8");

test("employee archive attachments keep the legacy explicit GO pagination action", () => {
  const start = source.indexOf("if(kind==='archive')");
  const end = source.indexOf("  const action=", start);
  assert.ok(start >= 0 && end > start, "employee archive branch should be present");
  const archiveBranch = source.slice(start, end);

  assert.match(archiveBranch, /onClick=\{\(\)=>void preview\(r\)\}/, "archive should keep its preview action");
  assert.match(archiveBranch, /onClick=\{\(\)=>void download\(r\)\}/, "archive should keep its download action");
  assert.match(archiveBranch, /showQuickJumper:\{goButton:'GO'\}/, "archive pagination should retain the legacy cPaging GO action");
});

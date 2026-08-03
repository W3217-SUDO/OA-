import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal detail exposes a separate read-only legacy audit list", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  const auditStart = source.indexOf('<Modal\n        open={auditListOpen}');
  const fileStart = source.indexOf('<Modal\n        open={fileListOpen}', auditStart);
  const auditSource = source.slice(auditStart, fileStart);

  assert.match(source, /const \[auditListOpen, setAuditListOpen\] = useState\(false\)/);
  assert.match(source, /<Button type="link" onClick=\{\(\) => setAuditListOpen\(true\)\}>\s*审核记录\s*<\/Button>/);
  assert.match(source, /title="审批流程"/);
  assert.match(source, /审批人/);
  assert.match(source, /审核状态/);
  assert.match(source, /审核日期/);
  assert.match(source, /审批意见/);
  assert.match(source, /审批轮次/);
  assert.match(auditSource, /pagination=\{false\}/);
  assert.doesNotMatch(auditSource, /pagination=\{sealFilePagination\}/);
});

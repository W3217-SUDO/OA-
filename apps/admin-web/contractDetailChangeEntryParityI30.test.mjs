import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract detail keeps the legacy change entry with the archive gate", () => {
  assert.match(source, /const detailSecondaryActionPolicy = contractSecondaryActionPolicy\(viewing\?\.status\);/);

  const detailFooterStart = source.indexOf("footer={<Space>{viewing?.status");
  const detailFooterEnd = source.indexOf("</Space>}", detailFooterStart);
  assert.ok(detailFooterStart >= 0 && detailFooterEnd > detailFooterStart);

  const detailFooter = source.slice(detailFooterStart, detailFooterEnd);
  assert.match(detailFooter, /detailSecondaryActionPolicy\.canEdit/);
  assert.match(detailFooter, /onClick=\{\(\) => openChange\(viewing\)\}/);
  assert.match(detailFooter, />\s*合同变更\s*<\/Button>/);
});

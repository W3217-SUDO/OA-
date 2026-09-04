import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const pageSource = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const cssSource = fs.readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");

test("9.1 row 2 keeps the complete generation menu outside the scrolling case detail", () => {
  assert.match(pageSource, /placement="bottomLeft"[\s\S]*autoAdjustOverflow=\{false\}/);
  assert.match(pageSource, /getPopupContainer=\{\(\) => document\.body\}/);
  assert.match(pageSource, /classNames=\{\{root:"case-document-generation-popup"\}\}/);
  assert.match(cssSource, /\.case-document-generation-popup\{[^}]*z-index:2400!important[^}]*max-height:calc\(100vh - 96px\)[^}]*overflow-y:auto/);
});

test("9.1 row 2 preserves every legacy generation action from first to last", async () => {
  const { getLegacyCaseDocumentGenerationItems } = await import("./src/caseDocumentGenerationActions.mjs");
  const labels = getLegacyCaseDocumentGenerationItems().map(([, label]) => label);

  assert.equal(labels.length, 11);
  assert.ok(labels.includes("生成鉴定函"));
  assert.equal(labels[0], "生成归档封面");
  assert.equal(labels.at(-1), "生成代收代付赔偿款申请单");
});

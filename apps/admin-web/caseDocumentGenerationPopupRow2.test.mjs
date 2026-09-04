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

test("9.1 row 2 preserves every legacy generation action, including Guangdong national-standard letters", async () => {
  const { getLegacyCaseDocumentGenerationItems } = await import("./src/caseDocumentGenerationActions.mjs");
  const items = getLegacyCaseDocumentGenerationItems();
  const labels = items.map(([, label]) => label);

  assert.equal(labels.length, 16);
  assert.equal(labels[0], "生成归档封面");
  assert.equal(labels.at(-1), "生成代收代付赔偿款申请单");
  assert.deepEqual(items.slice(7, 13), [
    ["gd-authorization-letter", "生成广东版授权委托书"],
    ["gd-first-instance-appellant-lawyer-letter", "生成广东版一审上诉人律师函"],
    ["gd-first-instance-appellee-lawyer-letter", "生成广东版一审被上诉人律师函"],
    ["gd-second-instance-appellant-lawyer-letter", "生成广东版二审上诉人律师函"],
    ["gd-second-instance-appellee-lawyer-letter", "生成广东版二审被上诉人律师函"],
    ["gd-execution-lawyer-letter", "生成广东版执行律师函"],
  ]);
});

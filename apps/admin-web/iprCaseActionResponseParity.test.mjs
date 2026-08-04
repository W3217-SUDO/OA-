import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helper = await import(new URL("./src/iprCaseWorkflowParity.mjs", import.meta.url));
const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

test("IPR action response preserves legacy IsSuccess failure envelopes", () => {
  assert.deepEqual(
    helper.normalizeIprCaseActionResponse({ data: { IsSuccess: false, Message: "legacy business failure" } }, "fallback success"),
    { ok: false, message: "legacy business failure" },
  );
  assert.deepEqual(
    helper.normalizeIprCaseActionResponse({ data: { IsSuccess: true, Message: "legacy ok" } }, "fallback success"),
    { ok: true, message: "legacy ok" },
  );
  assert.deepEqual(
    helper.normalizeIprCaseActionResponse({ data: { id: 8, status: "active" } }, "fallback success"),
    { ok: true, message: "fallback success" },
  );
  assert.equal(
    helper.getIprCaseActionErrorMessage({ response: { data: { Message: "legacy business failure" } } }, "fallback failure"),
    "legacy business failure",
  );
});

test("IPR status actions check normalized responses before refreshing", () => {
  assert.match(page, /normalizeIprCaseActionResponse/);
  assert.match(page, /getIprCaseActionErrorMessage/);
  assert.match(page, /if \(!actionResult\.ok\) throw new Error\(actionResult\.message\);/);
  assert.match(page, /message\.success\(actionResult\.message\)/);
});

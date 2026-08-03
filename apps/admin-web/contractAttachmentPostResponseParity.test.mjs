import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { normalizeContractActionResponse } from "./src/contractWorkflowPolicy.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("attachment PostResponse failure keeps the backend Message instead of showing success", () => {
  assert.deepEqual(
    normalizeContractActionResponse({ data: { IsSuccess: false, Message: "删除失败！" } }, "删除失败"),
    { ok: false, message: "删除失败！" },
  );
});

test("delete attachment checks the normalized action response before refreshing", () => {
  const start = contractCenterSource.indexOf("const deleteViewingAttachment = async");
  const end = contractCenterSource.indexOf("const submit = async", start);
  const handler = start >= 0 && end > start ? contractCenterSource.slice(start, end) : "";
  assert.match(handler, /normalizeContractActionResponse\(response/);
  assert.match(handler, /await openViewing\(viewing!/);
});

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("payment writeoff list exposes the guarded legacy refresh action", () => {
  assert.match(
    source,
    /initialView === "finance-payment-writeoff"\s*&&\s*\(\s*<Button\s+icon=\{<ReloadOutlined\s*\/>\}\s+disabled=\{contractPaymentSource\.active\}\s+onClick=\{\(\)\s*=>\s*void load\(\)\}\s*>\s*刷新\s*<\/Button>/,
  );
});

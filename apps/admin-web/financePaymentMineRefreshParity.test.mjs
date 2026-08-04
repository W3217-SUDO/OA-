import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("my payment and internal-fee lists expose the guarded legacy refresh action", () => {
  assert.match(
    source,
    /\[\s*"finance-payment-mine",\s*"finance-internal-mine",?\s*\]\.includes\(initialView\)\s*&&\s*\(\s*<Button\s+icon=\{<ReloadOutlined\s*\/>\}\s+disabled=\{contractPaymentSource\.active\}\s+onClick=\{\(\)\s*=>\s*void load\(\)\}\s*>\s*刷新\s*<\/Button>/,
  );
});

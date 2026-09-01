import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("row30 allocation validation remains visible inside the allocation modal", () => {
  assert.match(source, /const \[allocationValidationError, setAllocationValidationError\] = useState\(""\)/);
  assert.match(source, /setAllocationValidationError\(detail\);\s*message\.warning\(detail\)/);
  assert.match(source, /allocationValidationError && \(\s*<Alert[\s\S]*?type="error"[\s\S]*?message=\{allocationValidationError\}/);
});

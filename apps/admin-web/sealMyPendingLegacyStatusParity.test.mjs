import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("my pending maps only the legacy pending-approval status", () => {
  const source = fs.readFileSync("src/sealWorkflowPolicy.ts", "utf8");
  assert.match(
    source,
    /"seal-my-pending": \{ view: "my", statuses: \["\\u5f85\\u5ba1\\u6279"\] \}/,
  );
});

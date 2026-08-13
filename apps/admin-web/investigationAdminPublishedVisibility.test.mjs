import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  source,
  /initialTab === "investigation-task-published" && profile\.role !== "admin"/,
  "published investigation tasks must remain owner-scoped for ordinary users but visible to administrators",
);
assert.match(
  source,
  /initialTab === "investigation-task-sub-published"[\s\S]{0,100}profile\.role !== "admin"/,
  "published child-task view must preserve the same administrator exception",
);

console.log("PASS investigation administrator published-task visibility");

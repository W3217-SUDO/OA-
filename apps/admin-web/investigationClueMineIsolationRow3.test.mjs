import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const frontend = fs.readFileSync(
  new URL("./src/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);
const backend = fs.readFileSync(
  new URL("../api-server/app/main.py", import.meta.url),
  "utf8",
);

test("my investigation clues are isolated by their actual creator for every role", () => {
  assert.match(frontend, /if \(initialTab\.includes\("-my-"\)\)/);
  assert.doesNotMatch(
    frontend,
    /initialTab\.includes\("-my-"\) && profile\.role !== "admin"/,
  );
  assert.match(
    frontend,
    /row\.data\.publisher \|\|\s*row\.data\.imported_by \|\|\s*row\.owner/,
  );
});

test("new and imported clues persist the authenticated creator", () => {
  assert.match(
    backend,
    /payload\["data"\] = \{[^\n]+"publisher": identity\["username"\]\}/,
  );
  assert.match(
    backend,
    /"publisher": identity\["username"\], "imported_by": identity\["username"\]/,
  );
});

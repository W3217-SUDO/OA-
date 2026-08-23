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

test("my investigation clues isolate ordinary users while administrators retain full visibility", () => {
  assert.match(
    frontend,
    /initialTab\.includes\("-my-"\)\s*&&\s*profile\.role !== "admin"\s*&&\s*Boolean\(profile\.username\)/,
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

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const frontend = fs.readFileSync(
  new URL("./src/investigation/InvestigationCenterPage.tsx", import.meta.url),
  "utf8",
);
const backend = fs.readFileSync(
  new URL("../api-server/app/areas/investigation/router.py", import.meta.url),
  "utf8",
);

test("personal clues filter by current owner, not their publisher or importer", () => {
  assert.match(
    frontend,
    /initialTab\.includes\("-my-"\)\s*&&\s*Boolean\(profile\.username\)/,
  );
  assert.match(
    frontend,
    /String\(row\.owner \|\| ""\)\.toLocaleLowerCase\(\) ===\s*String\(profile\.username\)\.toLocaleLowerCase\(\)/,
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

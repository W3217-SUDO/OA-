import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/OrganizationCenterPage.tsx", import.meta.url), "utf8");

test("organization lists expose pagination and an add action when empty", () => {
  assert.equal((source.match(/pagination=\{\{/g) || []).length, 2);
  assert.match(source, /const emptyContent =/);
  assert.match(source, /\{canManageOrganization && \(/);
  assert.match(source, /api\.get\("\/hr\/departments"\)/);
  assert.match(source, /api\.get\("\/hr\/job-roles"\)/);
});

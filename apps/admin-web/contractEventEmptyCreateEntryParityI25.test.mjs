import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract event empty states retain the legacy create entry", () => {
  const eventSections = [...source.matchAll(/key: "events"/g)].map((match) => match.index ?? -1);
  assert.ok(eventSections.length >= 1);

  for (const start of eventSections) {
    const section = source.slice(start, start + 1800);
    assert.match(section, /暂无事项记录/);
    assert.match(section, /onClick=\{\(\) => viewing && void openContractEvent\(viewing\)\}/);
    assert.match(section, />新建<\/Button>/);
  }
});

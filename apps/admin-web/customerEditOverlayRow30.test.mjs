import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("row30 customer edit modal is not covered by the detail drawer", () => {
  assert.match(
    source,
    /<Drawer[\s\S]*?destroyOnHidden[\s\S]*?open=\{Boolean\(contacts\) && !editing && initialView !== "customer-new" && !detailPageOpen\}/,
  );
});

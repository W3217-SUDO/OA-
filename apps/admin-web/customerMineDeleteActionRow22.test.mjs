import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("row 22 my-customer menu exposes guarded customer deletion", () => {
  const mine = source.slice(source.indexOf('initialView === "customer-mine"'), source.indexOf(': initialView === "customer-dept"'));
  assert.match(mine, /key: "delete", label: "客户删除"/);
  assert.match(source, /if \(key === "delete"\) recycleCustomer\(target\)/);
  assert.match(source, /api\.post\(`\/customers\/\$\{row\.id\}\/recycle`/);
});

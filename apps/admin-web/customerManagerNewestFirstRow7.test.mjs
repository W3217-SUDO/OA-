import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /const prioritizeNewCustomerManagers = \(existing: string\[\], selected: string\[\]\)/);
assert.match(source, /const added = requested\.filter\(\(manager\) => !previous\.includes\(manager\)\)/);
assert.match(source, /return \[\.\.\.added\.reverse\(\), \.\.\.retained\]/);
assert.match(source, /getValueFromEvent=\{\(selected: string\[\]\) => prioritizeNewCustomerManagers/);

console.log("customer manager newest-first row 7 frontend contract passed");

import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /name="assistants"><Select mode="multiple"/);
assert.match(source, /assistant_usernames \|\| row\.data\.assistants/);
assert.match(source, /const added=selected\.filter\(value=>!previous\.includes\(value\)\)/);
assert.match(source, /\[\.\.\.added\.reverse\(\),\.\.\.selected\.filter\(value=>previous\.includes\(value\)\)\]/);

console.log("case multiple assistants row 5 frontend contract passed");

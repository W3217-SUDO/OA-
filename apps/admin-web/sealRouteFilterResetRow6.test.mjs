import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/SealCenterPage.tsx", import.meta.url),
  "utf8",
);

const routeEffect = source.slice(
  source.indexOf("useEffect(() => {\n    setTab(tabFromView(initialView));"),
  source.indexOf("useEffect(() => {\n    setSelectedKeys([]);"),
);

assert.match(routeEffect, /queryForm\.resetFields\(\);/);
assert.match(routeEffect, /setQuery\(\{\}\);/);
assert.match(routeEffect, /\[initialView, queryForm\]/);

console.log("seal route filter reset row 6 frontend contract passed");

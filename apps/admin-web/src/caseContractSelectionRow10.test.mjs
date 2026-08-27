import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./CaseCenterPage.tsx", import.meta.url), "utf8");

assert.doesNotMatch(source, /disabled=\{initialView !== "case-new" \|\| Boolean\(contractPrefill\?\.id\)\}/);
assert.match(source, /disabled=\{Boolean\(contractPrefill\?\.id\) \|\| !String\(createCustomer \|\| ""\)\.trim\(\)\}/);
assert.match(source, /buildCaseContractOptions\(contracts, contractPrefill, createCustomer\)/);
assert.match(source, /onChange=\{\(\)=>createForm\.setFieldsValue\(\{contract_record_id:undefined,source_person:undefined,title:undefined\}\)\}/);

for (const routeType of ["criminal", "administrative", "counsel", "arbitration"]) {
  assert.match(source, new RegExp(`initialView\\.endsWith\\("${routeType}"\\)`));
}

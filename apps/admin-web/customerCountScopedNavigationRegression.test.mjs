import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const contractPage = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");
const casePage = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const iprPage = await readFile(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");
const customerPage = await readFile(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer count links keep customer-scoped contract query after route reset", () => {
  assert.match(contractPage, /customerRelationQueryRef/);
  assert.match(contractPage, /const relationQuery = consumedRelationQuery \|\| customerRelationQueryRef\.current/);
  assert.match(contractPage, /customerRelationQueryRef\.current = effectiveQuery;/);
  assert.match(contractPage, /const relationQuery = customerRelationQueryRef\.current;[\s\S]*setQuery\(relationQuery\);[\s\S]*return;[\s\S]*const savedQuery = readContractQuery\(initialView\)/);
});

test("customer contract count opens the matching contract list scope", async () => {
  assert.match(customerPage, /initialView === "customer-mine"[\s\S]*\? "contract-mine"/);
  assert.match(customerPage, /\["customer-dept", "customer-dept-recycle"\]\.includes\(initialView\)[\s\S]*\? "contract-dept"/);
  assert.match(customerPage, /: "contract-company";[\s\S]*onNavigate\?\.\(targetView\)/);
  assert.doesNotMatch(customerPage, /rememberCustomerRelationTarget\(\{ id: customer\.id,[\s\S]*target: "contracts" \}\);\s*onNavigate\?\.\("contract-company"\)/);
});

test("customer civil-case count link is not overwritten by stale case-list return query", () => {
  assert.match(customerPage, /const openCustomerCivilCases[\s\S]*initialView === "customer-mine"[\s\S]*\? "case-mine"/);
  assert.match(customerPage, /const openCustomerCivilCases[\s\S]*\["customer-dept", "customer-dept-recycle"\]\.includes\(initialView\)[\s\S]*\? "case-dept"/);
  assert.match(customerPage, /const openCustomerCivilCases[\s\S]*: "case-company";[\s\S]*onNavigate\?\.\(targetView\)/);
  assert.doesNotMatch(customerPage, /onNavigate\?\.\("case-company-civil"\)/);
  assert.match(casePage, /customer_id: relationTarget\.id/);
  assert.match(casePage, /customer_no: relationTarget\.serial_no/);
  assert.match(casePage, /if \(!relationQuery\.customer_id && !relationQuery\.customer_no && !relationQuery\.customer/);
  assert.match(casePage, /sessionStorage\.removeItem\("sunhold:case-list-return"\);[\s\S]*return raw \? JSON\.parse\(raw\) : null/);
});

test("customer ipr-case count link initializes the ipr list with the relation customer keyword", () => {
  assert.match(iprPage, /CUSTOMER_IPR_RELATION_STORAGE_KEY = "sunhold:customer-ipr-relation"/);
  assert.match(iprPage, /return String\(parsed\.title \|\| parsed\.serial_no \|\| ""\)\.trim\(\)/);
  assert.match(iprPage, /const relationKeyword = consumeCustomerIprRelationKeyword\(\);[\s\S]*setKeyword\(relationKeyword\);[\s\S]*void load\(1, pageSize, relationKeyword \|\| keyword\)/);
});

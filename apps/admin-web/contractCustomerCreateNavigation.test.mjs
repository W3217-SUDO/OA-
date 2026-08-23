import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import { buildContractCustomerQueryFromRelation, openContractCustomerCreation } from "./src/contractCenterCustomerNavigation.ts";

const pageSource = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract customer shortcut opens the existing customer creation page", () => {
  let navigatedTo = "";

  const opened = openContractCustomerCreation((target) => {
    navigatedTo = target;
  });

  assert.equal(opened, true);
  assert.equal(navigatedTo, "customer-new");
});

test("contract customer shortcut stays inert when routing is unavailable", () => {
  assert.equal(openContractCustomerCreation(undefined), false);
});

test("customer-to-contract relation target is converted before the first contract list request", () => {
  const query = buildContractCustomerQueryFromRelation({
    id: 101,
    serial_no: "CUS-2026-001",
    title: "Acme Legal",
    target: "contracts",
  });

  assert.deepEqual(query, {
    customer_id: 101,
    customer_no: "CUS-2026-001",
    customer: "Acme Legal",
    exclude_archived: true,
  });
});

test("customer-to-contract relation uses the customer name and ignores non-contract targets", () => {
  assert.deepEqual(buildContractCustomerQueryFromRelation({ serial_no: "CUS-2026-002", target: "contracts" }), {
    customer_id: undefined,
    customer_no: "CUS-2026-002",
    customer: undefined,
    exclude_archived: true,
  });
  assert.equal(buildContractCustomerQueryFromRelation({ title: "Acme Legal", target: "civil-cases" }), null);
});

test("customer-to-contract relation filters by exact identity and hides archived contracts", () => {
  assert.match(pageSource, /if \(query\.customer_id\)/);
  assert.match(pageSource, /Number\(x\.data\.customer_id\) === Number\(query\.customer_id\)/);
  assert.match(pageSource, /else if \(query\.customer\)/);
  assert.match(pageSource, /text\(x\.customer\)\.includes\(text\(query\.customer\)\)/);
  assert.match(pageSource, /query\.exclude_archived/);
});

test("customer-to-contract relation survives duplicate page initialization but resets for a manual query", () => {
  assert.match(pageSource, /const relationQuery = consumedRelationQuery \|\| customerRelationQueryRef\.current/);
  assert.match(pageSource, /\{ \.\.\.baseQuery, customer_id: undefined, customer_no: "", customer: "", \.\.\.relationQuery \}/);
  assert.match(pageSource, /customerRelationQueryViewRef\.current !== initialView/);
  assert.match(pageSource, /customerRelationQueryRef\.current = null;\s*customerRelationQueryViewRef\.current = null;/);
});

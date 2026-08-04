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

  assert.deepEqual(query, { customer: "Acme Legal", customer_no: "CUS-2026-001", exclude_archived: true });
});

test("customer-to-contract relation keeps the legacy customerNo filter and ignores non-contract targets", () => {
  assert.deepEqual(buildContractCustomerQueryFromRelation({ serial_no: "CUS-2026-002", target: "contracts" }), {
    customer: "CUS-2026-002",
    customer_no: "CUS-2026-002",
    exclude_archived: true,
  });
  assert.equal(buildContractCustomerQueryFromRelation({ title: "Acme Legal", target: "civil-cases" }), null);
});

test("customer-to-contract relation filters by stable customer number and hides archived contracts", () => {
  assert.match(pageSource, /query\.customer_no/);
  assert.match(pageSource, /x\.data\.customer_no/);
  assert.match(pageSource, /text\(x\.data\.customer_no\) === text\(query\.customer_no\)/);
  assert.match(pageSource, /query\.exclude_archived/);
  assert.match(pageSource, /已归档/);
});

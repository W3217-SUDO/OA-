import assert from "node:assert/strict";
import test from "node:test";

import { buildContractCustomerQueryFromRelation, openContractCustomerCreation } from "./src/contractCenterCustomerNavigation.ts";

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

  assert.deepEqual(query, { customer: "Acme Legal" });
});

test("customer-to-contract relation falls back to customer number and ignores non-contract targets", () => {
  assert.deepEqual(buildContractCustomerQueryFromRelation({ serial_no: "CUS-2026-002", target: "contracts" }), {
    customer: "CUS-2026-002",
  });
  assert.equal(buildContractCustomerQueryFromRelation({ title: "Acme Legal", target: "civil-cases" }), null);
});

import assert from "node:assert/strict";
import test from "node:test";

import { openContractCustomerCreation } from "./src/contractCenterCustomerNavigation.ts";

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

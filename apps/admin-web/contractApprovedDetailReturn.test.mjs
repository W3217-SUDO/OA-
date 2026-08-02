import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(
  new URL("./src/ContractCenterPage.tsx", import.meta.url),
  "utf8",
);

test("approved-contract detail remembers and consumes its source list on close", () => {
  assert.match(
    source,
    /sessionStorage\.setItem\(CONTRACT_DETAIL_RETURN_VIEW_STORAGE_KEY, initialView\)/,
    "opening a detail must retain the exact source list",
  );
  assert.match(
    source,
    /onNavigate\?\.\(consumeContractDetailReturnView\(\)\)/,
    "closing a detail must return to its retained source list",
  );
  assert.doesNotMatch(
    source,
    /isContractDetailView \? onNavigate\?\.\("contract-mine"\)/,
    "detail close must not always route to my contracts",
  );
});

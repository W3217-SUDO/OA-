import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract investigation uploads use the investigation material whitelist category", () => {
  const createInvestigation = source.slice(
    source.indexOf("const createInvestigation = async"),
    source.indexOf("const openContractPayment"),
  );
  assert.match(createInvestigation, /attachment\.append\("category", "调查资料"\)/);
  assert.doesNotMatch(createInvestigation, /调查任务资料/);
});

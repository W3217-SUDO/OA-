import assert from "node:assert/strict";
import test from "node:test";

import { buildContractListRequestParams } from "./src/contractWorkflowPolicy.mjs";


test("contract list sends contract number and keyword fields to the records API", () => {
  const params = buildContractListRequestParams(
    "contract-mine",
    { current: 3, pageSize: 15 },
    { serial_no: " SHHT2610061 ", title: " 目标商标 ", customer: " 目标客户 " },
  );

  assert.equal(params.module, "contract");
  assert.equal(params.scope, "mine");
  assert.equal(params.page, 3);
  assert.equal(params.serial_no, "SHHT2610061");
  assert.equal(params.title, "目标商标");
  assert.equal(params.customer, "目标客户");
});

test("a new search keeps page size but returns to the first page", () => {
  const params = buildContractListRequestParams(
    "contract-mine",
    { current: 1, pageSize: 50 },
    { serial_no: "2610061" },
  );
  assert.equal(params.page, 1);
  assert.equal(params.page_size, 50);
});

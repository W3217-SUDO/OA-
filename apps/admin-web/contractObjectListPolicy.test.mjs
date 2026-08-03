import test from "node:test";
import assert from "node:assert/strict";
import {
  CONTRACT_OBJECT_DEFAULT_PAGE_SIZE,
  CONTRACT_OBJECT_PAGE_SIZES,
  paginateContractObjectRows,
  sortContractObjectRows,
  sortContractRecordRows,
} from "./src/contractObjectListPolicy.mjs";

test("contract object list keeps the legacy ten-row default and page-size choices", () => {
  assert.equal(CONTRACT_OBJECT_DEFAULT_PAGE_SIZE, 10);
  assert.deepEqual(CONTRACT_OBJECT_PAGE_SIZES, [10, 15, 20, 50, 100, 200]);
});

test("contract object rows follow legacy case and fee descending order", () => {
  const rows = [
    { id: 1, case_record_id: 8, case_office_fee_id: 2 },
    { id: 2, case_record_id: 9, case_office_fee_id: 1 },
    { id: 3, case_record_id: 9, case_office_fee_id: 3 },
    { id: 4, case_record_id: 9, case_office_fee_id: 3 },
  ];
  assert.deepEqual(sortContractObjectRows(rows).map((row) => row.id), [4, 3, 2, 1]);
  assert.deepEqual(rows.map((row) => row.id), [1, 2, 3, 4]);
});

test("contract payment, invoice and receipt rows follow legacy ascending IDs", () => {
  const rows = [{ id: 8 }, { id: 2 }, { id: 5 }];
  assert.deepEqual(sortContractRecordRows(rows).map((row) => row.id), [2, 5, 8]);
});

test("contract object pagination clamps invalid pages and preserves total", () => {
  const rows = Array.from({ length: 23 }, (_, index) => ({ id: index + 1 }));
  assert.deepEqual(paginateContractObjectRows(rows, 2, 10), {
    items: rows.slice(10, 20),
    current: 2,
    pageSize: 10,
    total: 23,
  });
  assert.deepEqual(paginateContractObjectRows(rows, 99, 15), {
    items: rows.slice(15, 23),
    current: 2,
    pageSize: 15,
    total: 23,
  });
});

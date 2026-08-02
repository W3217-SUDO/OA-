import assert from "node:assert/strict";
import test from "node:test";

import { readContractListPagination, saveContractListPagination } from "./src/contractListPagination.mjs";

const storage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
  };
};

test("contract audit list views use the legacy twenty-row default without leaking to normal lists", () => {
  const memory = storage();
  for (const view of ["contract-audit", "contract-audit-pending", "contract-audit-refused", "contract-audit-approved"]) {
    assert.deepEqual(readContractListPagination(memory, view), { current: 1, pageSize: 20 });
    assert.deepEqual(saveContractListPagination(memory, view, { current: 2, pageSize: 20 }), { current: 2, pageSize: 20 });
  }
  assert.deepEqual(readContractListPagination(memory, "contract-mine"), { current: 1, pageSize: 15 });
  assert.deepEqual(saveContractListPagination(memory, "contract-mine", { current: 1, pageSize: 200 }), { current: 1, pageSize: 200 });
});

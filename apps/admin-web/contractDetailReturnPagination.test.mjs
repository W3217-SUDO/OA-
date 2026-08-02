import assert from "node:assert/strict";
import test from "node:test";

import {
  readContractListPagination,
  saveContractListPagination,
} from "./src/contractListPagination.ts";

const memoryStorage = () => {
  const values = new Map();
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
};

test("contract list restores the selected page and page size after detail return", () => {
  const storage = memoryStorage();

  saveContractListPagination(storage, "contract-mine", {
    current: 3,
    pageSize: 10,
  });

  assert.deepEqual(readContractListPagination(storage, "contract-mine"), {
    current: 3,
    pageSize: 10,
  });
});

test("contract list pagination remains isolated between list views", () => {
  const storage = memoryStorage();

  saveContractListPagination(storage, "contract-mine", {
    current: 2,
    pageSize: 20,
  });

  assert.deepEqual(readContractListPagination(storage, "contract-dept"), {
    current: 1,
    pageSize: 15,
  });
});

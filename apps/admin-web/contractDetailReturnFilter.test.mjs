import assert from "node:assert/strict";
import test from "node:test";

import {
  readContractListQuery,
  saveContractListQuery,
} from "./src/contractListQuery.ts";

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

test("contract list query survives detail return without leaking into approval", () => {
  const storage = memoryStorage();

  saveContractListQuery(storage, "contract-mine", {
    serial_no: "SHHT2610035",
    customer: "test",
  });

  assert.deepEqual(readContractListQuery(storage, "contract-mine"), {
    serial_no: "SHHT2610035",
    customer: "test",
  });
  assert.deepEqual(readContractListQuery(storage, "contract-audit-pending"), {});
});

test("each contract list restores only its own query", () => {
  const storage = memoryStorage();

  saveContractListQuery(storage, "contract-mine", { serial_no: "SHHT2610035" });
  saveContractListQuery(storage, "contract-audit-pending", { customer: "待审批客户" });

  assert.deepEqual(readContractListQuery(storage, "contract-mine"), {
    serial_no: "SHHT2610035",
  });
  assert.deepEqual(readContractListQuery(storage, "contract-audit-pending"), {
    customer: "待审批客户",
  });
});

import assert from "node:assert/strict";
import test from "node:test";

import dayjs from "dayjs";

import {
  createContractCustomerContextConsumer,
  createContractNumber,
} from "./src/contractCreateContext.ts";

const memoryStorage = (initial = {}) => {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    removeItem(key) {
      values.delete(key);
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
};

test("new contracts receive an HT timestamp number instead of an unexplained 99", () => {
  assert.equal(
    createContractNumber(dayjs("2026-08-02T12:34:56")),
    "HT20260802123456",
  );
});

test("customer prefill survives duplicate contract-new initialization", () => {
  const storage = memoryStorage({
    "sunhold:contract-customer": JSON.stringify({
      id: 13,
      name: "test",
      serial_no: "SHKH1810649",
      at: Date.parse("2026-08-02T12:00:00Z"),
    }),
  });
  const consumer = createContractCustomerContextConsumer(
    storage,
    () => Date.parse("2026-08-02T12:05:00Z"),
  );

  const expected = {
    id: 13,
    name: "test",
    serial_no: "SHKH1810649",
    at: Date.parse("2026-08-02T12:00:00Z"),
  };

  assert.deepEqual(consumer.consume(), expected);
  assert.equal(storage.getItem("sunhold:contract-customer"), null);
  assert.deepEqual(consumer.consume(), expected);
});

test("reset allows a later customer source to replace the cached prefill", () => {
  const storage = memoryStorage();
  const consumer = createContractCustomerContextConsumer(storage);

  assert.equal(consumer.consume(), null);
  storage.setItem(
    "sunhold:contract-customer",
    JSON.stringify({ id: 27, name: "第二客户", serial_no: "SHKH2600027" }),
  );
  consumer.reset();

  assert.deepEqual(consumer.consume(), {
    id: 27,
    name: "第二客户",
    serial_no: "SHKH2600027",
    at: 0,
  });
});

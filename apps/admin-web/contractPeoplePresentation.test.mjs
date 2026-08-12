import test from "node:test";
import assert from "node:assert/strict";
import {
  PERSON_NAME_PLACEHOLDER,
  buildChinesePersonOptions,
  displayChinesePersonName,
  displayChinesePersonNames,
  isChinesePersonName,
} from "./src/contractPeoplePresentation.mjs";

test("contract approver options keep unique recorded person names", () => {
  const options = buildChinesePersonOptions([
    { username: "zhangsan", display_name: "张三", can_approve_contract: true },
    { username: "ceshi", display_name: "测试2", can_approve_contract: true },
    { username: "job-title", display_name: "范围经理", can_approve_contract: true },
    { username: "missing-name", display_name: "", can_approve_contract: true },
    { username: "lisi-one", display_name: "李四", can_approve_contract: true },
    { username: "lisi-two", display_name: "李四", can_approve_contract: true },
  ], (user) => user.can_approve_contract);

  assert.deepEqual(options, [
    { value: "zhangsan", label: "张三" },
    { value: "ceshi", label: "测试2" },
    { value: "job-title", label: "范围经理" },
  ]);
  assert.equal(isChinesePersonName("张三"), true);
  assert.equal(isChinesePersonName("测试2"), true);
  assert.equal(isChinesePersonName("范围经理"), true);
  assert.equal(isChinesePersonName("alice"), false);
});

test("contract and customer people hide unregistered account identifiers", () => {
  const directory = [{ username: "zhangsan", display_name: "张三" }];

  assert.equal(displayChinesePersonName("zhangsan", directory), "张三");
  assert.equal(displayChinesePersonName("alice", directory), PERSON_NAME_PLACEHOLDER);
  assert.equal(displayChinesePersonNames(["zhangsan", "alice"], directory), `张三、${PERSON_NAME_PLACEHOLDER}`);
});

test("customer people options accept every non-empty system display name", () => {
  const options = buildChinesePersonOptions(
    [
      { username: "alice-account", display_name: "Alice Smith", eligible_customer_person: true },
      { username: "range-manager", display_name: "范围经理员工", eligible_customer_person: true },
      { username: "login-only", display_name: "login-only", eligible_customer_person: true },
    ],
    (user) => user.eligible_customer_person,
    { allowNonChinese: true },
  );

  assert.deepEqual(options, [
    { value: "alice-account", label: "Alice Smith" },
    { value: "range-manager", label: "范围经理员工" },
    { value: "login-only", label: "login-only" },
  ]);
});

test("legacy option flags cannot invalidate a stored English display name", () => {
  assert.deepEqual(
    buildChinesePersonOptions(
      [{ username: "fwl", display_name: "fwl" }],
      () => true,
      { allowNonChinese: false },
    ),
    [{ value: "fwl", label: "fwl" }],
  );
});

test("person display accepts English names and names identical to usernames", () => {
  const directory = [
    { username: "alice-account", display_name: "Alice Smith" },
    { username: "fwl", display_name: "fwl" },
    { username: "missing", display_name: "" },
  ];

  assert.equal(displayChinesePersonName("alice-account", directory), "Alice Smith");
  assert.equal(displayChinesePersonName("Alice Smith", directory), "Alice Smith");
  assert.equal(displayChinesePersonName("fwl", directory), "fwl");
  assert.equal(displayChinesePersonName("missing", directory), PERSON_NAME_PLACEHOLDER);
  assert.equal(displayChinesePersonName("alice", directory), PERSON_NAME_PLACEHOLDER);
});

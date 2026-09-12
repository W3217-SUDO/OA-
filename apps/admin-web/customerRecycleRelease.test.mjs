import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";
import { buildCustomerActionRequest } from "./src/customerParity.mjs";
import { assertCustomerMutationSuccess } from "./src/customerUiBatchI17.mjs";

const source = fs.readFileSync(new URL("./src/crm/CustomerCenterPage.tsx", import.meta.url), "utf8");
const tree = ts.createSourceFile("CustomerCenterPage.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const handlers = {};
function visit(node) {
  if (ts.isVariableDeclaration(node) && ["action", "originalActionItems"].includes(node.name.getText(tree))) {
    handlers[node.name.getText(tree)] = node.initializer.getText(tree);
  }
  ts.forEachChild(node, visit);
}
visit(tree);
assert.ok(handlers.action && handlers.originalActionItems);
const compile = expression => ts.transpileModule(`const run = ${expression};`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;

for (const route of ["customer-recycle", "customer-dept-recycle", "customer-company-recycle"]) {
  test(`${route} keeps release next to restore`, () => {
    const items = new Function("initialView", "profile", `${compile(handlers.originalActionItems)}; return run;`)(route, { role: "user" });
    assert.deepEqual(items.map(item => item.key), ["restore", "release"]);
    assert.equal(items[1].label, "进入公海");
  });
}

function setup(data, networkError = false) {
  const requests = [], changes = [], messages = [];
  const message = Object.fromEntries(["success", "error"].map(level => [level, value => messages.push([level, value])]));
  const run = new Function("buildCustomerActionRequest", "api", "assertCustomerMutationSuccess", "message", "getCustomerActionMessage", "setSelectedRowKeys", "load", "getCustomerMutationErrorMessageI17", `${compile(handlers.action)}; return run;`)(
    buildCustomerActionRequest,
    { post: async (url, body) => { requests.push([url, body]); if (networkError) throw Error("network"); return { data }; } },
    assertCustomerMutationSuccess, message, (action, success) => `${action}:${success}`,
    value => changes.push(["selection", value]), async () => changes.push(["reload"]), (_, fallback) => fallback,
  );
  return { run, requests, changes, messages };
}

test("release sends chosen customer and refreshes only on successful response", async () => {
  const state = setup({ id: 23, status: "公海" });
  await state.run({ id: 23 }, "release");
  assert.equal(state.requests[0][0], "/customers/23/release");
  assert.deepEqual(state.changes, [["selection", []], ["reload"]]);
  assert.deepEqual(state.messages, [["success", "release:true"]]);
});

for (const networkError of [false, true]) {
  test(`release rejection preserves selection; network=${networkError}`, async () => {
    const state = setup({ IsSuccess: false, Message: "blocked" }, networkError);
    await state.run({ id: 23 }, "release");
    assert.deepEqual(state.changes, []);
    assert.equal(state.messages.length, 1);
    assert.equal(state.messages[0][0], "error");
  });
}

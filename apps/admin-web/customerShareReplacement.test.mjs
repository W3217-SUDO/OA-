import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";
import { buildCustomerShareRequest } from "./src/customerUiBatchI14.mjs";

test("explicit empty selection cancels sharing; missing or blank input cannot", () => {
  assert.deepEqual(buildCustomerShareRequest(12, [], "cancel"), {
    method: "post", url: "/customers/12/share", data: { recipients: [], comment: "cancel" },
  });
  for (const value of [undefined, null, "", [" ", ""]]) assert.equal(buildCustomerShareRequest(12, value), null);
  assert.equal(buildCustomerShareRequest(undefined, []), null);
  assert.deepEqual(buildCustomerShareRequest(12, [" share-two ", "share-two"]).data.recipients, ["share-two"]);
});

const source = fs.readFileSync(new URL("./src/crm/CustomerCenterPage.tsx", import.meta.url), "utf8");
const tree = ts.createSourceFile("CustomerCenterPage.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let handler;
function visit(node) {
  if (ts.isVariableDeclaration(node) && node.name.getText(tree) === "share") handler = node.initializer.getText(tree);
  ts.forEachChild(node, visit);
}
visit(tree);
assert.ok(handler);
const compiled = ts.transpileModule(`const run = ${handler};`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;

function setup(recipients, failed = false) {
  const requests = [], messages = [], changes = [];
  const message = Object.fromEntries(["success", "warning", "error"].map(level => [level, text => messages.push([level, text])]));
  const run = new Function("sharing", "shareForm", "buildCustomerShareRequest", "api", "assertCustomerMutationSuccess", "message", "setSharing", "setSelectedRowKeys", "load", "getCustomerMutationErrorMessageI17", `${compiled}; return run;`)(
    { id: 12 }, { validateFields: async () => ({ recipients, comment: "CODEX" }) }, buildCustomerShareRequest,
    { post: async (url, body) => { requests.push([url, body]); return { data: { IsSuccess: !failed } }; } },
    data => { if (!data.IsSuccess) throw Error("denied"); }, message,
    value => changes.push(["modal", value]), value => changes.push(["selection", value]),
    async () => changes.push(["reload"]), (_, fallback) => fallback,
  );
  return { run, requests, messages, changes };
}

test("save sends the current reduced selection, then closes and refreshes", async () => {
  const state = setup(["share-two"]);
  await state.run();
  assert.deepEqual(state.requests, [["/customers/12/share", { recipients: ["share-two"], comment: "CODEX" }]]);
  assert.deepEqual(state.changes, [["modal", null], ["selection", []], ["reload"]]);
});

test("clearing all recipients reaches API and reports cancelled sharing", async () => {
  const state = setup([]);
  await state.run();
  assert.deepEqual(state.requests[0][1].recipients, []);
  assert.deepEqual(state.messages, [["success", "已取消客户共享"]]);
});

test("business rejection preserves modal and does not claim success", async () => {
  const state = setup([], true);
  await state.run();
  assert.equal(state.changes.length, 0);
  assert.equal(state.messages[0][0], "error");
});

test("shared personnel control allows empty selection and has a save action", () => {
  const modal = fs.readFileSync(new URL("./src/crm/CustomerModals.tsx", import.meta.url), "utf8");
  const section = modal.slice(modal.indexOf("{/* 共享客户 Modal */}"));
  assert.match(section, /okText="保存共享设置"/);
  assert.match(section, /name="recipients"/);
  assert.doesNotMatch(section, /required:\s*true/);
});

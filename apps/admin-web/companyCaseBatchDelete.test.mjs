import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = fs.readFileSync(new URL("./src/legal/services/workflowActions.tsx", import.meta.url), "utf8");
const tree = ts.createSourceFile("workflowActions.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let handler;
function visit(node) {
  if (ts.isVariableDeclaration(node) && node.name.getText(tree) === "deleteCompanyCase") handler = node.initializer.getText(tree);
  ts.forEachChild(node, visit);
}
visit(tree);
assert.ok(handler);
const compiled = ts.transpileModule(`const run = ${handler};`, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;

function setup(options = {}) {
  const requests = [], messages = [], selection = [], refreshes = [];
  let modal;
  const context = {
    initialView: "case-company-civil", selectedCaseKeys: [1, 2],
    getCaseCapability: (row) => ({ can_delete_case: row.allowed !== false }),
    setSelectedCaseKeys: (keys) => selection.push(keys),
    caseQuery: { keyword: "CODEX" }, originalPage: 2, originalPageSize: 15,
    counselPage: 3, counselPageSize: 20, counselListMode: false,
    loadOrdinaryCases: async (...args) => { refreshes.push(["ordinary", ...args]); if (options.refreshError) throw Error("refresh"); },
    loadCounselCases: async (...args) => refreshes.push(["counsel", ...args]),
    ...options.context,
  };
  const api = { post: async (url, body) => { requests.push([url, body]); if (options.apiError) throw Error("failure"); return { data: { deleted: body.case_ids.length, cleanup_pending: options.cleanupPending || 0 } }; } };
  const message = Object.fromEntries(["success", "warning", "error"].map((level) => [level, (text) => messages.push([level, text])]));
  const run = new Function("context", "api", "Modal", "message", "isCompanyCaseListRoute", `${compiled}; return run;`)(
    context, api, { confirm: (value) => { modal = value; } }, message, (route) => route.startsWith("case-company"),
  );
  return { run, requests, messages, selection, refreshes, get modal() { return modal; } };
}

test("complete selection reaches one batch request only after confirmation", async () => {
  const state = setup();
  await state.run([{ id: 1 }, { id: 2 }]);
  assert.match(state.modal.content, /2 条案件/);
  assert.equal(state.requests.length, 0);
  await state.modal.onOk();
  assert.deepEqual(state.requests, [["/cases/batch-delete", { case_ids: [1, 2] }]]);
  assert.deepEqual(state.selection, [[]]);
  assert.deepEqual(state.refreshes, [["ordinary", { keyword: "CODEX" }, 2, 15]]);
});

test("empty, stale, denied and non-company selections never open confirmation", async () => {
  for (const [rows, context] of [
    [[], {}], [[{ id: 1 }], {}], [[{ id: 1 }, { id: 3 }], {}],
    [[{ id: 1 }, { id: 2, allowed: false }], {}],
    [[{ id: 1 }, { id: 2 }], { initialView: "case-mine-civil" }],
  ]) {
    const state = setup({ context });
    await state.run(rows);
    assert.equal(state.modal, undefined);
    assert.equal(state.requests.length, 0);
    assert.equal(state.messages[0][0], "warning");
  }
});

test("backend failure preserves selection and does not refresh or claim success", async () => {
  const state = setup({ apiError: true });
  await state.run([{ id: 1 }, { id: 2 }]);
  await assert.rejects(state.modal.onOk());
  assert.equal(state.selection.length, 0);
  assert.equal(state.refreshes.length, 0);
  assert.equal(state.messages.some(([level]) => level === "success"), false);
});

test("counsel list refresh uses its own loader and pagination", async () => {
  const state = setup({ context: { counselListMode: true } });
  await state.run([{ id: 1 }, { id: 2 }]);
  await state.modal.onOk();
  assert.deepEqual(state.refreshes, [["counsel", { keyword: "CODEX" }, 3, 20]]);
});

test("refresh and file cleanup warnings do not invite repeating committed deletion", async () => {
  const state = setup({ refreshError: true, cleanupPending: 1 });
  await state.run([{ id: 1 }, { id: 2 }]);
  await state.modal.onOk();
  assert.deepEqual(state.selection, [[]]);
  assert.equal(state.messages.filter(([level]) => level === "error").length, 0);
  assert.ok(state.messages.some(([, value]) => value.includes("清理待处理")));
  assert.ok(state.messages.some(([, value]) => value.includes("列表刷新失败")));
});

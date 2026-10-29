// BUG20261028019：仲裁的案件阶段树按旧系统截图一比一（我的案件、公司案件）；其他案件类型不变。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";
import * as parity from "../src/caseOrdinarySearchParity.mjs";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const element = (type, props) => ({ type, props: props || {} });
const stubs = {
  "../caseOrdinarySearchParity.mjs": parity,
  react: { useState: (init) => [typeof init === "function" ? init() : init, () => {}] },
  "react/jsx-runtime": { jsx: element, jsxs: element, Fragment: "Fragment" },
};
const loadConstants = () => {
  const compiled = ts.transpileModule(read("../src/legal/constants.tsx"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  const fakeRequire = (name) => stubs[name] ?? new Proxy({}, { get: (_target, key) => (key === "__esModule" ? true : () => null) });
  new Function("exports", "require", "module", compiled)(module.exports, fakeRequire, module);
  return module.exports;
};
const constants = loadConstants();
const ARBITRATION = "仲裁";
// 生产仲裁案件阶段分布：旧数据“待分配”7 个，其余各 1 个。
const counts = { 待分配: 7, 文书准备: 1, 仲裁准备开庭: 1, 仲裁庭后待判: 1, 已归档: 1 };

const arbitrationTree = (view) => parity.buildLegacyCasePhaseTree(
  constants.getCasePhaseDefinitions(view, [], []), [], counts,
  parity.casePhaseChildrenForCaseType(ARBITRATION), parity.casePhaseAliasesForCaseType(ARBITRATION),
);

test("仲裁阶段树与旧系统截图一致（我的案件、公司案件）", () => {
  for (const view of ["case-mine-arbitration", "case-company-arbitration"]) {
    const tree = arbitrationTree(view);
    assert.deepEqual(tree.map((item) => item.label), ["待分配", "文书准备", "仲裁阶段", "申诉阶段", "执行立案", "归档阶段"], view);
    const byLabel = Object.fromEntries(tree.map((item) => [item.label, item]));
    assert.deepEqual(byLabel["仲裁阶段"].children.map((item) => item.label), [
      "仲裁立案受理", "仲裁补充证据", "仲裁准备开庭", "仲裁再次开庭", "仲裁庭后待判",
    ]);
    assert.deepEqual(byLabel["申诉阶段"].children.map((item) => item.label), [
      "申诉立案受理", "申诉补充证据", "申诉通知开庭", "申诉庭后待判", "申诉再审裁定",
    ]);
    assert.equal(byLabel["执行立案"].value, "执行阶段");
    assert.deepEqual(byLabel["执行立案"].children.map((item) => item.label), [
      "执行立案", "执行受理", "执行中止", "执行结案", "和解中", "和解结案", "归档审核", "已归档",
    ]);
    assert.deepEqual(byLabel["归档阶段"].children.map((item) => item.label), [
      "归档审核", "已归档", "归档拒绝", "亏损内审", "亏损审核", "亏损归档", "亏损拒绝",
    ]);
    assert.deepEqual(tree.map((item) => item.count), [7, 1, 2, 0, 1, 1], view);
  }
});

test("仲裁按阶段筛选带上旧阶段名和目录子项", () => {
  const children = parity.casePhaseChildrenForCaseType(ARBITRATION);
  const aliases = parity.casePhaseAliasesForCaseType(ARBITRATION);
  assert.deepEqual(parity.legacyCasePhaseFilterValues("新案待分配", children, aliases), ["新案待分配", "待分配"]);
  assert.ok(parity.legacyCasePhaseFilterValues("仲裁阶段", children, aliases).includes("仲裁庭后待判"));
  assert.ok(parity.legacyCasePhaseFilterValues("执行阶段", children, aliases).includes("执行立案"));
});

test("民事、行政阶段树不变", () => {
  assert.equal(parity.casePhaseChildrenForCaseType(""), parity.LEGACY_PHASE_CHILDREN);
  assert.equal(parity.casePhaseChildrenForCaseType("行政案件及国家赔偿"), parity.LEGACY_ADMINISTRATIVE_PHASE_CHILDREN);
  assert.deepEqual(parity.legacyCasePhaseFilterValues("新案待分配"), ["新案待分配"]);
  const civilDefaults = [{ label: "新案待分配", value: "新案待分配" }];
  assert.deepEqual(constants.getCasePhaseDefinitions("case-mine-civil", civilDefaults, []), civilDefaults);
});

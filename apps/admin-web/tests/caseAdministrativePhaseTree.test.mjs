// BUG20261028018：行政案件及国家赔偿的案件阶段树按旧系统截图一比一；其他案件类型不变。
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
const ADMIN = "行政案件及国家赔偿";
// 生产 9 个行政案件：旧数据 4 个“待分配”、1 个“新案待分配”、4 个“已归档”。
const counts = { 待分配: 4, 新案待分配: 1, 已归档: 4 };

const adminTree = (view) => parity.buildLegacyCasePhaseTree(
  constants.getCasePhaseDefinitions(view, [], []), [], counts,
  parity.casePhaseChildrenForCaseType(ADMIN), parity.casePhaseAliasesForCaseType(ADMIN),
);

test("行政案件阶段树与旧系统截图一致", () => {
  for (const view of ["case-mine-administrative", "case-dept-administrative", "case-company-administrative"]) {
    const tree = adminTree(view);
    assert.deepEqual(tree.map((item) => item.label), [
      "待分配", "文书准备", "一审阶段", "二审阶段", "再审立案受理", "执行阶段",
      "和解中", "和解结案", "归档审核", "已归档", "归档阶段",
    ], view);
    const byLabel = Object.fromEntries(tree.map((item) => [item.label, item]));
    assert.deepEqual(byLabel["文书准备"].children.map((item) => item.label), ["客户盖章"]);
    assert.deepEqual(byLabel["一审阶段"].children.map((item) => item.label), [
      "一审立案受理", "一审补充证据", "一审准备开庭", "一审再次开庭", "一审庭后待判",
      "一审等待上诉", "一审待执行", "一审上诉准备", "一审补充代理意见",
    ]);
    assert.deepEqual(byLabel["二审阶段"].children.map((item) => item.label), [
      "二审立案受理", "二审补充证据", "二审通知开庭", "二审再次开庭", "二审庭后待判", "二审待执行", "二审补充代理意见",
    ]);
    assert.equal(byLabel["再审立案受理"].value, "再审阶段");
    assert.deepEqual(byLabel["再审立案受理"].children.map((item) => item.label), [
      "再审立案受理", "再审补充证据", "再审通知开庭", "再审庭后待判", "再审待执行",
    ]);
    assert.deepEqual(byLabel["执行阶段"].children.map((item) => item.label), ["执行立案", "执行受理", "执行中止", "执行结案"]);
    assert.deepEqual(byLabel["归档阶段"].children.map((item) => item.label), [
      "归档审核", "已归档", "归档拒绝", "亏损内审", "亏损审核", "亏损归档", "亏损拒绝",
    ]);
    // 旧“待分配”和“新案待分配”一起算，和旧系统【5】一致；已归档根和归档阶段都显示 4。
    assert.deepEqual([byLabel["待分配"].count, byLabel["已归档"].count, byLabel["归档阶段"].count], [5, 4, 4]);
  }
});

test("行政案件按阶段筛选带上旧阶段名和目录子项", () => {
  const children = parity.casePhaseChildrenForCaseType(ADMIN);
  const aliases = parity.casePhaseAliasesForCaseType(ADMIN);
  assert.deepEqual(parity.legacyCasePhaseFilterValues("新案待分配", children, aliases), ["新案待分配", "待分配"]);
  assert.deepEqual(parity.legacyCasePhaseFilterValues("文书准备", children, aliases), ["文书准备", "客户盖章"]);
  assert.ok(parity.legacyCasePhaseFilterValues("再审阶段", children, aliases).includes("再审待执行"));
});

test("民事、刑事阶段树不变", () => {
  const civil = parity.buildLegacyCasePhaseTree(
    constants.getCasePhaseDefinitions("case-mine-civil", parity.LEGACY_CIVIL_PHASE_ROOTS.map((value) => ({ label: value, value })), []),
    [], counts, parity.casePhaseChildrenForCaseType(""), parity.casePhaseAliasesForCaseType(""),
  );
  assert.deepEqual(civil.map((item) => item.label), parity.LEGACY_CIVIL_PHASE_ROOTS);
  assert.equal(civil.find((item) => item.label === "新案待分配").count, 1);
  assert.deepEqual(parity.legacyCasePhaseFilterValues("新案待分配"), ["新案待分配"]);
  assert.equal(parity.casePhaseChildrenForCaseType("刑事案件"), parity.LEGACY_CRIMINAL_PHASE_CHILDREN);
  assert.deepEqual(constants.getCasePhaseDefinitions("case-mine-criminal", [], parity.LEGACY_CRIMINAL_PHASE_ROOT_ITEMS), parity.LEGACY_CRIMINAL_PHASE_ROOT_ITEMS);
});

// 10.22 批次任务 C：第 11 行（刑事案件变更阶段树）与第 17 行（刑事案件文档目录）聚焦回归。
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

const civilPhase = (id, code, name, parent = "") => ({ id, code, name, canonical_name: name, case_type: "民事争议", parent_code: parent });
const criminalPhase = (id, code, name) => ({ id, code, name, canonical_name: name, case_type: "刑事案件", parent_code: "" });
const phaseOptions = () => {
  let id = 1;
  const items = [
    civilPhase(id++, "WAIT_NOTARY", "等待公证书"),
    civilPhase(id++, "NEW", "新案待分配"),
    criminalPhase(id++, "CRIMINAL_POLICE_INVESTIGATION", "公安侦查"),
    criminalPhase(id++, "CRIMINAL_ARREST", "批捕"),
    criminalPhase(id++, "CRIMINAL_PROSECUTION_REVIEW", "检察院审查起诉"),
  ];
  for (const [group, code] of [["一审阶段", "FIRST"], ["二审阶段", "SECOND"], ["再审阶段", "RETRIAL"], ["归档阶段", "ARCHIVE"]]) {
    items.push(civilPhase(id++, code, group));
    for (const child of parity.LEGACY_PHASE_CHILDREN[group]) items.push(civilPhase(id++, `${code}_${child}`, child, code));
  }
  // 10.22 新增第 11 行：刑事专用子阶段（民事没有的同组子项）。
  for (const name of ["一审通知开庭", "一审一审判决", "二审上诉准备", "二审判决", "二审判决生效"]) items.push(criminalPhase(id++, `CRIMINAL_${name}`, name));
  return items;
};

// 按渲染顺序收集阶段树中的文字（Checkbox 末级 / 📁 目录）。
const collectLabels = (node, output = []) => {
  if (node == null || typeof node === "boolean") return output;
  if (Array.isArray(node)) { node.forEach((child) => collectLabels(child, output)); return output; }
  if (typeof node === "string" || typeof node === "number") { output.push(String(node)); return output; }
  if (node.props?.className?.includes?.("case-phase-toggle")) return output;
  collectLabels(node.props?.children, output);
  return output;
};
const rootLabels = (tree) => tree.props.children.map((group) => collectLabels(group.props.children[0]).join("").replace("📁 ", ""));

test("第11行：刑事案件变更阶段树按旧系统刑事根（待分配、公安侦查、批捕、检察院审查起诉 + 一审/二审/再审/归档）", () => {
  const tree = constants.CasePhasePickerTree({ options: phaseOptions(), caseType: "刑事案件" });
  assert.deepEqual(rootLabels(tree), ["待分配", "公安侦查", "批捕", "检察院审查起诉", "一审阶段", "二审阶段", "再审阶段", "归档阶段"]);
  const labels = collectLabels(tree);
  // 10.22 新增第 11 行：子阶段逐项等于旧系统刑事截图，民事独有子阶段不出现。
  for (const group of ["一审阶段", "二审阶段", "再审阶段", "归档阶段"]) {
    for (const child of parity.LEGACY_CRIMINAL_PHASE_CHILDREN[group]) assert.ok(labels.includes(child), child);
  }
  for (const civilOnly of ["一审准备开庭", "一审和解中", "一审判决结案", "二审再次开庭", "二审判决结案", "再审和解中"]) assert.ok(!labels.includes(civilOnly), civilOnly);
  assert.deepEqual(parity.LEGACY_CRIMINAL_PHASE_CHILDREN["一审阶段"], ["一审立案受理", "一审补充证据", "一审通知开庭", "一审庭后待判", "一审一审判决", "一审等待上诉"]);
  assert.deepEqual(parity.LEGACY_CRIMINAL_PHASE_CHILDREN["二审阶段"], ["二审上诉准备", "二审立案受理", "二审补充证据", "二审通知开庭", "二审庭后待判", "二审判决", "二审判决生效"]);
  assert.deepEqual(parity.LEGACY_CRIMINAL_PHASE_CHILDREN["再审阶段"], ["再审立案受理", "再审补充证据", "再审通知开庭", "再审庭后待判", "再审待执行"]);
  assert.ok(!labels.includes("等待公证书"));
  assert.ok(!labels.some((label) => label.includes("执行阶段")));
});

test("第11行：未传案件类型时，接口返回刑事专用阶段即自动用刑事树；民事选项仍是民事根", () => {
  assert.equal(rootLabels(constants.CasePhasePickerTree({ options: phaseOptions() }))[0], "待分配");
  const civilOnly = phaseOptions().filter((item) => item.case_type !== "刑事案件");
  const civilRoots = rootLabels(constants.CasePhasePickerTree({ options: civilOnly }));
  assert.equal(civilRoots[0], "等待公证书");
  assert.ok(civilRoots.includes("新案待分配"));
});

test("第11行：“待分配”选中值是新案待分配阶段 id；列表面板与弹窗共用常量", () => {
  const options = phaseOptions();
  const tree = constants.CasePhasePickerTree({ options, caseType: "刑事案件", value: 2 });
  const pending = tree.props.children[0].props.children[0].props.children[1];
  assert.equal(pending.props.checked, true);
  assert.deepEqual(constants.CRIMINAL_CASE_PHASE_ROOT_ITEMS[0], { label: "待分配", value: "新案待分配" });
});

test("第17行：刑事案件新系统目录树为诉讼阶段文件四个子目录 + 公安机关文件、检察机关文件，民事不变", () => {
  const expanded = { 案件文档全部: true, 调查文档全部: true };
  const criminal = constants.buildNativeCaseDocumentTree({ caseType: "刑事案件", customFolders: ["CODEX-1022-17-自定义"], expandedGroups: expanded,
    folderTree: [{ value: "案件文档全部", label: "诉讼阶段文件", options: [{ value: "起诉材料及证据", label: "起诉材料及证据", disabled: true }] }] });
  assert.equal(criminal.find((item) => item.category === "案件文档全部").label, "诉讼阶段文件");
  assert.deepEqual(criminal.filter((item) => item.parent === "案件文档全部").map((item) => item.label),
    ["委托手续及证明", "起诉书及证据", "辩论意见及证据", "法院裁判文书", "起诉材料及证据", "CODEX-1022-17-自定义"]);
  assert.deepEqual(criminal.slice(-2).map((item) => [item.label, item.type]), [["公安机关文件", "folder"], ["检察机关文件", "folder"]]);
  const civil = constants.buildNativeCaseDocumentTree({ caseType: "民事争议", expandedGroups: expanded });
  assert.deepEqual(civil.filter((item) => item.parent === "案件文档全部").map((item) => item.label), constants.AGENT_CASE_DOCUMENT_FOLDERS);
  assert.ok(!civil.some((item) => item.label === "公安机关文件"));
});

test("第17行：上传、移动选项与分组排除按案件类型区分", () => {
  const upload = constants.getCaseUploadCategoryOptions({ caseType: "刑事案件",
    fileTypeOptions: [{ value: "主体及委托资料", label: "主体及委托资料" }, { value: "委托材料", label: "委托材料" }] }).map((item) => item.value);
  assert.deepEqual(upload, ["委托手续及证明", "起诉书及证据", "辩论意见及证据", "法院裁判文书", "公安机关文件", "检察机关文件", "委托材料", "普通附件"]);
  const nested = constants.getCaseUploadCategoryOptions({ caseType: "刑事案件", fileTypeOptions: [{ value: "调查文档", label: "调查文档",
    options: [{ value: "鉴别资料", label: "鉴别资料" }, { value: "庭审及庭后文件", label: "庭审及庭后文件" }] }] });
  assert.deepEqual(nested.find((item) => item.value === "调查文档").options.map((item) => item.value), ["鉴别资料"]);
  assert.deepEqual(constants.getCaseDocumentMoveCategoryOptions([], "刑事案件").map((item) => item.value),
    ["委托手续及证明", "起诉书及证据", "辩论意见及证据", "法院裁判文书", "公安机关文件", "检察机关文件"]);
  assert.deepEqual(constants.getCaseDocumentMoveCategoryOptions(["自定义"]).map((item) => item.value), [...constants.AGENT_CASE_DOCUMENT_FOLDERS, "自定义"]);
  assert.ok(constants.getNonCaseDocumentCategories("刑事案件").includes("公安机关文件"));
  assert.ok(!constants.getNonCaseDocumentCategories("民事争议").includes("公安机关文件"));
});

test("10.22 新增第11行：刑事案件列表左侧阶段树与筛选使用刑事子阶段，民事不变", () => {
  const criminalChildren = parity.casePhaseChildrenForCaseType("刑事案件");
  const tree = parity.buildLegacyCasePhaseTree(parity.LEGACY_CRIMINAL_PHASE_ROOT_ITEMS.map((item) => ({ ...item, count: 0 })), [], { "二审判决生效": 2, "一审一审判决": 1 }, criminalChildren);
  const second = tree.find((node) => node.label === "二审阶段");
  assert.deepEqual(second.children.map((child) => child.label), criminalChildren["二审阶段"]);
  assert.equal(second.count, 2);
  assert.equal(tree.find((node) => node.label === "一审阶段").count, 1);
  assert.ok(parity.legacyCasePhaseFilterValues("二审阶段", criminalChildren).includes("二审判决生效"));
  assert.ok(!parity.legacyCasePhaseFilterValues("二审阶段", criminalChildren).includes("二审判决结案"));
  assert.deepEqual(parity.casePhaseChildrenForCaseType("民事争议"), parity.LEGACY_PHASE_CHILDREN);
  assert.ok(parity.legacyCasePhaseFilterValues("二审阶段").includes("二审判决结案"));
});

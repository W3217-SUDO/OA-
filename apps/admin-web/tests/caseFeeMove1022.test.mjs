// 10.22 第8行：律所费用、平台费用“其他操作”新增“移到其他案子”。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const jsx = (type, props) => ({ type, props: props || {} });
const loadModule = (path, stubs = {}) => {
  const compiled = ts.transpileModule(read(path), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  const fakeRequire = (name) => stubs[name] ?? new Proxy({}, { get: (_target, key) => (key === "__esModule" ? true : () => null) });
  new Function("exports", "require", "module", compiled)(module.exports, fakeRequire, module);
  return module.exports;
};

const { CaseFeesPanel } = loadModule("../src/legal/CaseDetail/CaseFeesPanel.tsx", {
  "react/jsx-runtime": { jsx, jsxs: jsx, Fragment: "Fragment" },
  antd: { Button: "Button", Dropdown: "Dropdown", Space: "Space" },
  "../../components/ResizableTable": { __esModule: true, default: "Table" },
  "../../caseRelationConsumption.mjs": { PLATFORM_AGENCY_FEE_SUBTYPE: "平台代理费" },
  "../../financialValueDisplay": { displayFeeValue: (value) => value },
});

const findDropdowns = (node, output = []) => {
  if (!node || typeof node !== "object") return output;
  if (Array.isArray(node)) { node.forEach((child) => findDropdowns(child, output)); return output; }
  if (node.type === "Dropdown") output.push(node);
  findDropdowns(node.props?.children, output);
  return output;
};

const otherOperationsKeys = (scope, capabilities) => {
  const calls = [];
  const tree = CaseFeesPanel({
    scope, loading: false, feeRows: [{ id: 1, data: {} }], selectedFeeKeys: [1], setSelectedFeeKeys: () => {}, selectedFee: { id: 1, data: {} },
    counselDetailCapabilities: capabilities, firmCaseFeeColumns: [], externalCaseFeeColumns: [],
    handleExternalFeeOperation: (...args) => calls.push(args), requireSingleFee: () => false, canMarkCaseFeeRefundNotRequired: () => false,
  });
  const dropdown = findDropdowns(tree).find((item) => item.props.children?.props?.children === "其他操作");
  return { keys: dropdown ? dropdown.props.menu.items.map((item) => item.key) : [], dropdown, calls };
};

test("第8行：律所费用、平台费用都在“申请开票”之后出现“移到其他案子”，点击交给统一分发", () => {
  const capabilities = { can_apply_fee_payment: true, can_apply_fee_invoice: true, can_edit_finance: true, can_delete_finance: true, can_move_fee: true };
  for (const scope of ["firm", "platform"]) {
    const { keys, dropdown, calls } = otherOperationsKeys(scope, capabilities);
    assert.ok(keys.includes("move-case"), scope);
    assert.equal(keys.indexOf("move-case"), keys.indexOf("invoice") + 1, `${scope}：位于申请开票之后`);
    assert.ok(keys.indexOf("move-case") < keys.indexOf("edit"), `${scope}：位于修改之前`);
    dropdown.props.menu.onClick({ key: "move-case" });
    assert.deepEqual(calls[0].slice(2), ["move-case"]);
  }
});

test("第8行：没有“移到其他案件”权限时不显示该菜单项", () => {
  const { keys } = otherOperationsKeys("firm", { can_apply_fee_invoice: true, can_move_fee: false });
  assert.ok(!keys.includes("move-case"));
});

test("第8行：未选或多选时按统一提示拦截；弹窗字段、提示文字与提交接口", () => {
  const actions = read("../src/legal/services/financeActions.tsx");
  assert.match(actions, /key === "move-case" \? "移到其他案子"/);
  assert.match(actions, /if \(key === "move-case"\)\n\s+return openCaseFeeMove\(selectedFee!\);/);
  const page = read("../src/legal/CaseCenterPage.tsx");
  const modal = page.slice(page.indexOf('title="移到其他案子"'), page.indexOf("</Modal>", page.indexOf('title="移到其他案子"')));
  for (const label of ["当前案件", "客户编号", "合同编号", "目标案件", "请输入目标案件编号", "仅允许迁移到同一客户下的案件；一次只能迁移一条费用。", 'okText="确定"', 'cancelText="取消"']) {
    assert.ok(modal.includes(label) || page.includes(label), label);
  }
  assert.match(page, /api\.post\(`\/finance\/fees\/\$\{movingFee\.id\}\/move-case`, \{ target_case_no: targetCaseNo \}\)/);
  assert.match(page, /目标案件不能与当前案件相同/);
  const css = read("../src/case-center.css");
  assert.match(css, /\.case-fee-move-form \.ant-form-item-label\{flex:0 0 100%!important/);
});

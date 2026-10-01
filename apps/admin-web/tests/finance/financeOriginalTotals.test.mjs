import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";
import { paymentQueryPageTotal } from "../../src/finance/constants.ts";

const require = createRequire(import.meta.url);
const Button = () => null;
const Dropdown = () => null;
const Space = () => null;
const SummaryRow = () => null;
const SummaryCell = () => null;
const Table = Object.assign(() => null, { Summary: { Row: SummaryRow, Cell: SummaryCell } });

function load(name, dependencies) {
  const source = fs.readFileSync(new URL(`../../src/finance/${name}`, import.meta.url), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, {
    module, exports: module.exports,
    require: (specifier) => specifier in dependencies ? dependencies[specifier] : require(specifier),
  }, { filename: name });
  return module.exports;
}

function nodes(element) {
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!element || typeof element !== "object" || !("props" in element)) return [];
  return [element, ...nodes(element.props.children)];
}

const totals = load("FinanceOriginalTotals.tsx", {
  "../components/ResizableTable": Table,
  "./constants": { paymentQueryPageTotal },
});

test("payment query totals retain the fifth-column amount and suppress an empty page summary", () => {
  const rows = [{ id: 1, data: { amount: 10 } }, { id: 2, amount: 2.5 }];
  const body = totals.PaymentQueryTotalBody({ rows, columnCount: 6, children: "table rows" });
  const cells = nodes(body).filter((node) => node.type === "td");
  assert.equal(cells.length, 6);
  assert.equal(cells[4].props.children, "12.50");
  assert.equal(body.props.children[1], "table rows");
  assert.equal(totals.PaymentQueryPageSummary({ rows: [], columnCount: 6 }), null);
  const pageCells = nodes(totals.PaymentQueryPageSummary({ rows, columnCount: 6 })).filter((node) => node.type === SummaryCell);
  assert.equal(pageCells[4].props.children, "12.50");
});

test("fee query grand totals and current-page totals use their distinct data sources", () => {
  const headers = ["金额", "退费金额", "备注"];
  const body = totals.FeeQueryTotalBody({ headers, totals: { amount: 100, refund_requested_amount: null }, children: "rows" });
  const cells = nodes(body).filter((node) => node.type === "td");
  assert.equal(cells[1].props.children, "100.00");
  assert.equal(cells[2].props.children, null);
  const rows = [{ id: 1, data: { amount: 10, refund_requested_amount: 2 } }, { id: 2, data: { amount: 5.25 } }];
  const summary = totals.FeeQueryPageSummary({ rows, headers });
  const pageCells = nodes(summary).filter((node) => node.type === SummaryCell);
  assert.equal(pageCells[1].props.children, "15.25");
  assert.equal(pageCells[2].props.children, "2.00");
  assert.equal(totals.FeeQueryPageSummary({ rows: [], headers }), null);
});

test("internal payment and payment-package totals keep nullish amount precedence", () => {
  const internal = totals.InternalPaymentPageSummary({
    rows: [{ id: 1, data: { actual_commission: 0, amount: 8 } }, { id: 2, data: { amount: 3.2 } }],
    headers: ["申请编号", "实际提成"],
  });
  const internalCells = nodes(internal).filter((node) => node.type === SummaryCell);
  assert.equal(internalCells[2].props.children, "3.20");
  const rows = [{ id: 1, data: { total_amount: 0, amount: 10 } }, { id: 2, data: { amount: 7.5 } }];
  const body = totals.PaymentPackageTotalBody({ rows, headers: ["付款编号", "付款总金额"], children: "rows" });
  assert.equal(nodes(body).filter((node) => node.type === "td")[1].props.children, "7.50");
  const page = totals.PaymentPackagePageSummary({ rows: rows.slice(1), headers: ["付款编号", "付款总金额"] });
  assert.equal(nodes(page).filter((node) => node.type === SummaryCell)[1].props.children, "7.50");
});

test("fee query action menu preserves selected/all export and delegated actions", () => {
  const { FinanceFeeQueryActions } = load("FinanceFeeQueryActions.tsx", { antd: { Button, Dropdown, Space } });
  const calls = [];
  const rendered = nodes(FinanceFeeQueryActions({
    exportLoading: true,
    actionLoading: false,
    onExport: (selected) => calls.push(["export", selected]),
    onMoreAction: (key) => calls.push(["more", key]),
  }));
  const menus = rendered.filter((node) => node.type === Dropdown);
  assert.equal(rendered.find((node) => node.type === Button && node.props.children === "导出 ▾").props.loading, true);
  menus[0].props.menu.onClick({ key: "selected" });
  menus[0].props.menu.onClick({ key: "all" });
  menus[1].props.menu.onClick({ key: "tasks" });
  assert.deepEqual(calls, [["export", true], ["export", false], ["more", "tasks"]]);
});

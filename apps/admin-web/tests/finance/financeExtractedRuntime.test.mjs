import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";
import React from "react";
import { act, create } from "react-test-renderer";
import ts from "typescript";

const require = createRequire(import.meta.url);
const sourceRoot = new URL("../../src/finance/", import.meta.url);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test("internal queues request real 200-row pages, retain server status and expose denied access", async () => {
  const requests = [];
  const cleared = [];
  const fixtures = Array.from({ length: 201 }, (_, index) => ({ id: index + 1, status: "已付款", data: { fee_type: "代理费", amount: index + 1, cashed_amount: (index + 1) * 2 } }));
  let denied = false;
  const { useInternalFinanceQuery, internalFinanceQueryRequest } = loadModule("hooks/useInternalFinanceQuery.ts", {
    "../../api": { api: { get: async (path, options) => {
      requests.push({ path, ...options });
      if (denied) throw new Error("无权查询内部费用");
      const { page, page_size } = options.params;
      return { data: { items: fixtures.slice((page - 1) * page_size, page * page_size), total: fixtures.length, page, page_size, amount_visible: true, total_amount: 20301, total_cashed_amount: 40602 } };
    } } },
    "../financeErrors": { financeErrorDetail: (error) => error.message },
  });
  let state;
  const clear = (keys) => cleared.push(keys);
  const Probe = ({ center }) => { state = useInternalFinanceQuery("finance-internal-settle", clear, center); return null; };
  let tree;
  await act(async () => { tree = create(React.createElement(Probe, { center: "firm" })); });
  await act(async () => state.load({ routeField1: "CODEX-CASE" }, 1, 200));
  assert.equal(state.rows.length, 200);
  assert.equal(state.rows[0].status, "已付款");
  assert.equal(state.meta.total, 201);
  assert.equal(state.meta.pageSize, 200);
  assert.equal(state.meta.totalAmount, 20301);
  assert.equal(state.meta.totalCashedAmount, 40602);
  assert.equal(requests[0].path, "/finance/settlements/pending");
  assert.equal(requests[0].params.case_no, "CODEX-CASE");
  assert.equal(requests[0].params.finance_scope, "firm");
  await act(async () => state.load({ routeField1: "CODEX-CASE" }, 2, 200));
  assert.deepEqual(state.rows.map((row) => row.id), [201]);
  assert.equal(state.rows[0].data.amount, 201);
  assert.equal(state.rows[0].data.cashed_amount, 402);
  assert.equal(state.meta.totalAmount, 20301);
  assert.equal(state.meta.totalCashedAmount, 40602);
  await act(async () => tree.update(React.createElement(Probe, { center: "platform" })));
  assert.equal(state.rows.length, 0);
  await act(async () => state.load({}, 1, 200));
  assert.equal(requests.at(-1).params.finance_scope, "platform");
  denied = true;
  await act(async () => { await assert.rejects(state.load({}, 1, 50), /无权/); });
  assert.equal(state.error, "无权查询内部费用");
  assert.equal(state.rows.length, 0);
  assert.equal(state.loading, false);
  assert.equal(cleared.length, 4);
  const archive = internalFinanceQueryRequest("finance-internal-archive", {
    routeField2: "CODEX-APPLICANT", routeField5: "CODEX-CASE", routeField6: "CODEX-REQUEST",
  }, 1, 200);
  assert.equal(archive.params.scope, "archive");
  assert.equal(archive.params.application_no, "CODEX-REQUEST");
  assert.equal(archive.params.applicant, "CODEX-APPLICANT");
  const review = internalFinanceQueryRequest("finance-internal-fee-audit", {}, 1, 200);
  assert.equal(review.params.kind, "other");
  await act(async () => tree.unmount());
});

test("internal queue late response cannot overwrite a newer page or route", async () => {
  const pending = [];
  const { useInternalFinanceQuery } = loadModule("hooks/useInternalFinanceQuery.ts", {
    "../../api": { api: { get: (_path, options) => new Promise((resolve, reject) => pending.push({ ...options, resolve, reject })) } },
    "../financeErrors": { financeErrorDetail: (error) => error.message },
  });
  let state;
  const clear = () => {};
  const Probe = ({ route }) => { state = useInternalFinanceQuery(route, clear, "firm"); return null; };
  let tree, first, second;
  await act(async () => { tree = create(React.createElement(Probe, { route: "finance-internal-audit" })); });
  await act(async () => { first = state.load({}, 1, 15); });
  await act(async () => { second = state.load({}, 1, 200); });
  assert.equal(pending[0].signal.aborted, true);
  await act(async () => { pending[1].resolve({ data: { items: [{ id: 2 }], total: 1, page: 1, page_size: 200, amount_visible: true, total_amount: 200 } }); await second; });
  await act(async () => { pending[0].resolve({ data: { items: [{ id: 1 }], total: 1, page: 1, page_size: 15, amount_visible: true, total_amount: 15 } }); await first; });
  assert.equal(state.rows[0].id, 2);
  assert.equal(state.meta.totalAmount, 200);
  await act(async () => tree.update(React.createElement(Probe, { route: "finance-internal-refused" })));
  assert.equal(state.rows.length, 0);
  assert.equal(state.meta.page, 1);
  await act(async () => tree.unmount());
});

test("internal queue grand totals survive unequal pages and preserve zero, hidden amounts and errors", async () => {
  const fixtures = [{ id: 1, data: { amount: 10, actual_commission: 0 } }, { id: 2, data: { amount: 90 } }];
  let mode = "visible";
  const { useInternalFinanceQuery } = loadModule("hooks/useInternalFinanceQuery.ts", {
    "../../api": { api: { get: async (_path, { params }) => ({ data: {
      items: mode === "empty" ? [] : mode === "hidden" ? [{ id: params.page, data: {} }] : fixtures.slice(params.page - 1, params.page),
      total: mode === "empty" ? 0 : 2, page: params.page, page_size: params.page_size,
      amount_visible: mode === "missing" ? undefined : mode !== "hidden",
      total_amount: mode === "hidden" ? null : mode === "empty" ? 0 : 100,
      total_actual_commission: mode === "hidden" ? null : mode === "empty" ? 0 : mode === "invalid" ? undefined : 90,
    } }) } },
    "../financeErrors": { financeErrorDetail: (error) => error.message },
  });
  let state, tree;
  const clear = () => {};
  const Probe = () => { state = useInternalFinanceQuery("finance-internal-payment", clear, "firm"); return null; };
  await act(async () => { tree = create(React.createElement(Probe)); });
  for (const page of [1, 2]) {
    await act(async () => state.load({ routeField2: "CODEX-PAYEE" }, page, 1));
    assert.equal(state.rows[0].data.amount, page === 1 ? 10 : 90);
    assert.equal(state.meta.totalAmount, 100);
    assert.equal(state.meta.totalActualCommission, 90);
    assert.equal(state.meta.amountVisible, true);
  }
  mode = "empty";
  await act(async () => state.load({}, 1, 200));
  assert.equal(state.meta.totalAmount, 0);
  assert.equal(state.meta.totalActualCommission, 0);
  mode = "hidden";
  await act(async () => state.load({}, 1, 200));
  assert.equal(state.meta.amountVisible, false);
  assert.equal(state.meta.totalAmount, null);
  assert.equal(state.meta.totalActualCommission, null);
  for (mode of ["missing", "invalid"]) {
    await act(async () => { await assert.rejects(state.load({}, 1, 200), /汇总响应无效/); });
    assert.equal(state.error, "内部费用汇总响应无效");
    assert.equal(state.rows.length, 0);
  }
  await act(async () => tree.unmount());
});

test("case readers can open a receipt detail without gaining the company list or write route", () => {
  const { isWorkspaceRouteGranted } = loadModule("../workspacePermissions.ts", {
    "./dashboardWorkspace": { dashboardWorkspace: () => null },
    "./feedback/navigation": { FEEDBACK_ROUTE: "feedback" },
  });
  const granted = new Set(["case-company", "finance-internal-audit"]);
  assert.equal(isWorkspaceRouteGranted("finance-incoming-payment-824", granted), true);
  assert.equal(isWorkspaceRouteGranted("finance-incoming-company", granted), false);
  assert.equal(isWorkspaceRouteGranted("finance-receipts-new", granted), false);
  assert.equal(isWorkspaceRouteGranted("finance-incoming-payment-824", new Set(["hr-all"])), false);
  assert.equal(isWorkspaceRouteGranted("finance-incoming-payment-invalid", granted), false);
});
const host = (name) => ({ children, ...props }) => React.createElement(name, props, children);
const Form = host("form");
Form.Item = host("form-item");
Form.List = ({ children }) => children([{ key: 0, name: 0 }], { add: () => {}, remove: () => {} });
const Input = host("input");
Input.TextArea = host("textarea");
const antd = {
  Alert: host("alert"), AutoComplete: host("auto-complete"), DatePicker: host("date-picker"),
  Button: host("button"), Drawer: host("drawer"), Form, Input,
  InputNumber: host("input-number"), Modal: host("modal"), Select: host("select"),
  Space: host("space"), Steps: host("steps"),
};

function loadModule(name, dependencies, globals = {}) {
  const source = fs.readFileSync(new URL(name, sourceRoot), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, {
    module, exports: module.exports,
    require: (specifier) => {
      if (specifier in dependencies) return dependencies[specifier];
      if (specifier === "./financeCenterApi" || specifier === "../services/financeCenterApi") return loadModule("services/financeCenterApi.ts", dependencies);
      if (specifier === "../financialValueDisplay") return loadModule("../financialValueDisplay.ts", dependencies);
      if (specifier === "../settlementIdentity") return loadModule("settlementIdentity.ts", dependencies);
      return require(specifier);
    },
    AbortController, Blob, ...globals,
  }, { filename: name });
  return module.exports;
}

test("legacy history list summary and detail carry the explicit center without rewriting source statuses", async () => {
  const requests = [];
  const response = { data: { source_status: "30", status_code: "30", status_label: "原状态", amount: 0, read_only: true } };
  const { financeCenterApi } = loadModule("services/financeCenterApi.ts", {
    "../../api": { api: { get: async (path, config) => { requests.push({ path, config }); return response; } } },
  });
  for (const financeScope of ["firm", "platform", "unclassified"]) {
    const api = financeCenterApi(financeScope);
    for (const path of ["/finance/legacy-history", "/finance/legacy-history/summary", "/finance/legacy-history/17"]) {
      const config = { params: { page: 2, page_size: 15 }, signal: new AbortController().signal };
      assert.equal(await api.get(path, config), response);
      assert.equal(requests.at(-1).config.params.finance_scope, financeScope);
      assert.equal(requests.at(-1).config.params.page, 2);
      assert.equal(requests.at(-1).config.params.page_size, 15);
      assert.equal(requests.at(-1).config.signal, config.signal);
      assert.equal(Object.hasOwn(config.params, "finance_scope"), false);
      assert.equal(response.data.source_status, "30");
      assert.equal(response.data.status_code, "30");
      assert.equal(response.data.amount, 0);
      assert.equal(response.data.read_only, true);
    }
    const config = { params: { module: "contract" } };
    await api.get("/records", config);
    assert.equal(requests.at(-1).config, config);
  }
});

test("historical settlement identities cannot enter any modern settlement write action", async () => {
  const identity = loadModule("settlementIdentity.ts", {});
  const historical = { id: "legacy-normal:41", source: "legacy", read_only: true, legacy_record_id: 41 };
  assert.equal(identity.isHistoricalSettlement(historical), true);
  assert.throws(() => identity.requireWritableSettlements([historical]), /历史结算记录只读/);
  assert.throws(() => identity.requireWritableSettlements([{ id: "legacy-archive:71" }]), /历史结算记录只读/);
  identity.requireWritableSettlements([{ id: 8 }, { id: "archive:8:2" }]);
  assert.deepEqual(JSON.parse(JSON.stringify(identity.settlementExportIds([8, "legacy-normal:41", "legacy-archive:71"], "application_ids"))), {
    application_ids: "8", projection_ids: "legacy-normal:41,legacy-archive:71",
  });
  let writes = 0;
  let gates = 0;
  const { createFinanceSettlementsActions } = loadModule("services/settlementsActions.tsx", {
    antd: { message: {}, Modal: {} }, "../constants": {}, "../financeErrors": {},
    "../../api": { api: { post: async () => { writes += 1; } } },
  });
  const gate = { tryEnter: () => { gates += 1; return true; } };
  const actions = createFinanceSettlementsActions({
    financeScope: "firm", financeActionGates: { generalSettlement: gate, archiveSettlement: gate },
    generalSettlementReviewTargets: [historical], generalSettlementPaymentTargets: [historical],
    generalSettlementReapplyTargets: [historical], generalSettlementApplyTargets: [historical.id],
    archiveSettlementReviewTargets: [{ id: "legacy-archive:71" }],
    archiveSettlementRollbackTargets: [{ id: "legacy-archive:71" }],
    archiveSettlementReapplyTargets: [{ id: "legacy-archive:71" }],
  });
  for (const name of ["submitGeneralSettlementReview", "submitGeneralSettlementPayment", "submitGeneralSettlementReapply", "submitGeneralSettlementApply", "submitArchiveSettlementReview", "submitArchiveSettlementRollback", "submitArchiveSettlementReapply"]) {
    await assert.rejects(actions[name](), /历史结算记录只读/);
  }
  assert.equal(writes, 0);
  assert.equal(gates, 0);
});

test("settlement source warnings only expose positive server counts without filling missing values", () => {
  const { settlementSourceCounts, settlementSourceMessage } = loadModule("settlementIdentity.ts", {});
  assert.equal(settlementSourceMessage(settlementSourceCounts({})), "");
  assert.equal(settlementSourceMessage(settlementSourceCounts({ unknown_phase_total: 0, unknown_eligibility_total: 0, unknown_date_total: 0 })), "");
  const raw = { unknown_phase_total: 2, unknown_eligibility_total: 3, unknown_date_total: 1, amount: null, source_status: "30" };
  const counts = settlementSourceCounts(raw);
  assert.equal(settlementSourceMessage(counts), "案件阶段待核 2 条；结算条件待核 3 条；原日期待核 1 条");
  assert.equal(raw.amount, null);
  assert.equal(raw.source_status, "30");
  assert.equal(settlementSourceCounts({}).unknown_phase_total, undefined);
});

test("settlement exports preserve historical projection IDs and allow filtered query exports", async () => {
  const requests = [];
  const { createFinanceSettlementsActions } = loadModule("services/settlementsActions.tsx", {
    antd: { message: { success: () => {}, info: () => {} }, Modal: {} }, "../constants": {}, "../financeErrors": {},
    "../../api": { api: { get: async (path, options) => { requests.push({ path, options }); return { data: new Blob(["sheet"]) }; } } },
  }, { document: { createElement: () => ({ click() {} }) }, URL: { createObjectURL: () => "blob:CODEX", revokeObjectURL() {} } });
  const context = {
    financeScope: "platform", selectedOriginalRows: [8], isGeneralSettlementPendingRoute: false,
    isArchiveSettlementPaidRoute: true, setGeneralSettlementBusy() {}, setArchiveSettlementBusy() {},
    financeActionGates: { archiveSettlement: { tryEnter: () => true, leave() {} } },
    originalQuery: { customer: "CODEX-历史查询" },
    generalSettlementParams: query => ({ customer: query.customer, status: "待付款" }),
    archiveSettlementParams: query => ({ customer: query.customer, page: 1, page_size: 20 }),
  };
  const actions = createFinanceSettlementsActions(context);
  await actions.exportGeneralSettlement("settlement", [8, "legacy-normal:41"]);
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).options.params)), {
    kind: "settlement", application_ids: "8", projection_ids: "legacy-normal:41", finance_scope: "platform",
  });
  await actions.exportGeneralSettlement("case");
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).options.params)), {
    customer: "CODEX-历史查询", status: "待付款", kind: "case", finance_scope: "platform",
  });
  await actions.exportPendingArchiveSettlements(["legacy-archive:71"]);
  assert.equal(requests.at(-1).path, "/finance/archive-settlements/paid/export");
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).options.params)), { projection_ids: "legacy-archive:71", finance_scope: "platform" });
  await actions.exportPendingArchiveSettlements([]);
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).options.params)), { customer: "CODEX-历史查询", page: 1, page_size: 20, finance_scope: "platform" });
});

test("settlement downloads decode JSON Blob details without changing the selected receipt contract", async () => {
  const errors = loadModule("financeErrors.ts", {});
  const notices = [];
  const requests = [];
  const downloads = [];
  const busy = [];
  let failure;
  const document = { createElement: () => ({ click() { downloads.push(this.download); } }) };
  const { createFinanceSettlementsActions } = loadModule("services/settlementsActions.tsx", {
    antd: { message: { error: (value) => notices.push(value), success: () => {} }, Modal: { info: (value) => notices.push(value.content) } },
    "../../api": { api: { get: async (path, options) => {
      requests.push({ path, options });
      if (failure) throw failure;
      return { data: new Blob(["binary"], { type: "application/vnd.ms-excel" }) };
    } } },
    "../financeErrors": errors,
    "../constants": {},
  }, { document, URL: { createObjectURL: () => "blob:CODEX-row4", revokeObjectURL: () => {} } });
  const context = { financeScope: "platform", selectedOriginalRows: [], isGeneralSettlementPendingRoute: true, setGeneralSettlementBusy: (value) => busy.push(value) };
  const actions = createFinanceSettlementsActions(context);
  for (const kind of ["case", "settlement"]) {
    await actions.exportGeneralSettlement(kind, [17]);
    assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1))), {
      path: "/finance/general-settlements/export", options: { params: { kind, ids: "17", finance_scope: "platform" }, responseType: "blob" },
    });
  }
  assert.match(downloads[0], /^案件清单-.*\.xls$/);
  assert.match(downloads[1], /^结算清单-.*\.xls$/);
  context.isGeneralSettlementPendingRoute = false;
  await actions.exportGeneralSettlement("case", [71]);
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).options.params)), { kind: "case", application_ids: "71", finance_scope: "platform" });
  for (const [status, detail] of [[403, "无权导出"], [409, "部分回款已申请结算、尚未分配或无权导出"], [422, "请选择需要导出的回款."]]) {
    failure = { response: { status, data: new Blob([JSON.stringify({ detail })], { type: "application/json" }) } };
    await actions.exportGeneralSettlement("case", [17]);
    assert.equal(notices.at(-1), detail);
    assert.equal(busy.at(-1), false);
  }
  failure = { response: { data: new Blob([JSON.stringify({ detail: [{ loc: ["query", "kind"], msg: "invalid kind" }] })], { type: "application/json" }) } };
  await actions.exportGeneralSettlement("case", [17]);
  assert.equal(notices.at(-1), "query.kind：invalid kind");
  failure = { response: { data: new Blob(["{broken"], { type: "application/json" }) } };
  await actions.exportGeneralSettlement("case", [17]);
  assert.equal(notices.at(-1), "服务器返回的导出错误信息格式无效");
  failure = { message: "Request failed with status code 500", response: { data: new Blob(["private server detail"], { type: "text/plain" }) } };
  await actions.exportGeneralSettlement("case", [17]);
  assert.equal(notices.at(-1), "Request failed with status code 500");
  assert.equal(downloads.length, 3, "failed requests must never create a fake workbook download");
  await actions.exportGeneralSettlement("case", []);
  assert.equal(notices.at(-1), "请选择需要导出的回款.");
  assert.equal(errors.financeErrorDetail({ response: { data: { detail: "原有 JSON 详情" } } }), "原有 JSON 详情");
  assert.equal(await errors.financeDownloadErrorDetail({ response: { data: { detail: "原有 JSON 详情" } } }), "原有 JSON 详情");
});

test("extracted incoming and settlement forms render scoped data and submit or close through the original callbacks", async () => {
  const { IncomingRegistrationModal, IncomingClaimModal } = loadModule("FinanceIncomingModals.tsx", {
    antd, "./constants": { money: (value) => `¥${value}` },
  });
  const { SettlementBatchModal } = loadModule("SettlementBatchModal.tsx", { antd });
  const calls = [];
  let tree;
  await act(async () => {
    tree = create(React.createElement(IncomingRegistrationModal, {
      open: true, form: {}, customers: [{ title: "客户甲", serial_no: "C-1" }],
      onSubmit: async () => calls.push("register"), onClose: () => calls.push("close-register"),
    }));
  });
  let modal = tree.root.findByType("modal");
  assert.equal(modal.props.title, "登记银行到账");
  assert.equal(tree.root.findByType("auto-complete").props.options[0].value, "客户甲");
  await act(async () => { await modal.props.onOk(); modal.props.onCancel(); });
  assert.deepEqual(calls, ["register", "close-register"]);

  await act(async () => {
    tree.update(React.createElement(IncomingClaimModal, {
      target: { id: 9, receipt_no: "R-9", amount: 100 }, form: {},
      customers: [{ id: 3, title: "客户乙", serial_no: "C-2" }], loading: false,
      onSearch: async (value) => calls.push(["search", value]),
      onSubmit: async () => calls.push("claim"), onClose: () => calls.push("close-claim"),
    }));
  });
  modal = tree.root.findByType("modal");
  assert.equal(modal.props.open, true);
  assert.equal(tree.root.findByType("select").props.options[0].label, "客户乙｜C-2");
  await act(async () => { tree.root.findByType("select").props.onSearch("客户乙"); await modal.props.onOk(); modal.props.onCancel(); });
  assert.deepEqual(calls.slice(2), [["search", "客户乙"], "claim", "close-claim"]);

  await act(async () => {
    tree.update(React.createElement(SettlementBatchModal, {
      open: true, loading: true, selectedCaseCount: 2, form: {},
      financePeople: [{ username: "lawyer", label: "张律师" }],
      onSubmit: async () => calls.push("settle"), onClose: () => calls.push("close-settle"),
    }));
  });
  modal = tree.root.findByType("modal");
  assert.equal(modal.props.confirmLoading, true);
  assert.match(tree.root.findByType("alert").props.title, /2 个案件/);
  assert.equal(tree.root.findAllByType("select")[0].props.options[0].value, "lawyer");
  await act(async () => { await modal.props.onOk(); modal.props.onCancel(); });
  assert.deepEqual(calls.slice(5), ["settle", "close-settle"]);
  await act(async () => tree.unmount());
});

test("merged payment document loads all selected records and propagates network failure", async () => {
  const requests = [];
  let failure = false;
  const { createFinanceDocumentsActions } = loadModule("services/documentsActions.tsx", {
    antd: { message: { error: () => {} } },
    "../../api": { api: { get: async (path) => {
      requests.push(path);
      if (failure) throw new Error("finance unavailable");
      const id = Number(path.match(/\d+/)[0]);
      return { data: { id, data: { amount: id * 10, document_groups: [{ id }] } } };
    } } },
    "../../formSafety": { formatRequiredDate: () => "" },
    "../constants": { attachmentRecordModule: () => "finance" },
  });
  const { loadMergedPaymentDocument } = createFinanceDocumentsActions({});
  const rows = [{ id: 1, data: { amount: 10 } }, { id: 2, data: { amount: 20 } }];
  const merged = await loadMergedPaymentDocument(rows);
  assert.deepEqual(requests, ["/finance/payment-workflow/1/document", "/finance/payment-workflow/2/document"]);
  assert.equal(merged.data.amount, 30);
  assert.equal(merged.data._open_print, true);
  assert.deepEqual(Array.from(merged.data._batch_ids), [1, 2]);
  assert.deepEqual(Array.from(merged.data.document_groups, (entry) => entry.id), [1, 2]);
  failure = true;
  await assert.rejects(loadMergedPaymentDocument(rows), /finance unavailable/);
});

test("batch fee subtype selection writes the chosen label into its form-list row", async () => {
  const { RefundBatchFeeDrawer } = loadModule("RefundBatchFeeDrawer.tsx", {
    antd,
    "@ant-design/icons": { MinusCircleOutlined: host("minus-icon"), PlusOutlined: host("plus-icon") },
  });
  const writes = [];
  const form = {
    getFieldValue: () => ({ case_no: "CASE-1", customer: "客户甲" }),
    setFieldValue: (path, value) => writes.push([Array.from(path), value]),
    validateFields: async () => {},
  };
  let tree;
  await act(async () => {
    tree = create(React.createElement(RefundBatchFeeDrawer, {
      open: true, kind: "ordinary", step: 0, onStepChange: () => {}, form,
      baseType: "代垫费", subTypes: [{ id: 3, name: "诉讼费" }], paymentTypes: [], loading: false,
      onClose: () => {}, onSubmit: async () => {}, onSyncFirstField: () => {},
      contracts: [], financePeople: [],
    }));
  });
  const feeTypeItem = tree.root.findAllByType("form-item").find((item) =>
    Array.isArray(item.props.name) && item.props.name[1] === "fee_type_id");
  assert.ok(feeTypeItem);
  await act(async () => feeTypeItem.findByType("select").props.onChange(3, { label: "诉讼费" }));
  assert.deepEqual(writes, [[["items", 0, "fee_type_name"], "诉讼费"]]);
  await act(async () => tree.unmount());
});

test("incoming detail discards a route's late response and shows a current request failure", async () => {
  const pending = [];
  const errors = [];
  const { useFinanceIncomingState } = loadModule("hooks/useFinanceIncomingState.ts", {
    antd: { Form: { useForm: () => [{}] }, message: { error: (value) => errors.push(value) } },
    "../../incomingPaymentDetailNavigation": { resolveIncomingPaymentDetailTarget: (route) => Number(route.slice(-1)) || null },
    "../financeErrors": { financeErrorDetail: (error) => error.message },
    "../services/accountingActions": { loadIncomingPaymentDetail: (id, financeScope, signal) => new Promise((resolve, reject) => pending.push({ id, financeScope, signal, resolve, reject })) },
  });
  let current;
  const Probe = ({ route }) => { current = useFinanceIncomingState(route, "firm"); return React.createElement("probe"); };
  let tree;
  await act(async () => { tree = create(React.createElement(Probe, { route: "detail-1" })); });
  assert.equal(pending[0].id, 1);
  assert.equal(pending[0].financeScope, "firm");
  assert.equal(current.incomingDetailLoading, true);
  await act(async () => tree.update(React.createElement(Probe, { route: "detail-2" })));
  assert.equal(pending[0].signal.aborted, true);
  await act(async () => pending[0].resolve({ id: 1 }));
  assert.equal(current.incomingDetailTarget, null);
  await act(async () => pending[1].resolve({ id: 2 }));
  assert.equal(current.incomingDetailTarget.id, 2);
  assert.equal(current.incomingDetailLoading, false);
  await act(async () => tree.update(React.createElement(Probe, { route: "detail-3" })));
  assert.equal(current.incomingDetailTarget, null);
  await act(async () => pending[2].reject(new Error("回款网络中断")));
  assert.equal(current.incomingDetailError, "回款网络中断");
  assert.equal(current.incomingDetailLoading, false);
  assert.equal(current.incomingDetailTarget, null);
  await act(async () => current.retryIncomingDetail());
  assert.equal(current.incomingDetailError, null);
  assert.equal(current.incomingDetailLoading, true);
  assert.equal(pending[3].id, 3);
  await act(async () => pending[3].resolve({ id: 3 }));
  assert.equal(current.incomingDetailTarget.id, 3);
  assert.equal(current.incomingDetailError, null);
  assert.deepEqual(errors, []);
  await act(async () => tree.unmount());
});

test("payment package editor aborts candidate loads after close and keeps the next selection", async () => {
  const pending = [];
  const form = { setFieldsValue: () => {}, resetFields: () => {} };
  const errors = [];
  const { usePaymentPackageWorkspaceState } = loadModule("hooks/usePaymentPackageWorkspaceState.ts", {
    antd: { Form: { useForm: () => [form] }, message: { error: (value) => errors.push(value) } },
    "../financeErrors": { financeErrorDetail: (error) => error.message },
    "../services/paymentsActions": { loadPaymentPackageCandidates: (target, signal) => new Promise((resolve, reject) => pending.push({ target, signal, resolve, reject })) },
  });
  let current;
  const Probe = () => { current = usePaymentPackageWorkspaceState(); return React.createElement("probe"); };
  let tree;
  await act(async () => { tree = create(React.createElement(Probe)); });
  await act(async () => current.openPaymentPackageEditor({ id: 1, data: { fee_ids: [10] } }));
  assert.equal(current.paymentPackageEditorOpen, true);
  assert.deepEqual(Array.from(current.paymentPackageSelectedFeeIds), [10]);
  await act(async () => current.closePaymentPackageEditor());
  assert.equal(pending[0].signal.aborted, true);
  await act(async () => pending[0].resolve([{ id: 10 }]));
  assert.equal(current.paymentPackageEditorOpen, false);
  assert.equal(current.paymentPackageCandidates.length, 0);
  await act(async () => current.openPaymentPackageEditor({ id: 2, data: { fee_ids: [20] } }));
  await act(async () => pending[1].resolve([{ id: 20 }]));
  assert.equal(current.paymentPackageCandidates[0].id, 20);
  assert.deepEqual(errors, []);
  await act(async () => tree.unmount());
});

test("finance domain services keep request paths, parameters, and rejected requests observable", async () => {
  const requests = [];
  let rejectNext = false;
  const record = async (method, path, value) => {
    requests.push({ method, path, value });
    if (rejectNext) { rejectNext = false; throw new Error("service unavailable"); }
    if (path === "/auth/me") return { data: { display_name: "申请人甲" } };
    if (path === "/finance/payment-types") return { data: { items: [{ id: 3 }] } };
    if (path === "/system/parameters/options") return { data: { items: [
      { id: 1, selectable: true, base_fee_type: "官方费用" },
      { id: 2, selectable: false, base_fee_type: "官方费用" },
    ] } };
    return { data: { items: [{ id: 7 }] } };
  };
  const api = {
    get: (path, options) => record("get", path, options),
    post: (path, payload) => record("post", path, payload),
    delete: (path) => record("delete", path),
  };
  const common = {
    antd: { message: {}, Modal: {} }, "../../api": { api },
    "../../formSafety": { formatRequiredDate: () => "" },
    "../constants": {}, "../invoiceDetails.mjs": { fetchInvoiceRecord: async () => ({ id: 7 }) },
    "../financeErrors": {}, "../../financeInvoiceHelpers.mjs": {},
    "../paymentLifecycle.mjs": {}, "../../financeRefundHelpers.mjs": {},
    "../../components/ResizableTable": () => null,
  };
  const accounting = loadModule("services/accountingActions.tsx", common);
  const invoices = loadModule("services/invoicesActions.tsx", common);
  const payments = loadModule("services/paymentsActions.tsx", common);
  const refunds = loadModule("services/refundsActions.tsx", common);
  const settlements = loadModule("services/settlementsActions.tsx", common);
  const workflow = loadModule("services/workflowActions.tsx", common);
  const signal = new AbortController().signal;

  await workflow.loadFinanceLinkedRecord(5, signal);
  await invoices.loadInvoiceApplicationContext({ serial_no: "F-5", customer: "客户甲", data: { customer_id: 8 } }, signal);
  assert.deepEqual(JSON.parse(JSON.stringify(requests[1].value.params)), {
    customer: "客户甲", customer_id: 8, keyword: "F-5", page: 1, page_size: 100,
  });
  assert.equal(requests[1].value.signal, signal);
  assert.equal(await refunds.loadRefundApplicantProfile(signal), "申请人甲");
  await accounting.loadIncomingPaymentDetail(9, "firm", signal);
  await payments.loadPaymentPackageCandidates({ id: 4 }, signal);
  await refunds.loadRefundBatchPaymentTypes(signal);
  assert.equal((await refunds.loadRefundBatchFeeSubTypes("官方费用", signal)).length, 1);
  await payments.voidRejectedPaymentApplication(11);
  await workflow.reviewFinanceFlowRequest("refunds", 12, false);
  await accounting.rollbackFinanceTransactionRequest(13);
  await invoices.withdrawInvoiceApplication(14);
  await payments.deletePaymentPackageRequest(15);
  await settlements.markSettlementCommissionPaid([16, 17], "firm");
  assert.deepEqual(requests.map(({ method, path }) => [method, path]), [
    ["get", "/records/5"], ["get", "/finance/invoice-context"], ["get", "/auth/me"],
    ["get", "/finance/incoming-payments/9"], ["get", "/finance/payment-packages/candidates"],
    ["get", "/finance/payment-types"], ["get", "/system/parameters/options"],
    ["post", "/finance/fees/11/void"], ["post", "/finance/refunds/12/review"],
    ["delete", "/finance/transactions/13"], ["post", "/finance/invoices/14/withdraw"],
    ["delete", "/finance/payment-packages/15"], ["post", "/finance/settlements/mark-commission-paid"],
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(requests[8].value)), { approved: false, comment: "资料不完整，退回修改" });
  assert.equal(requests[3].value.params.finance_scope, "firm");
  assert.deepEqual(JSON.parse(JSON.stringify(requests[12].value)), { fee_ids: [16, 17] });
  rejectNext = true;
  await assert.rejects(payments.deletePaymentPackageRequest(18), /service unavailable/);
});

test("invoice application state owns prefill, rejects mixed customers, and invalidates closing edits", async () => {
  const warnings = [];
  const fields = [];
  const form = { resetFields: () => fields.push("reset"), setFieldsValue: (value) => fields.push(value), getFieldValue: () => [] };
  const { useInvoiceApplicationState } = loadModule("hooks/useInvoiceApplicationState.ts", {
    antd: { Form: { useForm: () => [form] }, message: { warning: (value) => warnings.push(value) } },
    "../constants": {
      buildInvoiceSourceFields: (fees) => ({ customer: fees[0].customer }),
      invoiceFeeAvailableAmount: () => 80,
    },
  });
  let generation = 0;
  const sharedGuard = { begin: () => ++generation, isLatest: (token) => token === generation };
  let current;
  const Probe = ({ route }) => { current = useInvoiceApplicationState(route, sharedGuard); return React.createElement("probe"); };
  let tree;
  await act(async () => { tree = create(React.createElement(Probe, { route: "finance-invoice-mine" })); });
  await act(async () => current.openInvoiceFromFee({ id: 1, customer: "客户甲" }, [{ id: 8 }], { invoice_title: "甲公司" }));
  assert.equal(current.invoiceOpen, true);
  assert.deepEqual(Array.from(current.invoiceSelectedFeeIds), [1]);
  assert.equal(fields.at(-1).customer_record_id, 8);
  assert.equal(fields.at(-1).invoice_title, "甲公司");
  await act(async () => current.applyInvoiceFeeSelection([1, 2], [
    { id: 1, customer: "客户甲" }, { id: 2, customer: "客户乙" },
  ], [], []));
  assert.match(warnings.at(-1), /同一客户/);
  assert.deepEqual(Array.from(current.invoiceSelectedFeeIds), [1]);
  const token = sharedGuard.begin();
  await act(async () => current.closeInvoiceApplication());
  assert.equal(current.invoiceOpen, false);
  assert.equal(sharedGuard.isLatest(token), false);
  assert.equal(fields.at(-1), "reset");
  const routeToken = sharedGuard.begin();
  await act(async () => tree.update(React.createElement(Probe, { route: "finance-invoice-pending" })));
  assert.equal(sharedGuard.isLatest(routeToken), false);
  await act(async () => tree.unmount());
});

test("refund batch fee state keeps form defaults and discards option responses after close", async () => {
  const errors = [];
  const pending = [];
  const values = [];
  const form = {
    setFieldsValue: (value) => values.push(value), resetFields: () => values.push("reset"),
    getFieldValue: () => [], setFieldValue: () => {},
  };
  const deferred = (kind, signal) => new Promise((resolve, reject) => pending.push({ kind, signal, resolve, reject }));
  const { useRefundBatchFeeState } = loadModule("hooks/useRefundBatchFeeState.ts", {
    antd: { Form: { useForm: () => [form] }, message: { error: (value) => errors.push(value) } },
    "../financeErrors": { financeErrorDetail: (error) => error.message },
    "../services/refundsActions": {
      loadRefundBatchPaymentTypes: (signal) => deferred("payment", signal),
      loadRefundBatchFeeSubTypes: (_type, signal) => deferred("fee", signal),
    },
  });
  let current;
  const Probe = () => { current = useRefundBatchFeeState(); return React.createElement("probe"); };
  let tree;
  await act(async () => { tree = create(React.createElement(Probe)); });
  await act(async () => current.openRefundBatchFee("官方费用", [{ id: 7, serial_no: "CASE-7", customer: "客户甲", data: {} }], "lawyer"));
  assert.equal(current.refundBatchFeeOpen, true);
  assert.equal(values[0].handler, "lawyer");
  assert.equal(values[0].items[0].case_no, "CASE-7");
  await act(async () => pending.find((item) => item.kind === "payment").reject(new Error("收款选项失败")));
  assert.equal(errors.at(-1), "收款选项失败");
  await act(async () => current.closeRefundBatchFee());
  assert.equal(pending[1].signal.aborted, true);
  await act(async () => pending[1].resolve([{ id: 9 }]));
  assert.equal(current.refundBatchFeeSubTypes.length, 0);
  assert.equal(current.refundBatchFeeOpen, false);
  assert.equal(values.at(-1), "reset");
  await act(async () => tree.unmount());
});

test("invoice edit service opens hydrated draft, suppresses a closed request, and exposes loading errors", async () => {
  const notices = [];
  const formWrites = [];
  let deferContext = false;
  let resolveContext;
  let failContext = false;
  const api = { get: async (path) => {
    if (path.startsWith("/finance/invoices/")) return { data: { id: Number(path.split("/").at(-1)), module: "invoice", data: {} } };
    assert.equal(path, "/finance/invoice-context");
    if (failContext) throw new Error("发票上下文不可用");
    if (deferContext) return new Promise((resolve) => { resolveContext = resolve; });
    return { data: { items: [], selected_items: [], customer_defaults: { invoice_title: "甲公司" } } };
  } };
  const { createFinanceInvoicesActions } = loadModule("services/invoicesActions.tsx", {
    antd: { message: { error: (value) => notices.push(value), warning: (value) => notices.push(value) }, Modal: {} },
    "../../api": { api }, "../../financeInvoiceHelpers.mjs": {},
    "../../formSafety": { formatRequiredDate: () => "" }, "../constants": {},
    "../financeErrors": { financeErrorDetail: () => undefined, financeErrorMessageText: (error) => error.message },
    "../invoiceDetails.mjs": {
      fetchInvoiceRecord: async () => ({ id: 7, customer: "客户甲", status: "草稿", data: {} }),
      invoiceEditValues: () => ({ case_fee_ids: [3], case_fee_allocations: [{ fee_id: 3, amount: 100 }] }),
      invoiceCurrentSourceFields: () => ({ external_contract_no: "CON-3" }),
    },
  });
  let generation = 0;
  let open = false;
  let editTarget = null;
  let selectedIds = [];
  let candidateFees = [];
  let detail = null;
  const setCandidates = (update) => { candidateFees = typeof update === "function" ? update(candidateFees) : update; };
  const form = {
    getFieldValue: () => [], resetFields: () => formWrites.push("reset"),
    setFieldsValue: (value) => formWrites.push(value),
  };
  const actions = createFinanceInvoicesActions({
    invoiceDetailRequestGuard: { begin: () => ++generation, isLatest: (token) => token === generation },
    setInvoiceDetail: (value) => { detail = value; },
    invoiceForm: form, invoiceEditTarget: null,
    setInvoiceOpen: (value) => { open = value; },
    setInvoiceEditTarget: (value) => { editTarget = value; },
    setInvoiceSelectedFeeIds: (value) => { selectedIds = value; },
    setContracts: () => {}, setCustomers: () => {}, setInvoiceCandidateFees: setCandidates,
  });
  await actions.openInvoiceEdit({ id: 7 });
  assert.equal(open, true);
  assert.equal(editTarget.id, 7);
  assert.deepEqual(Array.from(selectedIds), [3]);
  assert.equal(formWrites.at(-1).invoice_title, "甲公司");
  assert.equal(formWrites.at(-1).external_contract_no, "CON-3");

  open = false;
  deferContext = true;
  const late = actions.openInvoiceEdit({ id: 7 });
  await new Promise(setImmediate);
  generation += 1;
  resolveContext({ data: { items: [{ id: 99 }], selected_items: [] } });
  await late;
  assert.equal(open, false);
  assert.equal(candidateFees.length, 0);
  deferContext = true;
  const crossActionEdit = actions.openInvoiceEdit({ id: 7 });
  await new Promise(setImmediate);
  await actions.openInvoiceDetail({ id: 8 });
  assert.equal(detail.id, 8);
  const writesAfterDetail = formWrites.length;
  resolveContext({ data: { items: [{ id: 77 }], selected_items: [] } });
  await crossActionEdit;
  assert.equal(open, false, "late edit must not reopen after invoice detail takes focus");
  assert.equal(formWrites.length, writesAfterDetail);
  assert.equal(candidateFees.length, 0);
  deferContext = false;
  failContext = true;
  await actions.openInvoiceEdit({ id: 7 });
  assert.equal(notices.at(-1), "发票上下文不可用");
});

test("linked finance detail consumes each target once, cancels a stale route, and propagates current failures", async () => {
  const targets = [
    { id: 1, action: "create_invoice" }, { id: 2, action: "create_refund" },
    { id: 3, action: "create_invoice" }, { id: 4, action: "view" },
  ];
  const records = [];
  const contexts = [];
  const profiles = [];
  const errors = [];
  const results = [];
  const pending = (queue, id, signal) => new Promise((resolve, reject) => queue.push({ id, signal, resolve, reject }));
  const { useFinanceLinkedDetail } = loadModule("hooks/useFinanceLinkedDetail.ts", {
    antd: { message: { error: (value) => errors.push(value) } },
    "../../businessRecordDetailNavigation": { consumeBusinessRecordDetailTarget: () => targets.shift() || null },
    "../financeErrors": { financeErrorDetail: (error) => error.message, financeErrorMessageText: () => "" },
    "../services/workflowActions": { loadFinanceLinkedRecord: (id, signal) => pending(records, id, signal) },
    "../services/invoicesActions": {
      loadInvoiceApplicationContext: (record, signal) => pending(contexts, record.id, signal),
      loadInvoiceRecord: () => { throw new Error("unexpected invoice detail request"); },
    },
    "../services/refundsActions": { loadRefundApplicantProfile: (signal) => pending(profiles, 0, signal) },
  });
  const Probe = ({ route }) => {
    const [, rerender] = React.useState(0);
    useFinanceLinkedDetail(route, (result) => { results.push(result); rerender((value) => value + 1); });
    return React.createElement("probe");
  };
  let tree;
  await act(async () => { tree = create(React.createElement(Probe, { route: "invoice-1" })); });
  await act(async () => records[0].resolve({ id: 1, module: "finance", data: {} }));
  assert.equal(contexts[0].id, 1);
  await act(async () => tree.update(React.createElement(Probe, { route: "refund-2" })));
  assert.equal(records[0].signal.aborted, true);
  assert.equal(contexts[0].signal.aborted, true);
  await act(async () => records[1].resolve({ id: 2, module: "finance", data: { amount: 25 } }));
  await act(async () => profiles[0].resolve("申请人甲"));
  assert.equal(results[0].kind, "refund-creation");
  assert.equal(results[0].applicantName, "申请人甲");
  assert.equal(targets.length, 2, "callback rerender must not consume another target");
  await act(async () => contexts[0].resolve({ items: [{ id: 1 }] }));
  assert.equal(results.length, 1, "late invoice context must not overwrite the new route");

  await act(async () => tree.update(React.createElement(Probe, { route: "invoice-3" })));
  await act(async () => records[2].resolve({ id: 3, module: "finance", data: {} }));
  await act(async () => contexts[1].resolve({ items: [{ id: 99 }], customer_defaults: { invoice_title: "乙公司" } }));
  assert.equal(results[1].kind, "invoice-creation");
  assert.equal(results[1].sourceFee, undefined, "ineligible source must not be represented as a valid invoice fee");
  assert.equal(results[1].customerDefaults.invoice_title, "乙公司");

  await act(async () => tree.update(React.createElement(Probe, { route: "detail-4" })));
  await act(async () => records[3].reject(new Error("关联详情请求失败")));
  assert.equal(errors.at(-1), "关联详情请求失败");
  assert.equal(results.length, 2);
  await act(async () => tree.unmount());
});

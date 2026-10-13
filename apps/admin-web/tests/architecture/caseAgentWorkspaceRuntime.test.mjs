import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";
import { AxiosError } from "axios";
import React from "react";
import { act, create } from "react-test-renderer";
import ts from "typescript";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const require = createRequire(import.meta.url);
const sourceRoot = new URL("../../src/legal/", import.meta.url);

function loadModule(name, dependencies, globals = {}) {
  const entry = fileURLToPath(new URL(name, sourceRoot));
  const compilerOptions = { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true };
  const modules = new Map();
  const overrides = new Map();
  const resolveLocal = (specifier, filename) => {
    const resolved = ts.resolveModuleName(specifier, filename, compilerOptions, ts.sys).resolvedModule;
    if (!resolved) throw new Error(`无法解析测试依赖：${specifier}，导入文件：${filename}`);
    return resolved.resolvedFileName;
  };
  // 相对依赖按导入文件解析，已有注入只作用于对应模块，其他依赖加载真实源码。
  for (const [specifier, dependency] of Object.entries(dependencies)) {
    if (specifier.startsWith(".")) overrides.set(resolveLocal(specifier, entry), dependency);
  }
  const loadSource = (filename) => {
    if (modules.has(filename)) return modules.get(filename).exports;
    const source = fs.readFileSync(filename, "utf8");
    const output = ts.transpileModule(source, { compilerOptions, fileName: filename }).outputText;
    const module = { exports: {} };
    modules.set(filename, module);
    const localRequire = createRequire(filename);
    vm.runInNewContext(output, {
      module, exports: module.exports,
      require: (specifier) => {
        if (!specifier.startsWith(".")) return Object.hasOwn(dependencies, specifier) ? dependencies[specifier] : localRequire(specifier);
        if (specifier.endsWith(".css")) {
          // Node 行为测试不执行样式，但必须确认真实样式文件存在。
          fs.accessSync(new URL(specifier, pathToFileURL(filename)));
          return {};
        }
        const resolved = resolveLocal(specifier, filename);
        return overrides.has(resolved) ? overrides.get(resolved) : loadSource(resolved);
      },
      Error, AbortController, TextDecoder, Uint8Array, ...globals,
    }, { filename });
    return module.exports;
  };
  return loadSource(entry);
}

test("agent service streams an answer, records an approval, and exposes upstream failures", async () => {
  const notices = [];
  const messages = { error: (value) => notices.push(["error", value]), success: (value) => notices.push(["success", value]), warning: (value) => notices.push(["warning", value]) };
  const requests = [];
  let failFetch = false;
  let failApproval = false;
  const fetch = async (url, options) => {
    requests.push({ url, options });
    if (failFetch) return { ok: false, json: async () => ({ detail: "model_http_error" }) };
    const chunks = [new TextEncoder().encode('{"type":"delta","content":"第一段"}\n{"type":"delta","content":"第二段"}\n')];
    return { ok: true, body: { getReader: () => ({ read: async () => chunks.length ? { done: false, value: chunks.shift() } : { done: true } }) } };
  };
  const api = { post: async (path, payload, options) => {
    requests.push({ path, payload, options });
    if (failApproval) throw new AxiosError("审批被拒绝", undefined, undefined, undefined, { data: { detail: "审批被拒绝" } });
    return { data: { messages: [], pending_actions: [{ id: "a1", status: "approved" }] } };
  } };
  const { createCaseAssistantActions } = loadModule("services/assistantActions.tsx", {
    antd: { ...require("antd"), message: messages },
    "../../agentSkillRouting": { DEFAULT_AGENT_SKILL: "qa", encodeAgentSkillMessage: (_skill, value) => value },
    "../../api": { api },
    "../constants": {
      AGENT_DOCUMENT_LIMIT: 4, aiWordDocumentName: () => "answer.docx",
      isAiWordGenerationRequest: () => false, isExistingAnswerWordConversionRequest: () => false,
      isUsableAiDocumentContent: () => false,
    },
  }, { fetch, localStorage: { getItem: () => null } });
  let state = { messages: [], pending_actions: [] };
  let input = "案件进度如何";
  let sending = false;
  let decisionLoading = "";
  const activeRef = { current: null };
  const setState = (update) => { state = typeof update === "function" ? update(state) : update; };
  const context = {
    agentCase: { id: 8 }, get agentInput() { return input; }, agentSkillId: "qa", agentScreenshots: [],
    get agentState() { return state; }, get agentSending() { return sending; }, activeCaseAgentRequestRef: activeRef,
    agentDocumentIds: [], agentDocuments: [], viewingCounselCase: null,
    get agentDecisionLoading() { return decisionLoading; },
    setAgentState: setState, setAgentInput: (value) => { input = value; },
    setAgentSending: (value) => { sending = value; }, setAgentDecisionLoading: (value) => { decisionLoading = value; },
    setAgentSkillId: () => {}, setAgentScreenshots: () => {}, setAgentDocumentIds: () => {},
    setAgentMaterialPickerOpen: () => {}, stateWithAgentScreenshotPreviews: (value) => value,
    refreshCounselDetailAttachments: async () => {}, selectCounselDocCategory: () => {},
  };
  const actions = createCaseAssistantActions(context);
  await actions.sendCaseAgentMessage();
  assert.equal(requests[0].url, "/api/v1/case-spaces/8/agent/messages");
  assert.equal(JSON.parse(requests[0].options.body).message, "案件进度如何");
  assert.equal(state.messages.at(-1).content, "第一段第二段");
  assert.equal(input, "");
  assert.equal(sending, false);
  assert.equal(activeRef.current, null);

  await actions.decideCaseAgentAction({ id: "a1" }, "approved");
  assert.equal(requests.at(-1).path, "/case-spaces/8/agent/actions/a1/decision");
  assert.equal(requests.at(-1).payload.decision, "approved");
  assert.equal(requests.at(-1).options.headers["X-OA-Agent-Confirmation"], "frontend");
  assert.equal(state.pending_actions[0].status, "approved");
  assert.equal(decisionLoading, "");

  failApproval = true;
  await actions.decideCaseAgentAction({ id: "a1" }, "rejected");
  assert.equal(requests.at(-1).payload.decision, "rejected");
  assert.equal(notices.at(-1)[1], "审批被拒绝");
  assert.equal(decisionLoading, "");

  failFetch = true;
  await actions.sendCaseAgentMessage("请重试");
  assert.match(state.messages.at(-1).content, /模型本轮生成失败/);
  assert.equal(notices.at(-1)[0], "error");
  assert.equal(sending, false);
});

test("real approval preview loads the shared table and preserves original values and confirmation guards", () => {
  const { AgentOperationPreview, agentOperationError, hasAgentOperationPreview } = loadModule("../AgentOperationPreview.tsx", {});
  const action = {
    id: "a1", type: "case.update", summary: "修改经办律师",
    preview: { changes: [{ field: "handling_lawyers", before: "原律师", before_read: true, after: "新律师" }] },
  };
  const preview = AgentOperationPreview({ action });
  const table = React.Children.toArray(preview.props.children).find((child) => child.type?.name === "ResizableTable");
  assert.ok(table, "预览必须加载真实的统一列宽组件");
  assert.equal(table.props.rowKey, "field");
  assert.equal(table.props.pagination, false);
  assert.equal(table.props.scroll.x, 480);
  assert.equal(table.props.dataSource, action.preview.changes);
  assert.equal(table.props.columns[0].render("handling_lawyers"), "经办律师 (handling_lawyers)");
  const before = table.props.columns[1].render;
  const after = table.props.columns[2].render;
  assert.equal(before("原律师", { before_read: true }).props.children, "原律师");
  assert.equal(before("原律师", { before_read: false }).props.children, "未读取");
  assert.equal(before(undefined, { before_read: true }).props.children, "未读取");
  assert.equal(before(null, { before_read: true }).props.children, "空值 (null)");
  assert.equal(after("新律师").props.children, "新律师");
  assert.equal(after("").props.children, "空字符串");
  const created = AgentOperationPreview({ action: { ...action, preview: { ...action.preview, create: { title: "新建任务" } } } });
  assert.equal(React.Children.toArray(created.props.children).some((child) => child.type === table.type), false);
  const mcp = { id: "r1", type: "mcp.call", summary: "修改案件", payload: { request_id: "r1" }, preview: {
    operation_name: "修改案件字段", method: "PATCH", path: "/cases/8", params: { body: { title: "新名称" } }, requires_confirmation: true,
  } };
  assert.equal(hasAgentOperationPreview(mcp), true);
  assert.equal(hasAgentOperationPreview({ ...mcp, preview: { ...mcp.preview, requires_confirmation: false } }), false);
  assert.equal(hasAgentOperationPreview({ ...mcp, payload: {} }), false);
  assert.equal(agentOperationError(new AxiosError("request failed", undefined, undefined, undefined, { data: { detail: "权限不足" } }), "操作失败"), "权限不足");
  assert.equal(agentOperationError(new Error("网络中断"), "操作失败"), "网络中断");
});

test("personal confirmation history only reads decided records with paging, errors and cancellation", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const Empty = component("empty");
  Empty.PRESENTED_IMAGE_SIMPLE = "simple";
  const requests = [];
  const { ConfirmationHistory } = loadModule("../personal-agent/ConfirmationHistory.tsx", {
    antd: {
      ...require("antd"),
      Alert: component("alert"), Button: component("button"), Empty, Pagination: component("pagination"),
      Select: component("select"), Spin: component("spin"), Tag: component("tag"), Tooltip: component("tooltip"),
      Drawer: ({ open, children, ...props }) => open ? React.createElement("drawer", props, children) : null,
    },
    "../api": { api: { get: (path, options) => new Promise((resolve, reject) => requests.push({ path, options, resolve, reject })) } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(ConfirmationHistory)); });
  assert.equal(requests.length, 0, "未打开历史时不查询");
  assert.equal(renderer.root.findByProps({ className: "confirmation-history-label" }).props.children, "历史确认记录", "历史入口保留可见文字，不只依赖图标");
  await act(async () => renderer.root.findByProps({ "aria-label": "历史确认记录" }).props.onClick());
  assert.equal(renderer.root.findByType("drawer").props.rootClassName, "confirmation-history-drawer", "宽度限制作用域必须位于抽屉根节点，才能命中内容 wrapper");
  assert.equal(requests[0].path, "/personal-agent/confirmation-history");
  assert.equal(JSON.stringify(requests[0].options.params), JSON.stringify({ page: 1, page_size: 20 }));
  assert.equal(renderer.root.findByType("select").props.options.some((option) => option.value === "pending"), false);
  assert.equal(renderer.root.findByType("spin").type, "spin");
  const record = { id: "r1", source: "mcp", action_type: "batch", summary: "为2个案件新增期限提醒", status: "succeeded", requested_at: "2026-10-13T02:00:00Z", decided_at: "2026-10-13T02:01:00Z", finished_at: null, operator: "审核人", comment: "同意", result: { count: 2, message: "已生成期限提醒" }, error: null, conversation_id: null, conversation_title: null };
  await act(async () => requests[0].resolve({ data: { items: [record], total: 21, page: 1, page_size: 20 } }));
  assert.equal(renderer.root.findByType("strong").props.children, "为2个案件新增期限提醒");
  assert.equal(renderer.root.findByType("tag").props.children, "已执行");
  assert.equal(renderer.root.findByType("summary").props.children, "执行结果");
  assert.equal(renderer.root.findByType("details").props.open, undefined, "完整结果默认折叠");
  assert.deepEqual(JSON.parse(renderer.root.findByType("pre").props.children), record.result);
  assert.equal(renderer.root.findAllByType("button").length, 2, "历史只保留打开与刷新，不提供重放按钮");
  await act(async () => renderer.root.findByType("pagination").props.onChange(2));
  assert.equal(requests[1].options.params.page, 2);
  assert.equal(requests[0].options.signal.aborted, true);
  await act(async () => renderer.root.findByType("select").props.onChange("failed"));
  assert.equal(requests[2].options.params.page, 1);
  assert.equal(requests[2].options.params.status, "failed");
  assert.equal(requests[1].options.signal.aborted, true);
  await act(async () => requests[1].resolve({ data: { items: [record], total: 21, page: 2, page_size: 20 } }));
  assert.equal(renderer.root.findAllByType("li").length, 0, "已取消的旧页不能覆盖新筛选");
  await act(async () => requests[2].reject(new AxiosError("失败", undefined, undefined, undefined, { data: { detail: "权限已变更" } })));
  assert.equal(renderer.root.findByType("alert").props.description, "权限已变更");
  assert.equal(renderer.root.findAllByType("empty").length, 0, "失败不能伪装空记录");
  await act(async () => renderer.root.findByProps({ "aria-label": "刷新确认记录" }).props.onClick());
  await act(async () => requests[3].resolve({ data: { items: [], total: 0, page: 1, page_size: 20 } }));
  assert.equal(renderer.root.findByType("empty").props.description, "此状态下暂无确认记录");
  await act(async () => renderer.root.findByProps({ "aria-label": "刷新确认记录" }).props.onClick());
  await act(async () => renderer.root.findByType("drawer").props.onClose());
  assert.equal(requests[4].options.signal.aborted, true);
  await act(async () => renderer.unmount());
});

test("personal confirmation keeps failed cards and disables all decisions while executing", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  let closed = 0;
  let decisions = 0;
  const notices = [];
  const { ActionConfirmation } = loadModule("../personal-agent/ActionConfirmation.tsx", {
    antd: { Alert: component("alert"), Button: component("button"), Modal: ({ footer, children, ...props }) => React.createElement("modal", props, children, footer), Space: component("space"), Spin: component("spin"), Tag: component("tag"), message: { error: (value) => notices.push(value) } },
    "../AgentOperationPreview": {
      AgentOperationPreview: component("preview"), hasAgentOperationPreview: () => true,
      agentOperationError: (failure) => failure.message, agentOperationMessage: (value) => String(value),
    },
  });
  const action = { id: "a1", type: "create_task", summary: "为张三新建合同复核任务", status: "pending" };
  const props = { action, deciding: false, onClose: () => closed++, onDecide: async () => { decisions++; throw new Error("原有业务权限拒绝"); } };
  let renderer;
  await act(async () => { renderer = create(React.createElement(ActionConfirmation, props)); });
  await act(async () => renderer.root.findAllByType("button").find((button) => button.props.children === "确认并执行").props.onClick());
  assert.equal(decisions, 1);
  assert.equal(closed, 0, "失败不得关闭或丢弃待确认卡");
  assert.equal(renderer.root.findByType("preview").props.action, action);
  assert.equal(renderer.root.findByType("alert").props.description, "原有业务权限拒绝");
  assert.deepEqual(notices, ["原有业务权限拒绝"]);
  await act(async () => renderer.update(React.createElement(ActionConfirmation, { ...props, deciding: true })));
  assert.ok(renderer.root.findAllByType("button").every((button) => button.props.disabled));
  const modal = renderer.root.findByType("modal");
  assert.equal(modal.props.maskClosable, false);
  assert.equal(modal.props.keyboard, false);
  assert.equal(modal.props.closable, false);
  await act(async () => modal.props.onCancel());
  assert.equal(closed, 0);
  await act(async () => renderer.unmount());
});

test("homepage pending summary is shown once and direct cancellation retains failures", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const List = ({ dataSource, renderItem }) => React.createElement("list", null, dataSource.map((item) => React.cloneElement(renderItem(item), { key: item.id })));
  List.Item = ({ actions, children }) => React.createElement("list-item", null, children, actions);
  List.Item.Meta = component("list-meta");
  const { default: AssistantPanel } = loadModule("../personal-agent/AssistantPanel.tsx", {
    antd: { ...require("antd"), Alert: component("alert"), Button: component("button"), Input: { TextArea: component("textarea") }, List, Tooltip: component("tooltip") },
    "./AssistantStart": { __esModule: true, default: component("start"), shortcuts: [] },
    "./ConversationManager": { ConversationManager: component("conversation-manager") },
    "./AssistantWorkspaceTools": { AssistantWorkspaceTools: component("workspace-tools") },
    "./ConfirmationHistory": { ConfirmationHistory: component("confirmation-history") },
    "./ActionConfirmation": { ActionConfirmation: component("action-confirmation") },
  });
  const action = { id: "a1", type: "mcp.call", summary: "为2个案件新增期限提醒", status: "pending" };
  const decisions = [];
  const workspace = {
    status: { ready: true }, state: { messages: [], pending_actions: [action], conversation_id: "c1" },
    loading: false, loadError: "", sending: false, stopping: false, input: "", conversations: [], runningIds: [],
    conversationBusy: false, uploading: false, decisionId: "", setInput: () => {}, send: () => {}, stop: () => {}, load: () => {},
    decide: async (item, decision) => { decisions.push([item.id, decision]); throw new Error("取消被原权限拒绝"); },
  };
  const props = { workspace, suggestions: [], focusRequested: false, onFocusHandled: () => {} };
  let renderer;
  await act(async () => { renderer = create(React.createElement(AssistantPanel, props)); });
  const meta = renderer.root.findByType("list-meta");
  assert.equal(meta.props.title, action.summary);
  assert.equal(meta.props.description, undefined, "不重复标题和摘要");
  assert.equal(renderer.root.findAllByType("confirmation-history").length, 1);
  assert.equal(renderer.root.findAllByType("conversation-manager").length, 1, "对话历史仍保留");
  const button = (label) => renderer.root.findAllByType("button").find((item) => item.props.children === label);
  await act(async () => button("取消").props.onClick());
  assert.deepEqual(decisions, [["a1", "rejected"]]);
  assert.equal(renderer.root.findByType("alert").props.description, "取消被原权限拒绝");
  assert.equal(renderer.root.findAllByType("list-meta").length, 1);
  await act(async () => button("查看并确认").props.onClick());
  assert.equal(renderer.root.findByType("action-confirmation").props.action, action);
  assert.equal(decisions.length, 1, "查看预览不能直接批准");
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, decisionId: "a1" } })));
  assert.equal(button("取消").props.disabled, true);
  assert.equal(button("查看并确认").props.disabled, true);
  await act(async () => button("取消").props.onClick());
  assert.equal(decisions.length, 1);
  await act(async () => renderer.unmount());
});

test("agent workspace releases screenshot URLs on removal and unmount, and reports upload failures", async () => {
  const notices = [];
  const urls = [];
  let failUpload = false;
  let pendingUpload = false;
  let resolveUpload;
  let uploadSignal;
  let streamController;
  const api = { post: async (_path, _form, options) => {
    if (pendingUpload) {
      uploadSignal = options.signal;
      return new Promise((resolve) => { resolveUpload = resolve; });
    }
    if (failUpload) throw { response: { data: { detail: "上传失败：网络中断" } } };
    return { data: { attachment: { id: urls.length + 1, original_name: "shot.png" } } };
  } };
  const urlApi = {
    createObjectURL: () => { const url = `blob:shot-${urls.length + 1}`; urls.push(["create", url]); return url; },
    revokeObjectURL: (url) => urls.push(["revoke", url]),
  };
  class FormDataMock { append() {} }
  const { useCaseAgentWorkspace } = loadModule("hooks/useCaseAgentWorkspace.ts", {
    antd: { message: { error: (value) => notices.push(value), warning: (value) => notices.push(value), success: () => {}, info: () => {} } },
    "../../agentSkillRouting": { DEFAULT_AGENT_SKILL: "qa" },
    "../../api": { api },
    "../constants": { AGENT_DOCUMENT_LIMIT: 4 },
    "../services/assistantActions": { createCaseAssistantActions: (context) => ({
      loadCaseAgent: async () => {}, sendCaseAgentMessage: async () => {
        streamController = new AbortController();
        context.activeCaseAgentRequestRef.current = streamController;
      },
      decideCaseAgentAction: async () => {}, restoreCaseAgentAction: async () => {},
    }) },
    "./useCaseAgentDrawer": { useCaseAgentDrawer: () => ({ agentDrawerWidth: 600, startAgentDrawerResize: () => {} }) },
  }, { URL: urlApi, FormData: FormDataMock, requestAnimationFrame: (callback) => callback() });
  let current;
  function Probe() {
    current = useCaseAgentWorkspace({ viewingCounselCase: null, refreshCounselDetailAttachments: async () => {}, selectCounselDocCategory: () => {} });
    return React.createElement("probe", { open: current.drawerProps.agentOpen });
  }
  let tree;
  await act(async () => { tree = create(React.createElement(Probe)); });
  await act(async () => current.openCaseAgent({ id: 8 }));
  assert.equal(current.drawerProps.agentOpen, true);
  const file = { name: "shot.png", type: "image/png", size: 100 };
  await act(async () => current.drawerProps.uploadCaseAgentScreenshot(file));
  assert.equal(current.drawerProps.agentScreenshots.length, 1);
  assert.deepEqual(urls, [["create", "blob:shot-1"]]);
  await act(async () => current.drawerProps.removeAgentScreenshot(current.drawerProps.agentScreenshots[0]));
  assert.equal(current.drawerProps.agentScreenshots.length, 0);
  assert.deepEqual(urls.at(-1), ["revoke", "blob:shot-1"]);
  await act(async () => current.drawerProps.uploadCaseAgentScreenshot(file));
  failUpload = true;
  await act(async () => current.drawerProps.uploadCaseAgentScreenshot(file));
  assert.equal(current.drawerProps.agentScreenshotUploading, false);
  assert.equal(notices.at(-1), "上传失败：网络中断");
  failUpload = false;
  pendingUpload = true;
  let uploadResult;
  await act(async () => { uploadResult = current.drawerProps.uploadCaseAgentScreenshot(file); });
  assert.equal(current.drawerProps.agentScreenshotUploading, true);
  await act(async () => current.drawerProps.sendCaseAgentMessage());
  assert.equal(streamController.signal.aborted, false);
  await act(async () => tree.unmount());
  assert.equal(uploadSignal.aborted, true);
  assert.equal(streamController.signal.aborted, true);
  assert.deepEqual(urls.at(-1), ["revoke", "blob:shot-3"]);
  const urlCount = urls.length;
  await act(async () => {
    resolveUpload({ data: { attachment: { id: 99, original_name: "late.png" } } });
    await uploadResult;
  });
  assert.equal(urls.length, urlCount);
});

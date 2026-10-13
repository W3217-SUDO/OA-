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
  for (const [status, label] of [["failed", "执行失败"], ["succeeded", "已执行"], ["rejected", "已取消"], ["executing", "执行中"], ["approved", "已批准"]]) {
    const terminal = { ...action, status, error: status === "failed" ? "真实的非 MCP 业务拒绝" : undefined };
    await act(async () => renderer.update(React.createElement(ActionConfirmation, { ...props, action: terminal })));
    assert.equal(renderer.root.findByType("tag").props.children, label);
    assert.equal(renderer.root.findAllByType("button").some((button) => button.props.children === "确认并执行"), false);
    if (status === "failed") assert.equal(renderer.root.findAllByType("alert")[0].props.description, "真实的非 MCP 业务拒绝");
    if (status === "approved") assert.equal(renderer.root.findByType("tag").props.color, "processing", "已批准不冒称执行成功");
  }
  await act(async () => renderer.update(React.createElement(ActionConfirmation, props)));
  assert.equal(renderer.root.findByType("tag").props.children, "待确认", "无 PA 存档的原 pending 请求保留人工确认入口");
  assert.equal(renderer.root.findAllByType("button").find((button) => button.props.children === "确认并执行").props.disabled, false);
  await act(async () => renderer.unmount());
});

test("homepage pending summary is shown once and direct cancellation retains failures", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const List = ({ dataSource, renderItem }) => React.createElement("list", null, dataSource.map((item) => React.cloneElement(renderItem(item), { key: item.id })));
  List.Item = ({ actions, children }) => React.createElement("list-item", null, children, actions);
  List.Item.Meta = ({ title, description }) => React.createElement("list-meta", { title, description }, description);
  const { default: AssistantPanel } = loadModule("../personal-agent/AssistantPanel.tsx", {
    antd: { ...require("antd"), Alert: component("alert"), Button: component("button"), Input: { TextArea: component("textarea") }, List, Tag: component("tag"), Tooltip: component("tooltip") },
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
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, sending: true, runningIds: ["c1"] } })));
  assert.equal(button("查看并确认").props.disabled, false, "生成不能阻止人工查看已有待确认操作");
  assert.equal(button("取消").props.disabled, false, "取消由工作区等待服务端释放生成锁");
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, decisionId: "a1" } })));
  assert.equal(button("取消").props.disabled, true);
  assert.equal(button("查看并确认").props.disabled, true);
  await act(async () => button("取消").props.onClick());
  assert.equal(decisions.length, 1);
  const failed = { ...action, status: "failed", error: { status_code: 409, detail: { detail: "任务由案件阶段自动完成，人工只能变更期限" } } };
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, state: { ...workspace.state, pending_actions: [failed] } } })));
  assert.equal(renderer.root.findByType("tag").props.children, "执行失败");
  assert.equal(renderer.root.findByType("alert").props.title, "任务由案件阶段自动完成，人工只能变更期限");
  assert.equal(button("查看并确认"), undefined);
  assert.equal(button("取消"), undefined);
  await act(async () => button("查看状态").props.onClick());
  assert.equal(renderer.root.findByType("action-confirmation").props.action.status, "failed");
  assert.equal(decisions.length, 1, "失败卡只读查看，不能重复执行");
  await act(async () => renderer.unmount());
});

test("personal center retains terminal outcomes as visible read-only cards", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const action = { id: "a1", type: "mcp.call", status: "failed", summary: "旧批量任务", error: { detail: { detail: "任务由案件阶段自动完成，人工只能变更期限" } } };
  const workspace = {
    status: { ready: true, commands: [] }, state: { conversation_id: "c1", messages: [], pending_actions: [action] },
    skills: [], skillId: "general-office", input: "", loading: false, sending: true, uploading: false,
    materials: [], caseMaterials: [], savedDocuments: {}, conversations: [], runningIds: ["c1"],
    decisionId: "", conversationBusy: false,
  };
  const { default: PersonalAgentCenterPage } = loadModule("../PersonalAgentCenterPage.tsx", {
    antd: { ...require("antd"), Alert: component("alert"), Button: component("button"), Input: { TextArea: component("textarea") }, Select: component("select"), Segmented: component("segmented"), Space: component("space"), Tag: component("tag"), Tooltip: component("tooltip") },
    "./personal-agent/usePersonalWorkspace": { usePersonalWorkspace: () => workspace },
    "./personal-agent/WorkPanel": { WorkPanel: component("work-panel") },
    "./personal-agent/ConversationManager": { ConversationManager: component("conversations") },
    "./personal-agent/MobileComposerOptions": { MobileComposerOptions: component("mobile-options") },
    "./personal-agent/SkillManager": { SkillManager: component("skills") },
    "./personal-agent/MaterialPreview": { MaterialPreview: component("materials") },
    "./personal-agent/CaseMaterialsPicker": { CaseMaterialsPicker: component("picker") },
    "./personal-agent/ActionConfirmation": { ActionConfirmation: component("confirmation") },
    "./personal-agent/ConfirmationHistory": { ConfirmationHistory: component("history") },
    "./AgentToolRequests": { AgentToolRequests: component("tool-requests") },
    "./AgentToolResult": { AgentToolResult: component("tool-result") },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalAgentCenterPage, { onNavigate() {} })); });
  const button = (label) => renderer.root.findAllByType("button").find((item) => item.props.children === label);
  assert.equal(button("查看并确认"), undefined);
  assert.equal(button("查看状态").props.disabled, false);
  assert.equal(renderer.root.findByType("alert").props.title, "任务由案件阶段自动完成，人工只能变更期限");
  await act(async () => button("查看状态").props.onClick());
  assert.equal(renderer.root.findByType("confirmation").props.action.status, "failed");
  await act(async () => renderer.unmount());
});

test("confirmation controls retain mobile wrapping, touch size and bounded scrolling", () => {
  const parse = require("postcss").parse;
  const assistant = parse(fs.readFileSync(new URL("../personal-agent/assistant-panel.css", sourceRoot), "utf8"));
  const center = parse(fs.readFileSync(new URL("../personal-agent-center.css", sourceRoot), "utf8"));
  const confirmation = parse(fs.readFileSync(new URL("../personal-agent/confirmation-history.css", sourceRoot), "utf8"));
  const value = (root, selector, property, width) => {
    let result;
    root.walkRules((rule) => {
      if (!rule.selectors.includes(selector)) return;
      for (let parent = rule.parent; parent; parent = parent.parent) {
        if (parent.type !== "atrule" || parent.name !== "media") continue;
        const limit = /max-width:\s*(\d+)px/.exec(parent.params);
        if (!limit || width > Number(limit[1])) return;
      }
      rule.walkDecls(property, (declaration) => { result = declaration.value; });
    });
    return result;
  };
  for (const width of [320, 375, 390, 414, 768]) {
    assert.equal(value(assistant, ".assistant .assistant-pending .ant-list-item", "flex-wrap", width), "wrap");
    assert.equal(value(assistant, ".assistant .assistant-pending", "overflow", width), "auto");
    assert.equal(value(assistant, ".assistant .assistant-pending .ant-btn", "min-width", width), "44px");
    assert.equal(value(assistant, ".assistant .assistant-pending .ant-btn", "min-height", width), "44px");
    assert.equal(value(center, ".workspace-pending-row > .ant-btn", "min-height", width), "44px");
    assert.equal(value(center, ".workspace-pending-row > div:first-child", "overflow-wrap", width), "anywhere");
    assert.equal(value(center, ".workspace-pending", "overflow", width), "auto");
    if (width <= 760) assert.equal(value(center, ".workspace-pending-row", "flex-wrap", width), "wrap");
    assert.equal(value(confirmation, ".personal-action-confirmation .ant-modal-footer .ant-btn", "min-height", width), "44px");
  }
});

test("personal MCP confirmation rereads failed status and permits only manual cancellation of stale pending requests", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const action = { id: "a1", type: "mcp.call", status: "pending", payload: { request_id: "r1" } };
  let status = "pending";
  let reads = 0;
  let closed = 0;
  const decisions = [];
  const { ActionConfirmation } = loadModule("../personal-agent/ActionConfirmation.tsx", {
    antd: { ...require("antd"), Alert: component("alert"), Button: component("button"), Modal: ({ footer, children, ...props }) => React.createElement("modal", props, children, footer), Space: component("space"), Spin: component("spin"), Tag: component("tag"), message: { error() {} } },
    "../api": { api: { get: async () => { reads++; return { data: { request_id: "r1", status, preview: {}, summary: "确认操作" } }; } } },
    "../AgentOperationPreview": { AgentOperationPreview: component("preview"), hasAgentOperationPreview: () => true, agentOperationError: (error) => error.message, agentOperationMessage: String },
  });
  const props = { action, deciding: false, onClose: () => closed++, onDecide: async (_action, decision) => {
    decisions.push(decision);
    if (decision === "approved") throw new AxiosError("接口定义已变化，请重新准备", undefined, undefined, undefined, { status: 409, data: { detail: "接口定义已变化，请重新准备" } });
    return true;
  } };
  let renderer;
  await act(async () => { renderer = create(React.createElement(ActionConfirmation, props)); });
  const button = (label) => renderer.root.findAllByType("button").find((item) => item.props.children === label);
  await act(async () => button("确认并执行").props.onClick());
  assert.equal(reads, 2, "409 后只读回查真实请求，不重试写入");
  assert.equal(button("确认并执行").props.disabled, true);
  assert.equal(button("取消操作").props.disabled, false, "仍待确认的过期请求可以由用户取消");
  await act(async () => button("确认并执行").props.onClick());
  assert.deepEqual(decisions, ["approved"], "错误状态不能重复批准");
  await act(async () => button("取消操作").props.onClick());
  assert.deepEqual(decisions, ["approved", "rejected"]);
  assert.equal(closed, 1);
  status = "failed";
  await act(async () => renderer.update(React.createElement(ActionConfirmation, { ...props, action: { ...action, id: "a2" } })));
  assert.equal(renderer.root.findAllByType("button").some((item) => item.props.children === "确认并执行"), false);
  assert.equal(renderer.root.findByType("tag").props.children, "执行失败");
  await act(async () => renderer.unmount());
});

test("personal runtime completes on authoritative state without waiting for transport EOF", { timeout: 3000 }, async () => {
  let runtime;
  let controller;
  let cancelled = false;
  const body = new ReadableStream({ start(value) { controller = value; }, cancel() { cancelled = true; } });
  const { useConversationRuntime } = loadModule("../personal-agent/useConversationRuntime.ts", {
    "../api": { api: {} },
  }, { fetch: async () => ({ ok: true, body }), localStorage: { getItem: () => "test-only" } });
  function Probe() { runtime = useConversationRuntime(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  const initial = { conversation_id: "c1", messages: [], pending_actions: [] };
  await act(async () => runtime.activate(initial));
  let generation;
  await act(async () => { generation = runtime.generate(initial, { content: "准备操作" }, { role: "user", content: "准备操作" }, {}); });
  assert.equal(runtime.running("c1"), true);
  const completed = { ...initial, messages: [{ role: "assistant", content: "等待人工确认" }], pending_actions: [{ id: "a1", status: "pending" }] };
  await act(async () => {
    controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: "state", state: completed })}\r\n\r\n`));
    await generation;
  });
  assert.equal(cancelled, true, "终态后主动结束读取，不等待代理关闭连接");
  assert.equal(runtime.running("c1"), false);
  assert.equal(Object.keys(runtime.activities).length, 0);
  assert.equal(runtime.state.pending_actions[0].id, "a1");
  await act(async () => renderer.unmount());
});

test("personal runtime treats done without state as an explicit incomplete response", { timeout: 3000 }, async () => {
  let runtime;
  let controller;
  const body = new ReadableStream({ start(value) { controller = value; } });
  const { useConversationRuntime } = loadModule("../personal-agent/useConversationRuntime.ts", {
    "../api": { api: {} },
  }, { fetch: async () => ({ ok: true, body }), localStorage: { getItem: () => "test-only" } });
  function Probe() { runtime = useConversationRuntime(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  const initial = { conversation_id: "c1", messages: [], pending_actions: [] };
  await act(async () => runtime.activate(initial));
  let generation;
  await act(async () => { generation = runtime.generate(initial, { content: "查询" }, { role: "user", content: "查询" }, {}); });
  await act(async () => {
    const rejected = assert.rejects(generation, /未收到完整结果/);
    controller.enqueue(new TextEncoder().encode('data: {"type":"done"}\n\n'));
    await rejected;
  });
  assert.equal(runtime.running("c1"), false);
  assert.equal(runtime.state.messages.at(-1).failed, true);
  await act(async () => renderer.unmount());
});

test("personal decision waits for server stop, serializes duplicate clicks and propagates stop refusal", { timeout: 5000 }, async () => {
  let workspace;
  let controller;
  let resolveStop;
  let rejectStop;
  const calls = [];
  const action = { id: "a1", type: "mcp.call", status: "pending", summary: "准备修改", payload: { request_id: "r1" } };
  const initial = { conversation_id: "c1", messages: [], pending_actions: [action] };
  const stopped = { ...initial, messages: [{ role: "user", content: "查询" }, { role: "assistant", content: "已停止", stopped: true }] };
  const api = {
    get: async (path) => ({ data: path === "/agent/skills" ? { items: [{ id: "general-office", available: true, name: "办公" }] } : { ready: true } }),
    post: async (path, body, options) => {
      calls.push({ path, body, options });
      if (path.endsWith("/stop")) return new Promise((resolve, reject) => { resolveStop = resolve; rejectStop = reject; });
      return { data: { state: { ...stopped, pending_actions: [] } } };
    },
  };
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    "../api": { api },
    antd: { ...require("antd"), message: { warning() {}, error() {}, success() {} } },
    "./usePersonalConversations": { usePersonalConversations: (activate) => ({
      items: [], busy: false, locked: () => false, load: async () => activate(initial), refresh: async () => {},
    }) },
    "../legal/constants": { aiWordDocumentName: () => "", isAiWordGenerationRequest: () => false, isUsableAiDocumentContent: () => false },
    "../legal/services/agentDocumentConfirmation": { confirmCaseAgentDocument: () => assert.fail("不得自动保存业务文档") },
  }, {
    fetch: async (_path, options) => ({ ok: true, body: new ReadableStream({ start(value) {
      controller = value;
      options.signal.addEventListener("abort", () => { const error = new Error("aborted"); error.name = "AbortError"; controller.error(error); });
    } }) }),
    localStorage: { getItem: () => "test-only" },
  });
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  let generation;
  await act(async () => { generation = workspace.send("查询"); });
  let decision;
  await act(async () => { decision = workspace.decide(action, "approved"); });
  assert.equal(workspace.decisionId, "a1");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, "/personal-agent/conversations/c1/stop");
  await act(async () => assert.equal(await workspace.decide(action, "approved"), false));
  assert.equal(calls.length, 1, "等待停止时重复点击不能再发确认请求");
  await act(async () => { resolveStop({ data: { state: stopped } }); assert.equal(await decision, true); await generation; });
  assert.equal(calls.length, 2);
  assert.equal(calls[1].path, "/personal-agent/actions/a1/decision");
  assert.equal(calls[1].body.conversation_id, "c1");
  assert.equal(calls[1].options.headers["X-OA-Agent-Confirmation"], "frontend");
  assert.equal(workspace.sending, false);
  assert.equal(workspace.decisionId, "");
  await act(async () => { generation = workspace.send("再次查询"); });
  await act(async () => { decision = workspace.decide(action, "approved"); });
  await act(async () => {
    const refused = assert.rejects(decision, /不能中断/);
    rejectStop(new Error("已确认的 OA 操作不能中断"));
    await refused;
  });
  assert.equal(calls.length, 3, "停止拒绝后不能继续发确认请求");
  assert.equal(workspace.decisionId, "");
  await act(async () => {
    controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: "state", state: { ...stopped, pending_actions: [] } })}\n\n`));
    await generation;
    renderer.unmount();
  });
});

test("personal failed decision synchronizes authoritative conversation without replaying writes", async () => {
  let workspace;
  const action = { id: "a1", status: "pending", type: "mcp.call", payload: { request_id: "r1" } };
  let current = { conversation_id: "c1", messages: [], pending_actions: [action] };
  const refreshed = { ...current, pending_actions: [] };
  const calls = [];
  const failure = new AxiosError("请求失败", undefined, undefined, undefined, { status: 409, data: { detail: { status: "failed", error: { detail: "原业务接口已拒绝" } } } });
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("失败不能伪造成功") } },
    "../api": { api: {
      get: async (path) => {
        calls.push(["get", path]);
        return { data: path === "/agent/skills" ? { items: [] } : path === "/personal-agent/conversations" ? { state: refreshed, items: [] } : { ready: true } };
      },
      post: async (path) => { calls.push(["post", path]); throw failure; },
    } },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace: (next) => { current = next; } }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], busy: false, locked: () => false, load: async () => {}, refresh: async () => {} }) },
    "../legal/constants": {}, "../legal/services/agentDocumentConfirmation": {},
  });
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => assert.rejects(workspace.decide(action, "approved"), (error) => error === failure));
  assert.equal(current, refreshed);
  assert.equal(workspace.state.pending_actions.length, 0);
  assert.equal(workspace.decisionId, "");
  assert.deepEqual(calls.filter(([method]) => method === "post"), [["post", "/personal-agent/actions/a1/decision"]]);
  await act(async () => assert.rejects(workspace.decide(action, "approved"), /不存在或已处理/));
  assert.equal(calls.filter(([method]) => method === "post").length, 1);
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

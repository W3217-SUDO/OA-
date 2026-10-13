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

test("manual new conversation requires one confirmation, cancellation preserves state and failures keep the drawer", async () => {
  const confirmations = [], failures = [], created = [];
  let failCreate = false;
  const modal = { confirm: options => { confirmations.push(options); } };
  const { ConversationManager } = loadModule("../personal-agent/ConversationManager.tsx", {
    antd: {
      Button: "button", Drawer: "drawer", Empty: "empty", Tooltip: "tooltip",
      Modal: { useModal: () => [modal, null] },
      message: { error: value => failures.push(value), success() {} },
    },
    "./types": { errorText: (error, fallback) => error.message || fallback },
  });
  let renderer;
  const props = {
    items: [], activeId: "original", busy: false, runningIds: [],
    onCreate: async () => { if (failCreate) throw new Error("创建失败"); created.push("new"); },
    onSelect: async () => {}, onDelete: async () => {},
  };
  await act(async () => { renderer = create(React.createElement(ConversationManager, props)); });
  const newButton = () => renderer.root.findAllByType("button").find(button => button.props["aria-label"] === "新建对话");
  await act(async () => { newButton().props.onClick(); newButton().props.onClick(); });
  assert.equal(confirmations.length, 1, "连续点击只能打开一个确认框");
  assert.match(confirmations[0].content, /可在对话列表中返回/);
  assert.equal(created.length, 0, "打开确认框不会创建对话");
  await act(async () => { confirmations[0].onCancel?.(); confirmations[0].afterClose(); });
  assert.equal(created.length, 0, "取消不会调用创建操作");
  await act(async () => { newButton().props.onClick(); await confirmations[1].onOk(); confirmations[1].afterClose(); });
  assert.equal(created.length, 1, "确认才创建一次对话");
  await act(async () => { renderer.update(React.createElement(ConversationManager, { ...props, activeId: null })); });
  await act(async () => { newButton().props.onClick(); });
  assert.equal(confirmations[2].content, "确认打开一条新对话？", "无当前会话时不承诺返回未保存草稿");
  await act(async () => { confirmations[2].afterClose(); });
  await act(async () => { renderer.root.findAllByType("button").find(button => button.props["aria-label"] === "对话列表").props.onClick(); });
  assert.equal(renderer.root.findByType("drawer").props.open, true);
  await act(async () => { renderer.root.findByType("drawer").props.extra.props.onClick(); });
  failCreate = true;
  await act(async () => { await assert.rejects(confirmations[3].onOk(), /创建失败/); });
  assert.equal(renderer.root.findByType("drawer").props.open, true, "创建失败保留当前抽屉");
  assert.deepEqual(failures, ["创建失败"]);
  await act(async () => { newButton().props.onClick(); });
  assert.equal(confirmations.length, 4, "失败时确认框保持打开，不增加第二个确认框");
  failCreate = false;
  await act(async () => { await confirmations[3].onOk(); confirmations[3].afterClose(); });
  assert.equal(renderer.root.findByType("drawer").props.open, false, "抽屉新建成功才关闭抽屉");
  assert.equal(created.length, 2);
  await act(async () => { renderer.unmount(); });
});

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

test("personal confirmation history reads pending and decided records with paging, errors and cancellation", async () => {
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
    "./ConfirmationHistoryDetails": { ConfirmationHistoryDetails: component("history-details") },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(ConfirmationHistory)); });
  assert.equal(requests.length, 0, "未打开历史时不查询");
  assert.equal(renderer.root.findByProps({ className: "confirmation-history-label" }).props.children, "历史确认记录", "历史入口保留可见文字，不只依赖图标");
  await act(async () => renderer.root.findByProps({ "aria-label": "历史确认记录" }).props.onClick());
  assert.equal(renderer.root.findByType("drawer").props.rootClassName, "confirmation-history-drawer", "宽度限制作用域必须位于抽屉根节点，才能命中内容 wrapper");
  assert.equal(requests[0].path, "/personal-agent/confirmation-history");
  assert.equal(JSON.stringify(requests[0].options.params), JSON.stringify({ page: 1, page_size: 20 }));
  assert.equal(renderer.root.findByType("select").props.options.some((option) => option.value === "pending"), true);
  assert.equal(renderer.root.findByType("spin").type, "spin");
  const record = { id: "r1", source: "mcp", action_type: "batch", summary: "为2个案件新增期限提醒", status: "succeeded", requested_at: "2026-10-13T02:00:00Z", decided_at: "2026-10-13T02:01:00Z", finished_at: null, operator: "审核人", comment: "同意", result: { count: 2, message: "已生成期限提醒" }, error: null, conversation_id: null, conversation_title: null, action_id: null, can_decide: false };
  await act(async () => requests[0].resolve({ data: { items: [record], total: 21, page: 1, page_size: 20 } }));
  assert.equal(renderer.root.findByType("strong").props.children, "为2个案件新增期限提醒");
  assert.equal(renderer.root.findByType("tag").props.children, "已执行");
  assert.equal(renderer.root.findByType("summary").props.children, "执行结果");
  assert.equal(renderer.root.findByType("details").props.open, undefined, "完整结果默认折叠");
  assert.deepEqual(JSON.parse(renderer.root.findByType("pre").props.children), record.result);
  assert.equal(renderer.root.findAllByType("button").length, 3, "历史新增只读详情，不提供决定或重放按钮");
  await act(async () => renderer.root.findAllByType("button").find((button) => button.props.children === "查看详情").props.onClick());
  assert.equal(renderer.root.findByType("history-details").props.record, record);
  assert.equal(requests.length, 1, "查看已执行记录不发决定请求");
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
    "./PersonalAiSpace": { PersonalAiSpace: component("personal-ai-space") },
    "./ActionConfirmation": { ActionConfirmation: component("action-confirmation") },
  });
  const action = { id: "a1", type: "mcp.call", summary: "为2个案件新增期限提醒", status: "pending" };
  const decisions = [];
  const workspace = {
    status: { ready: true }, state: { messages: [], pending_actions: [action], dismissed_action_ids: [], conversation_id: "c1" },
    visibleActions: [action], dismissalId: "", decisionFailures: {},
    loading: false, loadError: "", sending: false, stopping: false, input: "", conversations: [], runningIds: [],
    conversationBusy: false, uploading: false, decisionId: "", setInput: () => {}, send: () => {}, stop: () => {}, load: () => {},
    decide: async (item, decision) => { decisions.push([item.id, decision]); throw new Error("取消被原权限拒绝"); },
  };
  const props = { workspace, suggestions: [], focusRequested: false, onFocusHandled: () => {} };
  let renderer;
  await act(async () => { renderer = create(React.createElement(AssistantPanel, props)); });
  assert.equal(renderer.root.findAllByType("personal-ai-space").length, 1, "桌面与手机共用唯一空间抽屉");
  assert.equal(renderer.root.findByType("personal-ai-space").props.open, false);
  await act(async () => renderer.root.findByType("workspace-tools").props.onOpenPersonalAiSpace());
  assert.equal(renderer.root.findByType("personal-ai-space").props.open, true);
  await act(async () => renderer.root.findByType("personal-ai-space").props.onClose());
  await act(async () => renderer.root.findAllByType("button").find((item) => item.props["aria-label"] === "个人 AI 空间").props.onClick());
  assert.equal(renderer.root.findByType("personal-ai-space").props.open, true, "桌面入口使用同一空间开关");
  await act(async () => renderer.root.findByType("personal-ai-space").props.onClose());
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
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, visibleActions: [failed], state: { ...workspace.state, pending_actions: [failed] } } })));
  assert.equal(renderer.root.findByType("action-confirmation").props.action, failed, "已打开弹窗直接读取最新操作，不保留旧 pending 对象");
  assert.equal(renderer.root.findByType("tag").props.children, "执行失败");
  assert.equal(renderer.root.findByType("alert").props.title, "任务由案件阶段自动完成，人工只能变更期限");
  assert.equal(button("查看并确认"), undefined);
  assert.equal(button("取消"), undefined);
  await act(async () => button("查看状态").props.onClick());
  assert.equal(renderer.root.findByType("action-confirmation").props.action.status, "failed");
  assert.equal(decisions.length, 1, "失败卡只读查看，不能重复执行");
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, visibleActions: [], state: { ...workspace.state, pending_actions: [] } } })));
  assert.equal(renderer.root.findByType("action-confirmation").props.action, null, "操作已移除时关闭弹窗，不回退旧对象");
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, state: { ...workspace.state, conversation_id: "c2", pending_actions: [action] } } })));
  assert.equal(renderer.root.findByType("action-confirmation").props.action, null, "切换会话后不能沿用旧操作选择");
  const failures = {
    a1: { actionId: "a1", message: "A执行结果未知", state: "unknown" },
    b1: { actionId: "b1", message: "B执行结果未知", state: "unknown" },
  };
  await act(async () => renderer.update(React.createElement(AssistantPanel, { ...props, workspace: { ...workspace, visibleActions: [], decisionFailures: failures, state: { ...workspace.state, pending_actions: [] } } })));
  assert.deepEqual(renderer.root.findAllByType("alert").map((item) => item.props.description), ["A执行结果未知", "B执行结果未知"], "原卡移除也显示所有相关错误，不只最后一条");
  await act(async () => renderer.unmount());
});

test("personal center retains terminal outcomes as visible read-only cards", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const action = { id: "a1", type: "create_task", status: "pending", summary: "原待确认任务" };
  const workspace = {
    status: { ready: true, commands: [] }, state: { conversation_id: "c1", messages: [], pending_actions: [action], dismissed_action_ids: [] },
    visibleActions: [action], dismissalId: "", decisionFailures: {},
    skills: [], skillId: "general-office", input: "", loading: false, sending: true, uploading: false,
    materials: [], caseMaterials: [], savedDocuments: {}, conversations: [], runningIds: ["c1"],
    decisionId: "", conversationBusy: false,
  };
  const { default: PersonalAgentCenterPage } = loadModule("../PersonalAgentCenterPage.tsx", {
    antd: { ...require("antd"), Alert: component("alert"), Button: component("button"), Input: { TextArea: component("textarea") }, Select: component("select"), Segmented: component("segmented"), Space: component("space"), Tag: component("tag"), Tooltip: component("tooltip") },
    "./personal-agent/usePersonalWorkspace": { usePersonalWorkspace: () => workspace },
    "./personal-agent/WorkPanel": { WorkPanel: component("work-panel") },
    "./personal-agent/ConversationManager": { ConversationManager: component("conversations") },
    "./personal-agent/PersonalAiSpace": { PersonalAiSpace: component("personal-ai-space") },
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
  await act(async () => button("查看并确认").props.onClick());
  assert.equal(renderer.root.findByType("confirmation").props.action, action);
  const failed = { ...action, status: "failed", error: { detail: { detail: "任务由案件阶段自动完成，人工只能变更期限" } } };
  workspace.state = { ...workspace.state, pending_actions: [failed] };
  workspace.visibleActions = [failed];
  await act(async () => renderer.update(React.createElement(PersonalAgentCenterPage, { onNavigate() {} })));
  assert.equal(renderer.root.findByType("confirmation").props.action, failed, "非 MCP 弹窗同步最新终态和错误");
  assert.equal(button("查看并确认"), undefined);
  assert.equal(button("查看状态").props.disabled, false);
  assert.equal(renderer.root.findByType("alert").props.title, "任务由案件阶段自动完成，人工只能变更期限");
  await act(async () => button("查看状态").props.onClick());
  assert.equal(renderer.root.findByType("confirmation").props.action.status, "failed");
  workspace.state = { ...workspace.state, pending_actions: [] };
  workspace.visibleActions = [];
  await act(async () => renderer.update(React.createElement(PersonalAgentCenterPage, { onNavigate() {} })));
  assert.equal(renderer.root.findByType("confirmation").props.action, null, "已移除的非 MCP 操作不能退回旧 pending");
  workspace.state = { ...workspace.state, conversation_id: "c2", pending_actions: [action] };
  workspace.visibleActions = [action];
  await act(async () => renderer.update(React.createElement(PersonalAgentCenterPage, { onNavigate() {} })));
  assert.equal(renderer.root.findByType("confirmation").props.action, null, "切换会话清除旧选择，不确认另一会话");
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
  for (const width of [320, 375, 390, 414, 768, 1280, 1880]) {
    assert.equal(value(assistant, ".assistant-pending .assistant-action-dismiss.ant-btn", "width", width), "44px");
    assert.equal(value(assistant, ".assistant-pending .assistant-action-dismiss.ant-btn", "height", width), "44px");
    assert.equal(value(center, ".workspace-pending-row > .ant-btn-icon-only", "width", width), "44px");
    assert.equal(value(center, ".workspace-pending-row > .ant-btn-icon-only", "height", width), "44px");
    assert.equal(value(confirmation, ".confirmation-history-detail .ant-modal-footer .ant-btn", "min-height", width), "44px");
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
  const initial = { conversation_id: "c1", messages: [], pending_actions: [], dismissed_action_ids: [] };
  await act(async () => runtime.activate(initial));
  let generation;
  await act(async () => { generation = runtime.generate(initial, { content: "准备操作" }, { role: "user", content: "准备操作" }, {}); });
  assert.equal(runtime.running("c1"), true);
  await act(async () => runtime.activate(initial));
  assert.equal(runtime.state.messages.length, 2, "在途生成仍保留已有流式cache");
  const completed = { ...initial, messages: [{ role: "assistant", content: "等待人工确认" }], pending_actions: [{ id: "a1", status: "pending" }] };
  await act(async () => {
    controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: "state", state: completed })}\r\n\r\n`));
    await generation;
  });
  assert.equal(cancelled, true, "终态后主动结束读取，不等待代理关闭连接");
  assert.equal(runtime.running("c1"), false);
  assert.equal(Object.keys(runtime.activities).length, 0);
  assert.equal(runtime.state.pending_actions[0].id, "a1");
  const fresh = { ...completed, pending_actions: [{ id: "a1", status: "failed" }] };
  await act(async () => runtime.activate(fresh));
  assert.equal(runtime.state, fresh, "非运行会话采用服务端fresh状态，不回退旧pending缓存");
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
  const initial = { conversation_id: "c1", messages: [], pending_actions: [], dismissed_action_ids: [] };
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
  const initial = { conversation_id: "c1", messages: [], pending_actions: [action], dismissed_action_ids: [] };
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
  let resolveRead;
  const action = { id: "a1", status: "pending", type: "mcp.call", payload: { request_id: "r1" } };
  let current = { conversation_id: "c1", messages: [], pending_actions: [action], dismissed_action_ids: [] };
  const refreshed = { ...current, pending_actions: [] };
  const calls = [];
  const failure = new AxiosError("请求失败", undefined, undefined, undefined, { status: 409, data: { detail: { status: "failed", error: { detail: "原业务接口已拒绝" } } } });
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("失败不能伪造成功") } },
    "../api": { api: {
      get: async (path, options) => {
        calls.push(["get", path]);
        if (path === "/personal-agent/conversations") {
          assert.equal(options.timeout, 15000);
          return await new Promise((resolve) => { resolveRead = resolve; });
        }
        return { data: path === "/agent/skills" ? { items: [] } : { ready: true } };
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
  let rejection;
  await act(async () => { rejection = assert.rejects(workspace.decide(action, "approved"), (error) => error === failure); });
  assert.equal(workspace.decisionFailures[action.id].message, "原业务接口已拒绝", "只读GET未返回前已经显示真实HTTP错误");
  assert.equal(workspace.decisionFailures[action.id].state, "syncing");
  assert.equal(workspace.state.pending_actions[0].status, "pending", "不能把未知执行结果伪造为failed");
  await act(async () => { resolveRead({ data: { state: refreshed, items: [] } }); await rejection; });
  assert.equal(current, refreshed);
  assert.equal(workspace.state.pending_actions.length, 0);
  assert.equal(workspace.decisionId, "");
  assert.equal(workspace.decisionFailures[action.id].state, "verified");
  assert.equal(workspace.decisionFailures[action.id].message, "原业务接口已拒绝", "原卡移除也保留会话错误反馈");
  assert.deepEqual(calls.filter(([method]) => method === "post"), [["post", "/personal-agent/actions/a1/decision"]]);
  await act(async () => assert.rejects(workspace.decide(action, "approved"), /不存在或已处理/));
  assert.equal(calls.filter(([method]) => method === "post").length, 1);
  await act(async () => renderer.unmount());
});

test("personal action dismissal persists one captured ID batch and resumes only the mapped original action", async () => {
  let workspace;
  let current = { conversation_id: "CODEX-conversation", messages: [], dismissed_action_ids: [], pending_actions: [
    { id: "CODEX-action-a", type: "mcp.call", status: "pending", summary: "待确认A" },
    { id: "CODEX-action-b", type: "create_task", status: "failed", summary: "失败B" },
  ] };
  const calls = [];
  let failDismiss = false;
  let resolveDismiss;
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("展示操作不得假称业务成功") } },
    "../api": { api: {
      get: async (path) => ({ data: path === "/agent/skills" ? { items: [] } : { ready: true } }),
      post: async (path, body) => {
        calls.push([path, body]);
        if (failDismiss) throw new Error("展示持久化失败");
        return await new Promise((resolve) => { resolveDismiss = resolve; });
      },
    } },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace: (next) => { current = next; } }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], busy: false, locked: () => false, load: async () => {}, refresh: async () => {}, select: async (id) => { calls.push(["select", id]); return current; } }) },
    "../legal/constants": {}, "../legal/services/agentDocumentConfirmation": {},
  });
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  let saved;
  await act(async () => { saved = workspace.dismissActions(workspace.visibleActions); });
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0])), ["/personal-agent/conversations/CODEX-conversation/actions/dismiss", { action_ids: ["CODEX-action-a", "CODEX-action-b"] }]);
  assert.equal(workspace.visibleActions.length, 2, "服务器保存前不得乐观隐藏");
  current = { ...current, pending_actions: [...current.pending_actions, { id: "CODEX-new", type: "create_task", status: "pending", summary: "新请求" }] };
  await act(async () => { resolveDismiss({ data: { state: { ...current, dismissed_action_ids: ["CODEX-action-a", "CODEX-action-b"] } } }); await saved; });
  assert.deepEqual(workspace.visibleActions.map((action) => action.id), ["CODEX-new"], "点击后新到的请求不在旧收起ID集");
  assert.equal(current.dismissed_action_ids.length, 0, "不把收起返回的旧消息快照覆盖流式状态");
  failDismiss = true;
  await act(async () => assert.rejects(workspace.dismissAction(workspace.visibleActions[0]), /展示持久化失败/));
  assert.equal(workspace.visibleActions[0].id, "CODEX-new");
  const detail = { item: { source: "mcp", id: "CODEX-request-r", status: "pending", action_id: "CODEX-action-a", can_decide: true }, conversation_id: current.conversation_id, conversation_title: "本轮对话", action: current.pending_actions[0], can_decide: true, request_preview: null };
  let restored;
  await act(async () => { restored = await workspace.reopenConfirmation(detail); });
  assert.equal(restored.actionId, "CODEX-action-a", "不能用不同的MCP request_id猜action_id");
  assert.equal(calls.filter(([path]) => path.endsWith("/decision")).length, 0, "关闭及重开不发决定请求");
  await act(async () => assert.rejects(workspace.reopenConfirmation({ ...detail, can_decide: false }), /不是可恢复/));
  await act(async () => assert.rejects(workspace.reopenConfirmation({ ...detail, item: { ...detail.item, action_id: "CODEX-request-r" } }), /不是可恢复/));
  current = { ...current, dismissed_action_ids: ["CODEX-action-a", "CODEX-action-b"] };
  await act(async () => renderer.unmount());
  await act(async () => { renderer = create(React.createElement(Probe)); });
  assert.deepEqual(workspace.visibleActions.map((action) => action.id), ["CODEX-new"], "重载从服务器契约恢复收起，不依赖组件state或localStorage");
  await act(async () => renderer.unmount());
});

test("personal unknown decision state stays actionable only after explicit history verification", async () => {
  let workspace;
  const action = { id: "CODEX-unknown", type: "create_task", status: "pending", summary: "待核对" };
  const current = { conversation_id: "CODEX-conversation", messages: [], dismissed_action_ids: [], pending_actions: [action] };
  let posts = 0;
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("未知结果不能报告成功") } },
    "../api": { api: {
      get: async (path) => { if (path === "/personal-agent/conversations") throw new Error("只读状态读取超时"); return { data: path === "/agent/skills" ? { items: [] } : { ready: true } }; },
      post: async () => { posts++; throw new Error("网络断开，执行结果未知"); },
    } },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace() {} }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], busy: false, locked: () => false, load: async () => {}, refresh: async () => {} }) },
    "../legal/constants": {}, "../legal/services/agentDocumentConfirmation": {},
  });
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => assert.rejects(workspace.decide(action, "approved"), /禁止重复提交/));
  assert.equal(workspace.decisionFailures[action.id].state, "unknown");
  assert.equal(action.status, "pending", "网络未知不得伪造业务failed");
  await act(async () => workspace.hideDecisionFailure(action.id));
  await act(async () => assert.rejects(workspace.decide(action, "approved"), /禁止直接重复提交/));
  assert.equal(posts, 1, "收起错误反馈不清除未知决定保护，不重POST");
  await act(async () => renderer.unmount());
});

test("personal per-action failure ledger preserves A across B failures, dismissal and verified reopening", async () => {
  let workspace;
  const a = { id: "CODEX-action-A", type: "mcp.call", status: "pending", summary: "操作A", payload: { request_id: "CODEX-request-A" } };
  const b = { id: "CODEX-action-B", type: "create_task", status: "pending", summary: "操作B" };
  let current = { conversation_id: "CODEX-conversation", messages: [], dismissed_action_ids: [], pending_actions: [a, b] };
  const posts = [];
  let failSelect = true;
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("未知结果不能报告成功") } },
    "../api": { api: {
      get: async (path) => { if (path === "/personal-agent/conversations") throw new Error("只读回查失败"); return { data: path === "/agent/skills" ? { items: [] } : { ready: true } }; },
      post: async (path, body) => {
        posts.push([path, body]);
        if (path.endsWith("/actions/dismiss")) return { data: { state: { ...current, dismissed_action_ids: body.action_ids } } };
        throw new Error(`网络未知：${path}`);
      },
    } },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace: (next) => { current = next; } }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], busy: false, locked: () => false, load: async () => {}, refresh: async () => {}, select: async () => { if (failSelect) throw new Error("原会话读取失败"); return current; } }) },
    "../legal/constants": {}, "../legal/services/agentDocumentConfirmation": {},
  });
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => assert.rejects(workspace.decide(a, "approved"), /禁止重复提交/));
  const originalA = workspace.decisionFailures[a.id];
  await act(async () => assert.rejects(workspace.decide(b, "approved"), /禁止重复提交/));
  assert.equal(workspace.decisionFailures[a.id], originalA, "B失败不能覆盖A的保护与错误");
  assert.equal(workspace.decisionFailures[b.id].state, "unknown");
  await act(async () => workspace.hideDecisionFailure(b.id));
  assert.equal(workspace.decisionFailures[a.id], originalA, "收起B提示只修改B");
  await act(async () => workspace.dismissAction(a));
  assert.deepEqual(JSON.parse(JSON.stringify(posts.at(-1))), ["/personal-agent/conversations/CODEX-conversation/actions/dismiss", { action_ids: [a.id] }], "单卡X只传一项");
  assert.deepEqual(workspace.visibleActions.map((action) => action.id), [b.id], "单卡收起不隐藏B");
  assert.equal(workspace.decisionFailures[a.id], originalA, "关闭操作卡不清未知决定保护");
  const detail = { item: { source: "personal_action", id: b.id, status: "pending", action_id: b.id, can_decide: true }, conversation_id: current.conversation_id, conversation_title: "本轮对话", action: b, can_decide: true, request_preview: null };
  await act(async () => assert.rejects(workspace.reopenConfirmation(detail), /原会话读取失败/));
  assert.equal(workspace.decisionFailures[b.id].state, "unknown", "读取失败不能解除B保护");
  failSelect = false;
  await act(async () => { await workspace.reopenConfirmation(detail); });
  assert.equal(workspace.decisionFailures[b.id], undefined, "只对已核验的B解除保护");
  assert.equal(workspace.decisionFailures[a.id], originalA, "重开B不能解除A未知保护");
  await act(async () => assert.rejects(workspace.decide(a, "approved"), /禁止直接重复提交/));
  assert.equal(posts.filter(([path]) => path.endsWith("/decision")).length, 2, "A与B最初各一POST，A禁止重POST");
  await act(async () => renderer.unmount());
});

test("personal workspace preserves legacy case Word confirmation and follows explicit document capabilities", async () => {
  let workspace;
  let caseConfirmation;
  const calls = [];
  const errors = [];
  let running = false;
  const caseMessage = { role: "assistant", content: "原案件正文", case_id: 42, case_no: "CODEX-CASE", can_save_document: true };
  const personalMessage = { role: "assistant", content: "个人正文", can_save_document: true, can_save_case_document: false, can_save_personal_document: true };
  const caseWithoutUpload = { ...personalMessage, content: "有关联案件但无案件上传权限", case_id: 42 };
  const state = { conversation_id: "CODEX-conversation", messages: [caseMessage, personalMessage, caseWithoutUpload], pending_actions: [], dismissed_action_ids: [] };
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error: (text) => errors.push(text), success() {} } },
    "../api": { api: { get: async (path) => ({ data: path === "/agent/skills" ? { items: [] } : { ready: true } }) } },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state, activities: {}, anyRunning: () => false, running: () => running, reset() {}, get: () => state }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], busy: false, locked: () => false, load: async () => {}, refresh: async () => {} }) },
    "../legal/constants": { aiWordDocumentName: () => "原文.docx" },
    "../legal/services/agentDocumentConfirmation": { confirmCaseAgentDocument: (value) => { calls.push("case"); caseConfirmation = value; } },
    "./personalAiDocumentConfirmation": { confirmPersonalAiDocument: async (value) => { calls.push("personal"); assert.equal(value.conversationId, "CODEX-conversation"); assert.ok([1, 2].includes(value.messageIndex)); assert.equal(Object.hasOwn(value, "caseId"), false); value.onSaved({ name: "个人文稿.docx" }); } },
  });
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => { await workspace.saveWord(caseMessage, 0); });
  assert.deepEqual(calls, ["case"], "原can_save_document+case_id消息保留案件确认，不依赖新标记");
  assert.equal(caseConfirmation.caseId, 42);
  assert.equal(caseConfirmation.serialNo, "CODEX-CASE");
  assert.equal(caseConfirmation.content, caseMessage.content);
  assert.equal(workspace.documentRevision, 0, "打开确认不等于保存成功");
  await act(async () => { await caseConfirmation.onSaved(); });
  assert.equal(workspace.savedDocuments[0], "原文.docx");
  assert.equal(workspace.documentRevision, 1);
  await act(async () => { await workspace.saveWord(personalMessage, 1); });
  assert.deepEqual(calls, ["case", "personal"]);
  assert.equal(workspace.savedDocuments[1], "个人文稿.docx");
  assert.equal(workspace.documentRevision, 2, "两个真实成功回调都刷新个人空间索引");
  await act(async () => { await workspace.saveWord(caseWithoutUpload, 2); });
  assert.deepEqual(calls, ["case", "personal", "personal"], "真实case标记为false时不能凭case_id走案件写入");
  assert.equal(workspace.documentRevision, 3);
  running = true;
  await act(async () => { await workspace.saveWord(caseWithoutUpload, 2); });
  assert.match(errors.at(-1), /尚未完整生成/);
  running = false;
  state.messages[2] = { ...caseWithoutUpload, failed: true };
  await act(async () => { await workspace.saveWord(caseWithoutUpload, 2); });
  state.messages[2] = { ...caseWithoutUpload, content: "已变化正文" };
  await act(async () => { await workspace.saveWord(caseWithoutUpload, 2); });
  assert.equal(calls.length, 3, "未完成、失败或变化的原消息不打开保存确认");
  await act(async () => renderer.unmount());
});

test("explicit document capability flags cannot fall through to legacy case permissions", () => {
  const { workspaceDocumentSaveTarget } = loadModule("../personal-agent/types.ts", { "../AgentOperationPreview": { agentOperationError: (error) => error.message } });
  const legacy = { role: "assistant", content: "正文", case_id: 42, can_save_document: true };
  assert.equal(workspaceDocumentSaveTarget(legacy), "case");
  assert.equal(workspaceDocumentSaveTarget({ ...legacy, can_save_case_document: false, can_save_personal_document: true }), "personal");
  assert.equal(workspaceDocumentSaveTarget({ ...legacy, can_save_case_document: false, can_save_personal_document: false }), null);
  assert.equal(workspaceDocumentSaveTarget({ ...legacy, can_save_case_document: true, can_save_personal_document: true }), "case");
  assert.equal(workspaceDocumentSaveTarget({ role: "assistant", content: "个人正文", can_save_document: true, can_save_personal_document: true, can_save_case_document: false }), "personal");
});

test("personal AI document uses raw UTF8 hash and explicit one-shot confirmation without case inference", async () => {
  const { createHash, webcrypto } = require("node:crypto");
  const content = "\n 中文正文\r\n保留空格 \n";
  let configured = false;
  let options;
  let modalReady;
  let available = true;
  const posts = [];
  const updates = [];
  const saved = [];
  const notices = [];
  const file = { id: "a".repeat(32), attachment_id: null, name: "文稿.docx", content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", size: 128, sha256: "b".repeat(64), status: "available", storage_backend: "oss", owner_user_id: 1, owner_name: "CODEX测试员工", source_kind: "assistant_message", conversation_id: "CODEX-conversation", source_request_id: null, case_id: null, created_at: "2026-10-13T00:00:00Z", download_url: "/api/v1/personal-agent/ai-space/files/" + "a".repeat(32) + "/download", error: null };
  const { confirmPersonalAiDocument } = loadModule("../personal-agent/personalAiDocumentConfirmation.tsx", {
    antd: { Alert: () => null, message: { success: (text) => notices.push(text) }, Modal: { confirm: (value) => { options = value; modalReady(); return { update: (value) => updates.push(value) }; } } },
    "../api": { api: {
      get: async () => ({ data: { owner_user_id: 1, owner_name: "CODEX测试员工", employee_record_id: 1, folder: "员工目录", storage_backend: "oss", configured } }),
      post: async (path, body, request) => { posts.push([path, body, request]); return { data: available ? file : { ...file, status: "uncertain", error: "存储状态未核实" } }; },
    } },
    "../AgentOperationPreview": { AgentOperationPreview: () => null, agentOperationError: (error) => error.message },
  }, { crypto: webcrypto, TextEncoder });
  const args = { conversationId: "CODEX-conversation", messageIndex: 3, name: "文稿.docx", content, onSaved: (item) => saved.push(item) };
  await assert.rejects(confirmPersonalAiDocument(args), /OSS 尚未配置/);
  assert.equal(options, undefined);
  assert.equal(posts.length, 0);
  configured = true;
  const ready = new Promise((resolve) => { modalReady = resolve; });
  const opened = confirmPersonalAiDocument(args);
  await ready;
  assert.equal(posts.length, 0, "查询配置及计算hash不写入，必须等待人工确认");
  await options.onOk();
  await opened;
  assert.equal(posts[0][0], "/personal-agent/ai-space/files");
  assert.deepEqual(JSON.parse(JSON.stringify(posts[0][1])), { conversation_id: "CODEX-conversation", message_index: 3, name: "文稿.docx", expected_content_sha256: createHash("sha256").update(content, "utf8").digest("hex") });
  assert.equal(posts[0][2].headers["X-OA-Agent-Confirmation"], "frontend");
  assert.equal(saved.length, 1);
  assert.equal(notices.length, 1);
  await assert.rejects(options.onOk(), /禁止重复提交/);
  assert.equal(posts.length, 1);
  available = false;
  const failedReady = new Promise((resolve) => { modalReady = resolve; });
  const failed = confirmPersonalAiDocument(args);
  await failedReady;
  await assert.rejects(options.onOk(), /存储状态未核实/);
  assert.equal(saved.length, 1, "uncertain不能标记保存成功");
  assert.equal(notices.length, 1);
  assert.equal(updates.at(-1).okButtonProps.disabled, true);
  options.onCancel();
  await failed;
});

test("personal AI mobile tools close their existing popover before opening the shared space", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  let mobile = true;
  let mediaChange;
  let opened = 0;
  const media = { get matches() { return mobile; }, addEventListener: (_event, listener) => { mediaChange = listener; }, removeEventListener() {} };
  const workspace = { status: { commands: [] }, loading: false, stopping: false, uploading: false, decisionId: "", conversationBusy: false, skills: [], skillId: "general-office", selectedCase: null, materials: [], caseMaterials: [] };
  const { AssistantWorkspaceTools } = loadModule("../personal-agent/AssistantWorkspaceTools.tsx", {
    antd: { Button: component("button"), Popover: ({ content, children, open, ...props }) => React.createElement("popover", { open, ...props }, children, open ? content : null), Segmented: component("segmented"), Select: component("select"), Tooltip: component("tooltip"), message: { error: (text) => assert.fail(text) } },
    "./usePersonalWorkspace": { MATERIAL_ACCEPT: ".docx" },
    "./types": { errorText: (error) => error.message },
    "./CaseMaterialsPicker": { CaseMaterialsPicker: component("case-picker") },
    "./MaterialPreview": { MaterialPreview: component("material-preview") },
    "./SkillManager": { SkillManager: component("skill-manager") },
  }, { window: { matchMedia: () => media } });
  let renderer;
  await act(async () => { renderer = create(React.createElement(AssistantWorkspaceTools, { workspace, onOpenPersonalAiSpace: () => { opened++; } })); });
  assert.equal(opened, 0);
  await act(async () => renderer.root.findByType("popover").props.onOpenChange(true));
  const entry = renderer.root.findAllByType("button").find((item) => item.props.className === "personal-ai-space-mobile-entry");
  assert.ok(entry);
  await act(async () => entry.props.onClick());
  assert.equal(renderer.root.findByType("popover").props.open, false);
  assert.equal(opened, 1);
  mobile = false;
  await act(async () => mediaChange());
  assert.equal(renderer.root.findAllByType("popover").length, 0);
  assert.equal(renderer.root.findAllByType("button").some((item) => item.props.className === "personal-ai-space-mobile-entry"), false, "桌面工具组不重复挂入口");
  await act(async () => renderer.unmount());
});

test("personal AI space shows known Chinese source labels and preserves unknown source values", () => {
  const { PersonalAiSpaceFiles } = loadModule("../personal-agent/PersonalAiSpaceFiles.tsx", { antd: { Button: () => null, Empty: () => null, Tag: () => null, Tooltip: () => null } });
  const text = (node) => typeof node === "string" || typeof node === "number" ? String(node) : React.Children.toArray(node?.props?.children).map(text).join("");
  for (const [source, label] of [["mcp_export", "案件导出"], ["mcp_generated", "智能体生成文件"], ["case_draft", "案件AI草稿"], ["case_upload", "案件AI上传"], ["case_migration", "案件AI迁移"], ["assistant_message", "助手回答"], ["personal_identity", "个人身份文件"], ["future_source", "future_source"], ["toString", "toString"]]) {
    const rendered = PersonalAiSpaceFiles({ items: [{ id: "CODEX-file", name: "CODEX文稿.docx", status: "failed", size: 10, created_at: "2026-10-13T00:00:00Z", source_kind: source, conversation_id: null, source_request_id: null, error: null, download_url: null }], downloadingId: "", busy: false, onDownload: () => assert.fail("来源展示不能下载"), onConversation: () => assert.fail("无来源会话不能导航") });
    assert.ok(text(rendered).includes(label));
    assert.ok(text(rendered).includes("保存时间"));
    assert.equal(text(rendered).includes("生成时间"), false);
    if (source !== label) assert.equal(text(rendered).includes(source), false);
  }
});

test("personal AI download preserves XLS filename and rejects unavailable files before bytes", async () => {
  let status = "available";
  const paths = [];
  const urls = [];
  const anchor = { click() {} };
  const file = { id: "c".repeat(32), name: "案件导出.xls", status: "available", download_url: "/api/v1/personal-agent/ai-space/files/" + "c".repeat(32) + "/download" };
  const { downloadPersonalAiFile } = loadModule("../personal-agent/personalAiSpaceApi.ts", {
    "../api": { api: { get: async (path) => { paths.push(path); return { data: path.endsWith("/download") ? {} : { ...file, status } }; } } },
  }, { document: { createElement: () => anchor }, URL: { createObjectURL: () => "blob:CODEX", revokeObjectURL: (url) => urls.push(url) }, window: { setTimeout: (callback) => callback() } });
  await downloadPersonalAiFile(file);
  assert.equal(anchor.download, "案件导出.xls", "保留实际扩展名，不伪装XLSX");
  assert.equal(paths[1], `/personal-agent/ai-space/files/${file.id}/download`);
  assert.deepEqual(urls, ["blob:CODEX"]);
  status = "uncertain";
  await assert.rejects(downloadPersonalAiFile(file), /不能下载/);
  assert.equal(paths.filter((path) => path.endsWith("/download")).length, 1);
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

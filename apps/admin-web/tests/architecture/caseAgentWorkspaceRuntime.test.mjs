import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";
import React from "react";
import { act, create } from "react-test-renderer";
import ts from "typescript";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const require = createRequire(import.meta.url);
const sourceRoot = new URL("../../src/legal/", import.meta.url);

function loadModule(name, dependencies, globals = {}) {
  const source = fs.readFileSync(new URL(name, sourceRoot), "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(output, {
    module, exports: module.exports,
    require: (specifier) => specifier in dependencies ? dependencies[specifier] : require(specifier),
    AbortController, TextDecoder, Uint8Array, ...globals,
  }, { filename: name });
  return module.exports;
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
  const api = { post: async (path, payload) => {
    requests.push({ path, payload });
    if (failApproval) throw { response: { data: { detail: "审批被拒绝" } } };
    return { data: { messages: [], pending_actions: [{ id: "a1", status: "approved" }] } };
  } };
  const { createCaseAssistantActions } = loadModule("services/assistantActions.tsx", {
    antd: { message: messages },
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
  assert.equal(state.pending_actions[0].status, "approved");
  assert.equal(decisionLoading, "");

  failApproval = true;
  await actions.decideCaseAgentAction({ id: "a1" }, "rejected");
  assert.equal(notices.at(-1)[1], "审批被拒绝");
  assert.equal(decisionLoading, "");

  failFetch = true;
  await actions.sendCaseAgentMessage("请重试");
  assert.match(state.messages.at(-1).content, /模型本轮生成失败/);
  assert.equal(notices.at(-1)[0], "error");
  assert.equal(sending, false);
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

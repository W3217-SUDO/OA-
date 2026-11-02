// 501147（tgn 11-03 00:04）：左侧“任务处理 / 收文助手 / 客户与合同”是会话归集，点开只列出该类历史会话，不下任何指令。
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";
import React from "react";
import { act, create } from "react-test-renderer";
import ts from "typescript";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const sourceRoot = new URL("../src/personal-agent/", import.meta.url);

function loadModule(name, dependencies = {}) {
  const entry = fileURLToPath(new URL(name, sourceRoot));
  const compilerOptions = { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true };
  const modules = new Map();
  const resolveLocal = (specifier, filename) => ts.resolveModuleName(specifier, filename, compilerOptions, ts.sys).resolvedModule.resolvedFileName;
  const loadSource = filename => {
    if (modules.has(filename)) return modules.get(filename).exports;
    const output = ts.transpileModule(fs.readFileSync(filename, "utf8"), { compilerOptions, fileName: filename }).outputText;
    const module = { exports: {} };
    modules.set(filename, module);
    const localRequire = createRequire(filename);
    vm.runInNewContext(output, {
      module, exports: module.exports, URL, URLSearchParams, Error, Set, Map,
      require: specifier => {
        if (Object.hasOwn(dependencies, specifier)) return dependencies[specifier];
        if (!specifier.startsWith(".")) return localRequire(specifier);
        if (specifier.endsWith(".css")) { fs.accessSync(new URL(specifier, pathToFileURL(filename))); return {}; }
        return loadSource(resolveLocal(specifier, filename));
      },
    }, { filename });
    return module.exports;
  };
  return loadSource(entry);
}

test("左侧固定任务展开为会话归集，最新在上，点会话只进入不发指令", async () => {
  const opened = [], started = [];
  const component = name => ({ children, ...props }) => React.createElement(name, props, children);
  const { AssistantWorkspaceSidebar } = loadModule("AssistantWorkspaceSidebar.tsx", {
    antd: { Button: component("button"), Tooltip: component("tooltip") },
    "@ant-design/icons": new Proxy({}, { get: () => "icon" }),
    "./ConfirmationHistory": { ConfirmationHistory: "confirmation-history" },
    "./ConversationWorkspaceNavigation": { ConversationWorkspaceNavigation: "workspace-navigation" },
    "./ConversationManager": { ConversationManager: ({ navigation }) => React.createElement("conversation-manager", null, navigation(null)) },
  });
  const entries = [{ key: "tasks", label: "任务处理", skillId: "my-tasks", hint: "" }, { key: "intake", label: "收文助手", skillId: "court-doc-intake", hint: "" }, { key: "customer", label: "客户与合同", skillId: "customer-contract-case", hint: "" }];
  const workspace = { taskEntries: entries, state: { conversation_id: "t-new" }, loading: false, stopping: false, uploading: false, decisionId: null, conversationBusy: false, runningIds: [], workspaceProjects: [], currentWorkspace: { kind: "personal" },
    conversations: [
      { id: "t-old", title: "任务处理", updated_at: "2026-11-01T02:00:00Z", skill_id: "my-tasks" },
      { id: "x", title: "普通对话", updated_at: "2026-11-02T09:00:00Z" },
      { id: "t-new", title: "任务处理 11-02", updated_at: "2026-11-02T08:00:00Z", skill_id: "my-tasks" },
      { id: "c1", title: "客户与合同", updated_at: "2026-11-02T03:00:00Z", skill_id: "customer-contract-case" },
    ] };
  let renderer;
  await act(async () => { renderer = create(React.createElement(AssistantWorkspaceSidebar, { workspace, name: "AI助手", onOpenPersonalSpace() {}, onReopenConfirmation: async () => {}, onStartIntake: () => started.push("intake"), onStartTask: id => started.push(id), onOpenTaskConversation: (id, skill) => opened.push([id, skill]) })); });
  const group = label => renderer.root.findAllByType("button").find(item => [].concat(item.props.children).some(child => child?.props?.children === label));
  assert.equal(renderer.root.findAllByType("ul").length, 0, "默认收起");
  await act(async () => { group("任务处理").props.onClick(); });
  assert.equal(started.length, 0, "点左侧不自动发“我今日的任务”");
  assert.equal(group("任务处理").props["aria-expanded"], true);
  const rows = () => renderer.root.findByProps({ "aria-label": "任务处理会话" }).findAllByType("li").map(item => item.findByType("button"));
  assert.deepEqual(rows().map(item => item.findByType("span").props.children), ["任务处理 11-02", "任务处理"], "只列这一类，最新在上");
  assert.equal(rows()[0].props["aria-current"], "true");
  await act(async () => { rows()[1].props.onClick(); });
  assert.deepEqual(JSON.parse(JSON.stringify(opened)), [["t-old", "my-tasks"]]);
  assert.equal(started.length, 0, "进入历史会话也不发指令");
  await act(async () => { group("收文助手").props.onClick(); });
  const empty = renderer.root.findByProps({ "aria-label": "收文助手会话" }).findAllByType("li");
  assert.equal(empty[0].props.children.join(""), "暂无会话，点对话框上方的“收文助手”开始");
  await act(async () => { group("任务处理").props.onClick(); });
  assert.equal(renderer.root.findAllByProps({ "aria-label": "任务处理会话" }).length, 0, "再点收起");
  await act(async () => { renderer.unmount(); });
});

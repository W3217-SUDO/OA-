// 501185（陶国南 11-03 09:36）：智能体首页“案件空间”点案件，跳到案件详情并弹出案件智能体浮窗。
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

test("501185：智能体首页点案件空间里的案件，跳到该案件详情并打开案件智能体，不在智能体页切换空间", async () => {
  const opened = [], selected = [];
  const component = name => ({ children, ...props }) => React.createElement(name, props, children);
  const { ConversationWorkspaceNavigation } = loadModule("ConversationWorkspaceNavigation.tsx", {
    antd: { Button: component("button"), Tooltip: ({ children }) => children, message: { error() {} } },
    "@ant-design/icons": new Proxy({}, { get: () => "icon" }),
    "./CaseWorkspaceSelector": { CaseWorkspaceSelector: component("case-selector") },
    "./conversationWorkspace": { PERSONAL_CONVERSATION_WORKSPACE: { kind: "personal" } },
    "./types": { errorText: (_error, fallback) => fallback },
  });
  const workspace = { loading: false, conversationBusy: false, uploading: false, decisionId: null, dismissalId: null, loadError: "",
    status: { commands: [{ id: "cases" }] }, currentWorkspace: { kind: "personal" },
    workspaceProjects: [{ kind: "case", case_id: 441, serial_no: "HZMS2600441", title: "浙江大光明", available: true }],
    selectWorkspace: async target => { selected.push(target); } };
  let renderer;
  await act(async () => { renderer = create(React.createElement(ConversationWorkspaceNavigation, { workspace, onOpenCaseAgent: (id, serial) => opened.push([id, serial]) })); });
  const project = renderer.root.findAllByType("button").find(item => item.props.className === "assistant-workspace-project");
  await act(async () => { project.props.onClick(); });
  assert.deepEqual(JSON.parse(JSON.stringify(opened)), [[441, "HZMS2600441"]], "跳到这个案件详情并打开智能体");
  assert.equal(selected.length, 0, "不再停在智能体页切换到案件空间");
  await act(async () => { await renderer.root.findByType("case-selector").props.onSelect({ id: 445, serial_no: "HZMS2600445-R", title: "测试" }); });
  assert.deepEqual(JSON.parse(JSON.stringify(opened.at(-1))), [445, "HZMS2600445-R"], "新选的案件也直接跳到详情");
  await act(async () => { renderer.unmount(); });
});

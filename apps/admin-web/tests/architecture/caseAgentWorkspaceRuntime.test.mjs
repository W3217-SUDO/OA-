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

test("系统技能查看完整声明，删除读取最新版本并明确确认后写入且真实刷新", async () => {
  const calls = [], notices = [];
  let revision = 3, refreshed = 0;
  const item = { id: "general-office", name: "通用办公", category: "办公", description: "完整说明", source: "内置", available: true };
  const instruction = "实际运行指令\n".repeat(1000);
  const { SystemSkillPanel } = loadModule("../SystemSkillPanel.tsx", {
    antd: {
      Alert: "alert", Button: "button", Descriptions: Object.assign(props => React.createElement("descriptions", props), { Item: "description" }),
      Drawer: ({ open, children, ...props }) => open ? React.createElement("drawer", props, children) : null,
      Modal: ({ open, children, ...props }) => open ? React.createElement("modal", props, children) : null,
      Space: "space", Spin: "spin", Tag: "tag", Tooltip: "tooltip", message: { success: value => notices.push(value) },
    },
    "./components/ResizableTable": ({ columns, dataSource }) => React.createElement("table", null, dataSource.map(row => React.createElement("tr", { key: row.id }, columns.at(-1).render(null, row)))),
    "./api": { api: {
      get: async path => { calls.push({ method: "GET", path }); return { data: { ...item, category: "最新分类", description: "最新说明", source: "最新来源", scope: "system", filename: "SKILL.md", content: `# 完整声明\n${instruction}`, instruction, quick_prompts: ["示例一", "示例二"], can_delete: true, revision, definition_sha256: "a".repeat(64), content_origin: "runtime_declaration", resources: [] } }; },
      delete: async (path, config) => { calls.push({ method: "DELETE", path, config }); return { data: { id: item.id, scope: "system", deleted: true, deletion_mode: "registry_deactivation", revision: revision + 1 } }; },
    } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(SystemSkillPanel, { items: [item], canManage: true, onChanged: async () => { refreshed += 1; } })); });
  const action = name => renderer.root.findAllByType("button").find(button => button.props["aria-label"] === `${name}通用办公`);
  await act(async () => { await action("查看").props.onClick(); });
  assert.equal(calls.at(-1).path, "/agent/system-skills/general-office/definition");
  assert.equal(renderer.root.findAllByType("pre")[0].props.children, instruction);
  assert.equal(renderer.root.findAllByType("li").length, 2);
  assert.ok(renderer.root.findAllByType("description").some(field => field.props.children === "最新来源"), "详情元数据读取GET实际字段，不沿用列表快照");
  assert.equal(renderer.root.findAllByType("modal").length, 0);
  revision = 4;
  await act(async () => { await action("删除").props.onClick(); });
  assert.equal(calls.length, 2, "点击删除先重新读取详情，尚未DELETE");
  await act(async () => { renderer.root.findByType("modal").props.onCancel(); });
  assert.equal(calls.length, 2, "取消不写入");
  await act(async () => { await action("删除").props.onClick(); });
  assert.equal(renderer.root.findByType("modal").props.okButtonProps.danger, true);
  await act(async () => { await renderer.root.findByType("modal").props.onOk(); });
  assert.equal(calls.at(-1).path, "/agent/system-skills/general-office");
  assert.deepEqual(JSON.parse(JSON.stringify(calls.at(-1).config)), { data: { confirm: true, revision: 4, definition_sha256: "a".repeat(64) } });
  assert.equal(refreshed, 1);
  assert.equal(notices.length, 1);
  assert.equal(renderer.root.findAllByType("drawer").length, 0);
  await act(async () => { renderer.update(React.createElement(SystemSkillPanel, { items: [item], canManage: false, onChanged: async () => {} })); });
  assert.equal(action("删除"), undefined, "非管理账号不出现删除控件");
  assert.ok(action("查看"), "查看沿用原页面权限，不按删除权限隐藏");
  await act(async () => { renderer.unmount(); });
});

test("系统技能详情/删除失败显示真实错误，刷新失败不重复删除，失效读取不可打开确认", async () => {
  const item = { id: "office", name: "办公", available: true };
  let failure = "", deletes = 0, refreshes = 0, pending;
  const { SystemSkillPanel } = loadModule("../SystemSkillPanel.tsx", {
    antd: {
      Alert: "alert", Button: "button", Descriptions: Object.assign(props => React.createElement("descriptions", props), { Item: "description" }),
      Drawer: ({ open, children, ...props }) => open ? React.createElement("drawer", props, children) : null,
      Modal: ({ open, children, ...props }) => open ? React.createElement("modal", props, children) : null,
      Space: "space", Spin: "spin", Tag: "tag", Tooltip: "tooltip", message: { success() {} },
    },
    "./components/ResizableTable": ({ columns }) => React.createElement("table", null, columns.at(-1).render(null, item)),
    "./personal-agent/types": { errorText: (error, fallback) => error.response?.data?.detail || error.message || fallback },
    "./api": { api: {
      get: async () => {
        if (failure === "read") throw { response: { status: 403, data: { detail: "无权读取系统技能" } } };
        const data = { ...item, scope: "system", content: "完整声明", instruction: "指令", quick_prompts: [], resources: [], content_origin: "runtime_declaration", can_delete: failure !== "permission", revision: 1, definition_sha256: "b".repeat(64) };
        if (failure === "pending") return new Promise(resolve => { pending = () => resolve({ data }); });
        return { data };
      },
      delete: async () => { deletes += 1; if (failure === "delete") throw { response: { status: 409, data: { detail: "注册版本已变化，请重新查看" } } }; return { data: { id: item.id, scope: "system", deleted: true, deletion_mode: "registry_deactivation", revision: 2 } }; },
    } },
  });
  let renderer;
  const props = { items: [item], canManage: true, onChanged: async () => { refreshes += 1; if (refreshes === 1) throw new Error("目录连接失败"); } };
  await act(async () => { renderer = create(React.createElement(SystemSkillPanel, props)); });
  const action = name => renderer.root.findAllByType("button").find(button => button.props["aria-label"] === `${name}办公`);
  const hasError = text => renderer.root.findAllByType("alert").some(alert => alert.props.title.includes(text));
  failure = "read";
  await act(async () => { await action("删除").props.onClick(); });
  assert.ok(hasError("无权读取")); assert.equal(renderer.root.findAllByType("modal").length, 0);
  failure = "permission";
  await act(async () => { await action("删除").props.onClick(); });
  assert.ok(hasError("无权删除")); assert.equal(renderer.root.findAllByType("modal").length, 0);
  failure = "delete";
  await act(async () => { await action("删除").props.onClick(); });
  await act(async () => { await renderer.root.findByType("modal").props.onOk(); });
  assert.ok(hasError("注册版本已变化")); assert.equal(refreshes, 0);
  failure = "";
  await act(async () => { await action("删除").props.onClick(); });
  await act(async () => { await renderer.root.findByType("modal").props.onOk(); });
  assert.ok(hasError("已删除，但目录刷新失败")); assert.equal(action("删除").props.disabled, true);
  await act(async () => { await renderer.root.findByType("alert").props.action.props.onClick(); });
  assert.equal(refreshes, 2); assert.equal(deletes, 2, "刷新重试不再次DELETE");
  failure = "pending";
  await act(async () => { action("删除").props.onClick(); });
  await act(async () => { renderer.root.findByType("drawer").props.onClose(); pending(); });
  assert.equal(renderer.root.findAllByType("modal").length, 0, "关闭后晚到的响应不能重新打开确认");
  await act(async () => { renderer.unmount(); });
});

test("空技能编码与个人草稿保留原默认，删除后置空且不替换其他技能", async () => {
  const routing = loadModule("../agentSkillRouting.ts", {});
  assert.equal(routing.DEFAULT_AGENT_SKILL, "general-office");
  assert.equal(routing.encodeAgentSkillMessage("", " 普通问题 "), "普通问题");
  assert.equal(routing.encodeAgentSkillMessage("general-office", "问题"), "[[skill:general-office]]\n问题");
  const { usePersonalDrafts } = loadModule("../personal-agent/usePersonalDrafts.ts", {});
  let drafts, renderer;
  function Probe() { drafts = usePersonalDrafts(); return null; }
  await act(async () => { renderer = create(React.createElement(Probe)); });
  const catalog = [{ id: "general-office", available: true }, { id: "other", available: true }];
  await act(async () => { drafts.refreshSkills(catalog); drafts.update("a", "input", "草稿A"); drafts.update("b", "skillId", ""); drafts.update("c", "skillId", "other"); });
  assert.equal(drafts.items.a.skillId, "general-office");
  await act(async () => { drafts.refreshSkills(catalog.slice(1)); });
  assert.equal(drafts.items.a.skillId, ""); assert.equal(drafts.items.a.input, "草稿A");
  assert.equal(drafts.items.b.skillId, ""); assert.equal(drafts.items.c.skillId, "other");
  assert.equal(drafts.empty.current.skillId, "", "新草稿默认不能恢复已删除通用办公");
  await act(async () => { drafts.update("d", "input", "新草稿"); drafts.refreshSkills(catalog); });
  assert.equal(drafts.items.d.skillId, "", "显式空选项不因目录变更自动选回默认");
  assert.equal(drafts.empty.current.skillId, "general-office", "新草稿在通用办公可用时维持原默认");
  await act(async () => { renderer.unmount(); });
});

test("系统技能目录通知刷新已挂载个人工作区，空技能真实发送且失败向管理面板传播", async () => {
  const catalog = loadModule("../agentSkillCatalog.ts", {});
  let items = [{ id: "general-office", name: "办公", available: true }, { id: "other", name: "其他", available: true }], fail = false, reads = 0;
  const generations = [], errors = [];
  const state = { conversation_id: "conversation", messages: [], pending_actions: [], dismissed_action_ids: [] };
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { error: value => errors.push(value), warning: value => errors.push(value) } },
    "../legal/constants": {},
    "../legal/services/agentDocumentConfirmation": { confirmCaseAgentDocument() {} },
    "./personalAiDocumentConfirmation": { confirmPersonalAiDocument() {} },
    "../agentSkillCatalog": catalog,
    "../api": { api: { get: async path => {
      if (path === "/agent/skills") { reads++; if (fail) throw new Error("真实目录请求失败"); return { data: { items } }; }
      assert.equal(path, "/personal-agent/status"); return { data: { ready: true } };
    } } },
    "./usePersonalMcpConnection": { usePersonalMcpConnection: () => ({ intercept: () => false, close() {} }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ loading: false, load: async () => {}, locked: () => false, capture: () => ({}), refresh: async () => {} }) },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state, activities: {}, reset() {}, anyRunning: () => false, running: () => false, stopping: () => false, get: () => state, generate: async (_conversation, payload, message) => { generations.push({ payload, message }); return state; } }) },
  });
  let workspace, renderer;
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  await act(async () => { renderer = create(React.createElement(Probe)); });
  assert.equal(workspace.skillId, "general-office");
  await act(async () => { workspace.setInput("保留草稿"); items = items.slice(1); await catalog.refreshAgentSkillCatalogConsumers(); });
  assert.equal(workspace.skillId, ""); assert.equal(workspace.input, "保留草稿"); assert.equal(workspace.skills.length, 1);
  await act(async () => { await workspace.send(); });
  assert.equal(generations[0].payload.skill_id, ""); assert.equal(generations[0].payload.content, "保留草稿");
  assert.equal(generations[0].message.skill_name, undefined, "不向history伪写通用办公技能名");
  await act(async () => { workspace.setSkillId("general-office"); await workspace.send("显式已删技能"); });
  assert.equal(generations.length, 1, "已删显式ID不能被自动换为空技能发出");
  assert.ok(errors.some(value => value.includes("所选技能已停用")));
  fail = true;
  await assert.rejects(catalog.refreshAgentSkillCatalogConsumers(), /真实目录请求失败/);
  await act(async () => { renderer.unmount(); });
  const before = reads; await catalog.refreshAgentSkillCatalogConsumers(); assert.equal(reads, before, "卸载后解除通知订阅");
});

test("案件技能加载保留历史空值/显式空值，缺失ID清空而不是自动替换", async () => {
  let picked, active = "", messages = [], items = [{ id: "general-office", available: true }, { id: "other", available: true }];
  const { createCaseAssistantActions } = loadModule("services/assistantActions.tsx", {
    antd: { message: { error: text => assert.fail(text) } },
    "../../AgentOperationPreview": {},
    "./agentDocumentConfirmation": {},
    "../constants": {},
    "../../api": { api: { get: async path => {
      if (path.endsWith("/agents")) return { data: { agents: [{ id: 1 }] } };
      if (path.endsWith("/conversations")) return { data: { conversations: [{ id: 2 }] } };
      return { data: path.endsWith("/status") ? { skills: items } : { active_skill: active, messages } };
    } } },
  });
  const noop = () => {};
  const context = { setAgentLoading: noop, setAgentStatus: noop, setAgentState: noop, setAgentDocuments: noop, setAgentDocumentIds: noop,
    setAgentSkillId: value => { picked = value; }, setAgentCatalog: noop, setAgentConversations: noop, setAgentId: noop, setConversationId: noop,
    activeAgentLoadRequestRef: { current: null }, activeAgentDocumentsRequestRef: { current: null }, setAgentDocumentsLoading: noop };
  const actions = createCaseAssistantActions(context);
  await actions.loadCaseAgent({ id: 8 }); assert.equal(picked, "general-office", "新对话仍用可用的原默认");
  messages = [{ role: "user", content: "普通问题" }];
  await actions.loadCaseAgent({ id: 8 }); assert.equal(picked, "", "历史明确空技能不恢复默认");
  active = "other";
  await actions.loadCaseAgent({ id: 8 }, false, undefined, undefined, ""); assert.equal(picked, "", "用户手动清空优先于旧active_skill");
  await actions.loadCaseAgent({ id: 8 }, false, undefined, undefined, "deleted"); assert.equal(picked, "", "显式失效ID不自动换成active技能");
  items = items.slice(1); active = "general-office";
  await actions.loadCaseAgent({ id: 8 }); assert.equal(picked, "", "已删除默认不能复活");
});

test("skill market browses server catalog, previews full instructions and installs only after confirmation", async () => {
  const requests = [], installed = [];
  let previewFails = false, catalogFails = false, empty = false, refreshFails = false;
  const instruction = "完整技能正文\n".repeat(1000);
  const description = "来源中的完整长技能说明。".repeat(70);
  const { SkillCatalog } = loadModule("../personal-agent/SkillCatalog.tsx", {
    antd: { Alert: "alert", Button: "button", Empty: "empty", Input: "input", Select: "select", Spin: "spin" },
    "../api": { api: {
      get: async (path, options) => {
        requests.push({ method: "GET", path, params: options.params });
        if (catalogFails) throw new Error("目录连接失败");
        const source = options.params.source;
        return { data: { source, query: options.params.q || "skill", items: empty ? [] : [{ id: "anthropics/skills/pdf", name: "pdf", description: "PDF tools", source, market_url: "https://skills.sh/anthropics/skills/pdf", repo: "anthropics/skills", skill_slug: "pdf" }] } };
      },
      post: async (path, body) => {
        requests.push({ method: "POST", path, body });
        if (path.endsWith("/preview")) {
          if (previewFails) throw new Error("此来源不支持导入");
          return { data: { name: "pdf", description, instruction, source: "https://github.com/anthropics/skills", url: "https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md", sha256: "content-hash" } };
        }
        return { data: { id: "personal-pdf", available: true } };
      },
    } },
    "./types": { errorText: (error, fallback) => error.message || fallback },
  });
  function Harness({ scope } = {}) {
    const [busy, setBusy] = React.useState(false);
    return React.createElement(SkillCatalog, { active: true, busy, scope, onBusy: setBusy, onInstalled: async skill => { if (refreshFails) throw new Error("列表网络失败"); installed.push(skill.id); } });
  }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Harness)); });
  const button = label => renderer.root.findAllByType("button").find(item => item.props.children === label);
  assert.equal(requests[0].params.source, "skills-sh");
  assert.equal(renderer.root.findAllByType("article").length, 1);
  await act(async () => { renderer.root.findByType("input").props.onChange({ target: { value: "pdf" } }); });
  assert.equal(requests.length, 1, "输入文字不会自动发送搜索");
  await act(async () => { button("搜索技能").props.onClick(); });
  assert.equal(requests.at(-1).params.q, "pdf");
  await act(async () => { await button("选择并预览").props.onClick(); });
  assert.equal(requests.at(-1).path, "/agent/skills/catalog/preview");
  assert.equal(requests.at(-1).body.id, "anthropics/skills/pdf");
  assert.equal(requests.at(-1).body.q, "pdf");
  assert.equal(renderer.root.findByType("pre").props.children, instruction, "大于6000字符仍完整显示");
  assert.ok(description.length > 500 && renderer.root.findAllByType("p").some(item => item.props.children === description), "真实长说明不截断");
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 0);
  await act(async () => { button("取消选择").props.onClick(); });
  assert.equal(renderer.root.findAllByType("pre").length, 0);
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 0, "取消不安装");
  await act(async () => { await button("选择并预览").props.onClick(); });
  await act(async () => { await button("确认安装到个人技能").props.onClick(); });
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 1);
  assert.equal(requests.at(-1).body.sha256, "content-hash");
  assert.deepEqual(installed, ["personal-pdf"]);
  previewFails = true;
  await act(async () => { await button("选择并预览").props.onClick(); });
  assert.ok(renderer.root.findAllByType("alert").some(item => item.props.description === "此来源不支持导入"));
  assert.equal(installed.length, 1);
  previewFails = false; refreshFails = true;
  await act(async () => { await button("选择并预览").props.onClick(); });
  await act(async () => { await button("确认安装到个人技能").props.onClick(); });
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 2);
  assert.equal(installed.length, 1, "列表刷新失败时不选中未载入技能");
  assert.ok(renderer.root.findAllByType("alert").some(item => item.props.title === "技能已安装，待刷新个人库" && item.props.description.includes("已安装，但列表刷新失败")));
  assert.equal(renderer.root.findAllByType("pre").length, 0, "成功落库后移除再次安装按钮");
  refreshFails = false;
  await act(async () => { renderer.root.findAllByType("alert").find(item => item.props.action)?.props.action.props.onClick(); });
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 2, "重试刷新不重复安装");
  assert.equal(installed.length, 2);
  catalogFails = true;
  await act(async () => { renderer.root.findByType("select").props.onChange("openai"); });
  assert.equal(requests.at(-1).params.source, "openai");
  assert.ok(renderer.root.findAllByType("alert").some(item => item.props.description === "目录连接失败"));
  catalogFails = false; empty = true;
  await act(async () => { renderer.root.findAllByType("alert").find(item => item.props.action)?.props.action.props.onClick(); });
  assert.equal(renderer.root.findByType("empty").props.description, "没有找到技能，请尝试英文技能名或切换来源");
  empty = false;
  await act(async () => { renderer.update(React.createElement(Harness, { scope: "global" })); });
  await act(async () => { renderer.root.findAllByType("button").find(item => item.props["aria-label"] === "刷新技能目录").props.onClick(); });
  await act(async () => { button("选择并预览").props.onClick(); });
  assert.ok(renderer.root.findAllByType("p").some(item => String(item.props.children).includes("全所账号可选用")));
  await act(async () => { button("确认安装到全局技能").props.onClick(); });
  assert.equal(requests.at(-1).path, "/agent/global-skills/github/install", "全局只向全局端点写入");
  await act(async () => { renderer.unmount(); });
});

test("GitHub URL install reports persisted success separately from personal-library refresh failure", async () => {
  const requests = [], selected = [];
  let refreshFails = true;
  const form = { resetFields() {}, setFieldsValue() {} };
  const Form = Object.assign(({ children, ...props }) => React.createElement("form", props, children), { useForm: () => [form], Item: "form-item" });
  const Input = Object.assign(props => React.createElement("input", props), { TextArea: "textarea" });
  const { SkillManager } = loadModule("../personal-agent/SkillManager.tsx", {
    antd: { Alert: "alert", Button: "button", Empty: "empty", Form, Input, Modal: "modal", Space: "space", Switch: "switch", Tabs: "tabs", Tooltip: "tooltip", message: { success() {}, info() {}, error() {} } },
    "./SkillCatalog": { SkillCatalog: () => null },
    "../capability-market/CapabilityMarket": { CapabilityMarket: "capability-market" },
    "./types": { errorText: (error, fallback) => error.message || fallback },
    "../api": { api: { post: async (path, body) => {
      requests.push({ path, body });
      return path.endsWith("/preview") ? { data: { name: "docx", description: "完整说明".repeat(210), instruction: "完整正文".repeat(1700), source: "https://github.com/anthropics/skills", url: "https://github.com/anthropics/skills/blob/main/skills/docx/SKILL.md", sha256: "hash" } } : { data: { id: "personal-docx", available: true } };
    } } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(SkillManager, { open: true, onClose() {}, skills: [], refresh: async () => { if (refreshFails) throw new Error("列表加载失败"); }, onSelect: id => selected.push(id) })); });
  const button = label => renderer.root.findAllByType("button").find(item => item.props.children === label);
  assert.equal(renderer.root.findAllByType("form-item").find(item => item.props.name === "description").props.rules[0].max, 8000);
  await act(async () => { renderer.root.findByType("tabs").props.onChange("github"); });
  await act(async () => { renderer.root.findAllByType("input").find(item => item.props["aria-label"] === "GitHub 技能链接").props.onChange({ target: { value: "https://github.com/anthropics/skills/tree/main/skills/docx" } }); });
  await act(async () => { button("预览技能").props.onClick(); });
  await act(async () => { button("确认安装并选中").props.onClick(); });
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 1);
  assert.equal(selected.length, 0);
  assert.ok(renderer.root.findAllByType("alert").some(item => item.props.message?.includes("技能已安装，但列表刷新失败")));
  assert.equal(renderer.root.findAllByType("pre").length, 0, "成功落库后不保留再次安装入口");
  refreshFails = false;
  await act(async () => { renderer.root.findAllByType("alert").find(item => item.props.action).props.action.props.onClick(); });
  assert.equal(requests.filter(item => item.path.endsWith("/install")).length, 1);
  assert.deepEqual(selected, ["personal-docx"]);
  assert.equal(renderer.root.findByType("tabs").props.activeKey, "mine");
  await act(async () => { renderer.update(React.createElement(SkillManager, { open: true, onClose() {}, mode: "import-only", scope: "global", skills: [{ id: "personal-docx", scope: "personal", custom: true, name: "本人导入技能", available: true, quick_prompts: [] }, { id: "global-one", scope: "global", custom: true, name: "全局示例", quick_prompts: [] }], refresh: async () => {}, onSelect: id => selected.push(id) })); });
  assert.deepEqual(Array.from(renderer.root.findByType("tabs").props.items, item => item.key), ["mine", "github"], "仅导入入口不提供技能包市场与手工管理页");
  assert.equal(renderer.root.findAllByType("switch").length, 0);
  assert.equal(renderer.root.findAllByType("form-item").length, 0);
  assert.equal(renderer.root.findAllByType("capability-market").length, 0);
  assert.equal(renderer.root.findAllByType("button").some(item => ["新增技能", "编辑技能", "删除技能"].includes(item.props["aria-label"])), false);
  const importedNames = renderer.root.findAllByType("b").map(item => item.props.children);
  assert.ok(importedNames.includes("本人导入技能") && !importedNames.includes("全局示例"), "仅导入模式强制本人作用域，不采纳传入的global");
  await act(async () => { button("使用").props.onClick(); });
  assert.deepEqual(selected, ["personal-docx", "personal-docx"], "本人已导入技能仍能真实选用");
  await act(async () => { renderer.update(React.createElement(SkillManager, { open: true, onClose() {}, scope: "global", skills: [{ id: "global-one", scope: "global", custom: true, name: "全局示例", quick_prompts: [] }, { id: "personal-one", scope: "personal", custom: true, name: "个人示例", quick_prompts: [] }], refresh: async () => {} })); });
  const visibleNames = renderer.root.findAllByType("b").map(item => item.props.children);
  assert.ok(visibleNames.includes("全局示例") && !visibleNames.includes("个人示例"), "全局管理列表不暴露个人编辑项");
  assert.equal(renderer.root.findAllByType("button").some(item => item.props.children === "使用"), false, "全局中心不强行选用聊天技能");
  await act(async () => { renderer.root.findByType("tabs").props.onChange("github"); });
  await act(async () => { renderer.root.findAllByType("input").find(item => item.props["aria-label"] === "GitHub 技能链接").props.onChange({ target: { value: "https://github.com/anthropics/skills/tree/main/skills/docx" } }); });
  await act(async () => { button("预览技能").props.onClick(); });
  assert.equal(requests.at(-1).path, "/agent/global-skills/github/preview");
  await act(async () => { button("确认安装到全局技能").props.onClick(); });
  assert.equal(requests.at(-1).path, "/agent/global-skills/github/install");
  assert.deepEqual(selected, ["personal-docx", "personal-docx"], "global无onSelect不会改变原个人选中项");
  await act(async () => { renderer.unmount(); });
});

test("capability market previews before install and preserves persisted success on refresh failure", async () => {
  const requests = [], selected = [];
  let refreshFails = true;
  const item = { id: "a".repeat(24), kind: "expert", name: "诉讼专家", description: "案件材料分析", category: "法务安全",
    author: "验证来源", license: "Apache-2.0", version: "1", tags: [], avatar: "", source: "https://example.org/source",
    members: [], unavailable_reason: "", sha256: "b".repeat(64), installed: [] };
  const { CapabilityMarket } = loadModule("../capability-market/CapabilityMarket.tsx", {
    antd: { Alert: "alert", Button: "button", Drawer: ({ open, footer, children, ...props }) => open ? React.createElement("drawer", props, children, footer) : null, Empty: "empty", Input: "input", Pagination: "pagination",
      Segmented: "segmented", Skeleton: "skeleton", Tabs: "tabs", Tag: "tag", Tooltip: "tooltip", message: { success() {} } },
    "./CapabilityAvatar": { CapabilityAvatar: "avatar" },
    "../personal-agent/types": { errorText: (error, fallback) => error.message || fallback },
    "../api": { api: {
      get: async path => {
        requests.push({ method: "GET", path });
        if (path === "/capability-market") return { data: { items: [item] } };
        if (path === `/capability-market/items/${item.id}`) return { data: { ...item, instruction: "完整指令", resources: [], license_documents: {}, connection_configs: {}, excluded_resources: [] } };
        throw new Error("未预期的目录请求");
      },
      post: async (path, body) => {
        requests.push({ method: "POST", path, body });
        return { data: { id: "personal-example", available: true } };
      },
    } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(CapabilityMarket, {
    active: true, onInstalled: async () => { if (refreshFails) throw new Error("技能列表刷新失败"); }, onSelect: id => selected.push(id),
  })); });
  const button = label => renderer.root.findAllByType("button").find(control => control.props.children === label);
  await act(async () => { button("查看详情").props.onClick(); });
  assert.equal(requests.filter(request => request.method === "POST").length, 0, "查看不安装");
  assert.equal(renderer.root.findByType("pre").props.children, "完整指令");
  await act(async () => { button("安装到个人技能").props.onClick(); });
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).body)), { scope: "personal", sha256: item.sha256 });
  assert.ok(renderer.root.findAllByType("alert").some(alert => alert.props.title.includes("能力已安装，但技能库刷新失败")));
  assert.equal(button("安装到个人技能"), undefined, "落库后不能重复安装");
  assert.equal(requests.filter(request => request.method === "POST").length, 1);
  assert.equal(button("使用"), undefined, "列表刷新失败不能提前选中");
  refreshFails = false;
  await act(async () => { button("刷新技能库").props.onClick(); });
  assert.equal(requests.filter(request => request.method === "POST").length, 1, "重试刷新不重复安装");
  await act(async () => { button("使用").props.onClick(); });
  assert.deepEqual(selected, ["personal-example"]);
  await act(async () => { renderer.unmount(); });
});

test("connector panel saves scoped configuration, preserves credentials and exposes links and failed verification", async () => {
  const requests = [], changed = [];
  const configuration = { "mcp.json": { mcpServers: { remote: { type: "streamableHttp", url: "https://example.org/mcp", headers: { Authorization: "" } } } } };
  const initial = { configuration, revision: "d".repeat(32), saved: true, status: "configured", error: "", last_checked: null, servers: [],
    secret_fields: [{ path: ["mcp.json", "mcpServers", "remote", "headers", "Authorization"], label: "remote · Authorization", configured: true, template: "" }],
    links: [{ label: "服务账号授权", url: "https://example.org/login" }] };
  const Input = Object.assign(props => React.createElement("input", props), { Password: "password", TextArea: "textarea" });
  const Form = Object.assign(props => React.createElement("form", props), { Item: "form-item" });
  const { ConnectorConfigPanel } = loadModule("../capability-market/ConnectorConfigPanel.tsx", {
    antd: { Alert: "alert", Button: "button", Checkbox: "checkbox", Form, Input, Popconfirm: "confirm", Select: "select", Skeleton: "skeleton", Tag: "tag", message: { success() {}, error() {} } },
    "../personal-agent/types": { errorText: (error, fallback) => error.message || fallback },
    "../api": { api: {
      get: async (path, options) => { requests.push({ method: "GET", path, scope: options.params.scope }); return { data: initial }; },
      put: async (path, body) => { requests.push({ method: "PUT", path, body }); return { data: { ...initial, revision: "e".repeat(32) } }; },
      post: async (path, body) => { requests.push({ method: "POST", path, body }); return { data: { ok: false, configuration: { ...initial, revision: "e".repeat(32), status: "failed", error: "服务返回HTTP401，请先授权" } } }; },
    } },
  }, { structuredClone });
  let renderer;
  await act(async () => { renderer = create(React.createElement(ConnectorConfigPanel, { itemId: "c".repeat(24), name: "连接器", scope: "personal", onBusy() {}, onChanged: value => changed.push(value) })); });
  const button = label => renderer.root.findAllByType("button").find(control => control.props.children === label);
  assert.equal(requests.length, 1, "打开配置不自动连接");
  assert.equal(requests[0].scope, "personal");
  assert.equal(button("服务账号授权").props.href, "https://example.org/login");
  assert.equal(button("服务账号授权").props.target, "_blank");
  assert.equal(renderer.root.findByType("password").props.value, "", "不显示已保存的凭据");
  await act(async () => { button("保存配置").props.onClick(); });
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).body.keep_credentials)), [initial.secret_fields[0].path]);
  assert.equal(requests.at(-1).body.scope, "personal");
  await act(async () => { button("测试连接").props.onClick(); });
  assert.equal(requests.at(-1).body.revision, "e".repeat(32));
  assert.equal(changed.at(-1).status, "failed");
  assert.ok(renderer.root.findAllByType("alert").some(alert => alert.props.title === "服务返回HTTP401，请先授权"));
  assert.equal(renderer.root.findAllByType("button").some(control => String(control.props.children).includes("安装到")), false, "连接器不显示技能安装命令");
  await act(async () => { renderer.unmount(); });
});

test("personal AI skill directory preserves owned definitions and downloads with import-only selection", async () => {
  const requests = [], savedDownloads = [], revoked = [], selected = [];
  let runtimeRefreshes = 0;
  const content = "---\nname: own-skill\n---\n" + "完整定义\n".repeat(1500);
  const downloadBytes = new Blob([content], { type: "text/markdown" });
  const api = {
    get: async (path, options) => {
      requests.push({ path, options });
      if (path.endsWith("/download")) return { data: downloadBytes, headers: { "content-disposition": 'attachment; filename="own-skill.md"' } };
      if (path.endsWith("/definition")) return { data: { id: "own", name: "本人技能", scope: "personal", filename: "own-skill.md", content, definition_sha256: "current-definition-sha", import_sha256: "original-import-sha" } };
      return { data: { items: [{ id: "own", name: "本人技能", scope: "personal", custom: true, enabled: true, available: true, description: "本人说明" }] } };
    },
    patch: async (path, body) => { requests.push({ path, body }); },
  };
  const { PersonalAiSpaceSkills } = loadModule("../personal-agent/PersonalAiSpaceSkills.tsx", {
    antd: { Alert: "alert", Button: "button", Empty: "empty", Modal: "modal", Spin: "spin", Switch: "switch", Tag: "tag" },
    "../api": { api }, "./SkillManager": { SkillManager: "skill-manager" }, "./types": { errorText: (error, fallback) => error.message || fallback },
  }, {
    URL: { createObjectURL: blob => { assert.equal(blob, downloadBytes); return "blob:actual-response"; }, revokeObjectURL: url => revoked.push(url) },
    window: { setTimeout: (callback, delay) => { assert.equal(delay, 1000); callback(); } },
    document: { body: { appendChild() {} }, createElement: () => ({ href: "", download: "", click() { savedDownloads.push({ href: this.href, filename: this.download }); }, remove() {} }) },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalAiSpaceSkills, { active: false, busy: false })); });
  assert.equal(requests.length, 0, "默认文件Tab不会加载个人技能目录");
  const props = { active: true, busy: false, onSkillsChanged: async () => { runtimeRefreshes += 1; }, onSelect: id => selected.push(id) };
  await act(async () => { renderer.update(React.createElement(PersonalAiSpaceSkills, props)); });
  assert.equal(requests[0].path, "/agent/skills/personal");
  const button = label => renderer.root.findAllByType("button").find(item => item.props.children === label);
  await act(async () => { button("查看完整定义").props.onClick(); });
  assert.equal(requests.at(-1).path, "/agent/skills/own/definition");
  assert.equal(renderer.root.findByType("pre").props.children, content);
  const hashes = renderer.root.findAllByType("small").map(item => String(item.props.children));
  assert.ok(hashes.some(value => value.includes("当前定义 SHA256") && value.includes("current-definition-sha")));
  assert.ok(hashes.some(value => value.includes("导入时原文件 SHA256") && value.includes("original-import-sha")));
  await act(async () => { button("下载 MD").props.onClick(); });
  assert.equal(requests.at(-1).path, "/agent/skills/own/definition/download");
  assert.equal(requests.at(-1).options.responseType, "blob");
  assert.deepEqual(savedDownloads, [{ href: "blob:actual-response", filename: "own-skill.md" }]);
  assert.deepEqual(revoked, ["blob:actual-response"]);
  assert.equal(renderer.root.findAllByType("switch").length, 0, "个人目录不再开放用户启停管理");
  assert.equal(renderer.root.findAllByType("button").some(item => ["编辑技能", "删除技能"].includes(item.props["aria-label"])), false);
  await act(async () => { button("使用").props.onClick(); });
  assert.deepEqual(selected, ["own"], "选用本人可用技能，不产生管理写入");
  await act(async () => { button("导入个人技能").props.onClick(); });
  const manager = renderer.root.findByType("skill-manager");
  assert.equal(manager.props.open, true);
  assert.equal(manager.props.mode, "import-only");
  assert.equal(manager.props.scope, "personal");
  assert.equal(manager.props.skills[0].id, "own");
  assert.equal(manager.props.onSelect, props.onSelect);
  await act(async () => { await manager.props.refresh(); });
  assert.equal(requests.at(-1).path, "/agent/skills/personal");
  assert.equal(runtimeRefreshes, 1, "导入后刷新本人目录与原AI助手可选目录");
  assert.equal(requests.some(item => Object.hasOwn(item, "body")), false, "查看、下载、选用和刷新均不发送启停PATCH");
  await act(async () => { renderer.update(React.createElement(PersonalAiSpaceSkills, { ...props, busy: true })); });
  assert.equal(button("导入个人技能").props.disabled, true);
  assert.equal(button("使用").props.disabled, true, "工作区忙碌时保留选用阻断");
  assert.equal(requests.filter(item => item.path.includes("ai-space") || item.path.includes("global-skills")).length, 0, "技能目录不传输OSS或其他作用域");
  await act(async () => { renderer.unmount(); });
});

test("global skill management follows global permission even when overview is denied and never selects personal chat skill", async () => {
  let canManage = true, overviewDenied = false, globalReads = 0, skillEnabled = true;
  const confirmations = [], patches = [];
  const { default: AgentAdminPage } = loadModule("../AgentAdminPage.tsx", {
    antd: { Alert: "alert", Button: "button", Card: "card", Descriptions: Object.assign(props => React.createElement("descriptions", props), { Item: "description" }), Drawer: ({ open, children }) => open ? React.createElement("drawer", null, children) : null, Modal: Object.assign(({ open, children }) => open ? React.createElement("modal", null, children) : null, { confirm: options => confirmations.push(options) }), Empty: "empty", Space: "space", Switch: "switch", Tabs: "tabs", Tag: "tag", message: { error() {}, success() {} } },
    "./components/ResizableTable": "table", "./personal-agent/SkillManager": { SkillManager: "skill-manager" },
    "./capability-market/CapabilityMarket": { CapabilityMarket: "capability-market" },
    "./capability-market/GlobalMcpWorkspace": { GlobalMcpWorkspace: "global-mcp-workspace" },
    "./SystemSkillPanel": { SystemSkillPanel: "system-skill-panel" },
    "./personal-agent/types": { errorText: (error, fallback) => error.message || fallback },
    "./api": { api: { get: async path => {
      if (path === "/agent-admin/overview") { if (overviewDenied) { const denial = new Error("管理员权限不足"); denial.response = { status: 403 }; throw denial; } return { data: { runtime: {}, system_skills: [], user_libraries: [] } }; }
      globalReads += 1; return { data: { items: [{ id: "shared-skill", name: "共享技能", category: "办公", enabled: skillEnabled }], can_manage: canManage } };
    }, patch: async (path, body) => { patches.push({ path, body }); skillEnabled = body.enabled; } } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(AgentAdminPage)); });
  const manage = () => React.Children.toArray(renderer.root.findAllByType("card")[0].props.extra.props.children).find(item => item.props.children === "新增或导入");
  assert.equal(renderer.root.findByType("tabs").props.items.slice(0, 3).map(item => item.key).join(","), "global,mcp,market");
  await act(async () => { manage().props.onClick(); });
  assert.equal(renderer.root.findByType("skill-manager").props.scope, "global");
  assert.equal(renderer.root.findByType("skill-manager").props.open, true);
  assert.equal(renderer.root.findByType("skill-manager").props.onSelect, undefined);
  await act(async () => { renderer.root.findByType("switch").props.onChange(false); });
  assert.equal(confirmations.length, 1);
  assert.equal(patches.length, 0, "开关点击不会直接写入");
  assert.equal(renderer.root.findByType("switch").props.checked, true, "未确认时保持旧状态");
  await act(async () => { confirmations[0].onCancel?.(); });
  assert.equal(patches.length, 0, "取消不发 PATCH");
  await act(async () => { await confirmations[0].onOk(); });
  assert.equal(patches[0].path, "/agent/global-skills/shared-skill");
  assert.equal(patches[0].body.enabled, false);
  assert.equal(renderer.root.findByType("switch").props.checked, false);
  canManage = false;
  await act(async () => { renderer.update(React.createElement(AgentAdminPage, { key: "no-write" })); });
  assert.equal(manage(), undefined);
  assert.equal(renderer.root.findAllByType("skill-manager").length, 0);
  const beforeDenied = globalReads; overviewDenied = true; canManage = true;
  await act(async () => { renderer.update(React.createElement(AgentAdminPage, { key: "no-overview" })); });
  assert.equal(globalReads, beforeDenied + 1, "overview 拒绝时仍独立读取全局技能授权");
  assert.ok(manage(), "全局接口授权的委派管理员仍可新增或导入");
  assert.equal(renderer.root.findByType("skill-manager").props.scope, "global");
  assert.equal(renderer.root.findByType("capability-market").props.canManage, true);
  assert.equal(renderer.root.findAllByType("alert").some(item => item.props.title === "智能体设置加载未完成"), false);
  await act(async () => { renderer.unmount(); });
});

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
  await act(async () => renderer.update(React.createElement(ConversationManager, { ...props, presentation: "sidebar", navigation: React.createElement("nav", { "aria-label": "项目导航" }) })));
  const sidebarSections = renderer.root.findAll((item) => item.props.className === "assistant-workspace-navigation" || item.props.className === "assistant-workspace-history");
  assert.deepEqual(sidebarSections.map((item) => item.props.className), ["assistant-workspace-navigation", "assistant-workspace-history"], "真实会话组件把整个导航区放在历史会话前");
  assert.equal(sidebarSections[0].findByType("nav").props["aria-label"], "项目导航");
  assert.equal(sidebarSections[1].findByType("h2").props.children, "历史会话");
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
    "../../agentSkillRouting": { ...loadModule("../agentSkillRouting.ts", {}), DEFAULT_AGENT_SKILL: "qa", encodeAgentSkillMessage: (_skill, value) => value },
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
  assert.equal(table.props.columns[0].render("handling_lawyers"), "经办律师");
  const before = table.props.columns[1].render;
  const after = table.props.columns[2].render;
  assert.equal(before("原律师", { before_read: true }).props.children, "原律师");
  assert.equal(before("原律师", { before_read: false }).props.children, "未读取");
  assert.equal(before(undefined, { before_read: true }).props.children, "未读取");
  assert.equal(before(null, { before_read: true }).props.children, "空值");
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

test("project workspace identity validates explicit scope and isolates empty drafts from conversation drafts", () => {
  const {
    PERSONAL_CONVERSATION_WORKSPACE,
    conversationWorkspaceKey,
    conversationDraftKey,
    requireConversationWorkspace,
    conversationWorkspaceParams,
  } = loadModule("../personal-agent/conversationWorkspace.ts", {});
  const personal = requireConversationWorkspace({ kind: "personal" });
  const firstCase = requireConversationWorkspace({ kind: "case", case_id: 42 });
  const secondCase = requireConversationWorkspace({ kind: "case", case_id: 43 });
  assert.equal(personal, PERSONAL_CONVERSATION_WORKSPACE);
  assert.equal(conversationWorkspaceKey(personal), "personal");
  assert.equal(conversationWorkspaceKey(firstCase), "case:42");
  assert.equal(conversationWorkspaceKey(secondCase), "case:43");
  assert.equal(conversationDraftKey(null, personal), "workspace:personal");
  assert.equal(conversationDraftKey(undefined, firstCase), "workspace:case:42");
  assert.notEqual(conversationDraftKey(null, firstCase), conversationDraftKey(null, secondCase), "未创建会话的案件项目草稿不能串空间");
  assert.equal(conversationDraftKey("CODEX-existing-conversation", firstCase), "CODEX-existing-conversation", "已有会话继续按自身 ID 保存草稿");
  assert.equal(conversationWorkspaceParams(undefined), undefined, "旧 unscoped 调用不伪造个人空间查询");
  assert.deepEqual(JSON.parse(JSON.stringify(conversationWorkspaceParams(personal))), { workspace_kind: "personal" });
  assert.deepEqual(JSON.parse(JSON.stringify(conversationWorkspaceParams(firstCase))), { workspace_kind: "case", workspace_case_id: 42 });
  for (const invalid of [undefined, null, {}, { kind: "personal", case_id: 42 }, { kind: "case" }, { kind: "case", case_id: 0 }, { kind: "case", case_id: -1 }, { kind: "case", case_id: 1.5 }, { kind: "case", case_id: "42" }, { kind: "case", case_id: Number.MAX_SAFE_INTEGER + 1 }, { kind: "unknown" }]) {
    assert.throws(() => requireConversationWorkspace(invalid), /会话响应缺少有效的空间归属/, "非法服务端空间归属必须明确失败，不能当作个人空间");
  }
});

test("personal conversation requests preserve legacy mode and keep background refresh bound to its original space", async () => {
  const requests = [], active = [], background = [];
  const personal = { kind: "personal" }, caseWorkspace = { kind: "case", case_id: 42 };
  const snapshot = (workspace, id) => ({
    workspace,
    workspaces: [{ kind: "personal", title: "个人空间", available: true }, { ...caseWorkspace, title: "测试案件", serial_no: "CODEX-CASE", available: true }],
    items: [{ id, title: id, workspace }],
    state: { conversation_id: id, workspace, messages: [], pending_actions: [], dismissed_action_ids: [] },
  });
  let wrongScope = false, denyCase = false, delayCase = false, resolveCase;
  const respond = (options) => options?.params?.workspace_kind === "case" ? snapshot(caseWorkspace, "CODEX-case") : snapshot(personal, options?.params ? "CODEX-personal" : "CODEX-legacy-global");
  const { usePersonalConversations } = loadModule("../personal-agent/usePersonalConversations.ts", {
    "../api": { api: {
      get: async (path, config) => {
        requests.push({ method: "GET", path, config });
        if (config?.params?.workspace_kind === "case") {
          if (denyCase) throw new Error("案件权限已撤销");
          if (delayCase) return new Promise((resolve) => { resolveCase = resolve; });
        }
        return { data: respond(config) };
      },
      post: async (path, body, config) => {
        requests.push({ method: "POST", path, body, config });
        return { data: wrongScope ? snapshot({ kind: "case", case_id: 43 }, "CODEX-wrong-space") : respond(config) };
      },
      delete: async (path, config) => { requests.push({ method: "DELETE", path, config }); return { data: respond(config) }; },
    } },
  });
  let conversations;
  function Probe() { conversations = usePersonalConversations((state) => active.push(state), (state) => background.push(state)); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => { await conversations.load(); });
  assert.equal(requests.at(-1).config.params, undefined);
  assert.equal(active.at(-1).conversation_id, "CODEX-legacy-global", "旧手机/global active 路径继续由原接口响应决定");
  await act(async () => { await conversations.create(); });
  assert.equal(requests.at(-1).body, undefined, "旧未分空间的新建不添加虚构 workspace");
  await act(async () => { await conversations.openWorkspace(personal); });
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).config.params)), { workspace_kind: "personal" });
  await act(async () => { await conversations.create(); });
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).body)), { workspace: personal });
  await act(async () => { await conversations.openWorkspace(caseWorkspace); });
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).config.params)), { workspace_kind: "case", workspace_case_id: 42 });
  await act(async () => { await conversations.create(); });
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).body)), { workspace: caseWorkspace });
  await act(async () => { await conversations.select("CODEX-case"); });
  assert.equal(requests.at(-1).path, "/personal-agent/conversations/CODEX-case/select");
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).config.params)), { workspace_kind: "case", workspace_case_id: 42 });
  await act(async () => { await conversations.remove("CODEX-case"); });
  assert.equal(requests.at(-1).method, "DELETE");
  assert.deepEqual(JSON.parse(JSON.stringify(requests.at(-1).config.params)), { workspace_kind: "case", workspace_case_id: 42 });
  const applied = active.length;
  wrongScope = true;
  await act(async () => { await assert.rejects(conversations.create(), /空间归属不匹配/); });
  assert.equal(active.length, applied, "不把其他项目响应写入当前会话");
  assert.equal(conversations.busy, false);
  assert.equal(conversations.locked(), false, "归属错误仍释放真实切换锁");
  wrongScope = false;
  denyCase = true;
  await act(async () => { await assert.rejects(conversations.openWorkspace(caseWorkspace), /案件权限已撤销/); });
  assert.equal(conversations.error, "案件权限已撤销");
  assert.equal(conversations.items.length, 0, "失权失败不能留下旧项目历史");
  assert.equal(active.at(-1).conversation_id, null);
  assert.equal(conversations.loading, false);
  denyCase = false;
  delayCase = true;
  const caseView = conversations.capture();
  let refresh;
  await act(async () => { refresh = conversations.refresh(caseView); });
  await act(async () => { await conversations.openWorkspace(personal); });
  await act(async () => { resolveCase({ data: snapshot(caseWorkspace, "CODEX-case-late") }); await refresh; });
  assert.equal(active.at(-1).conversation_id, "CODEX-personal");
  assert.equal(conversations.items[0].id, "CODEX-personal", "旧空间迟到响应不覆盖新空间历史");
  assert.equal(background.length, 0, "列表 refresh 不替换任何会话运行状态");
  await act(async () => renderer.unmount());
});

test("case file selection requires explicit checked documents and preserves failure and material limits", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const cases = [{ id: 42, serial_no: "CODEX-CASE", title: "有权案件" }];
  const documents = [{ id: 201, original_name: "勾选的文件.docx" }, { id: 202, original_name: "未勾选的文件.pdf" }];
  const originalCase = { id: 43, serial_no: "CODEX-ORIGINAL", title: "原引用案件" };
  const originalMaterials = [{ id: 301, name: "原引用文件.docx", case_id: 43 }];
  const requests = [], selected = [], warnings = [], timers = new Map();
  let timerId = 0, closed = 0, fail = false;
  const { CaseMaterialsPicker } = loadModule("../personal-agent/CaseMaterialsPicker.tsx", {
    antd: { Button: component("button"), Empty: component("empty"), Input: component("input"), Modal: ({ children, footer, ...props }) => React.createElement("modal", props, children, footer), Space: component("space"), Spin: component("spin"), Tree: component("tree"), message: { warning: (text) => warnings.push(text) } },
    "../api": { api: { get: async (path) => { requests.push(path); if (fail) throw new Error("案件文件权限已撤销"); return { data: { documents } }; } } },
    "../legal/constants": { buildAgentDocumentTree: (items) => items.map((item) => ({ key: `document:${item.id}`, title: item.original_name })) },
    "./types": { errorText: (error, label) => error.message || label },
    "./useVisibleWorkspaceCases": { useVisibleWorkspaceCases: () => ({ items: cases, loading: false, error: "", retry() {} }) },
  }, { window: { setTimeout: (callback) => { const id = ++timerId; timers.set(id, callback); return id; }, clearTimeout: (id) => timers.delete(id) } });
  const props = {
    mode: "case", selectedCase: originalCase, selectedMaterials: originalMaterials, privateCount: 11,
    onCase: () => assert.fail("PC选择案件文件不能用旧整案关联回调"),
    onMaterials: () => assert.fail("PC选择应原子返回案件与明确文件"),
    onSelection: (item, materials) => selected.push({ item, materials }),
    onClose: () => { closed++; },
  };
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseMaterialsPicker, props)); });
  assert.equal(renderer.root.findByType("modal").props.rootClassName, "assistant-case-materials-picker");
  await act(async () => renderer.root.findAllByType("button").find((item) => item.props.className === "workspace-case-option").props.onClick());
  assert.equal(selected.length, 0, "仅选案件不得自动关联整案或任意文件");
  await act(async () => { for (const [id, callback] of [...timers]) { timers.delete(id); await callback(); } });
  assert.deepEqual(requests, ["/case-spaces/42/context"]);
  const confirm = () => renderer.root.findAllByType("button").find((item) => item.props.type === "primary");
  assert.deepEqual(Array.from(renderer.root.findByType("tree").props.checkedKeys), []);
  assert.equal(confirm().props.disabled, true, "加载出文件也必须保持空选");
  await act(async () => renderer.root.findByType("tree").props.onCheck(["document:201"]));
  assert.equal(confirm().props.disabled, false);
  await act(async () => renderer.root.findByType("modal").props.onCancel());
  assert.equal(selected.length, 0, "取消选案和勾选不能提交部分引用");
  assert.equal(props.selectedCase, originalCase);
  assert.equal(props.selectedMaterials, originalMaterials, "取消后保留原案件和具体文件引用");
  await act(async () => renderer.update(React.createElement(CaseMaterialsPicker, { ...props, mode: null })));
  await act(async () => renderer.update(React.createElement(CaseMaterialsPicker, props)));
  await act(async () => renderer.root.findAllByType("button").find((item) => item.props.className === "workspace-case-option").props.onClick());
  await act(async () => { for (const [id, callback] of [...timers]) { timers.delete(id); await callback(); } });
  assert.deepEqual(Array.from(renderer.root.findByType("tree").props.checkedKeys), [], "重新打开不能把已取消的选择当成原引用");
  await act(async () => renderer.root.findByType("tree").props.onCheck(["document:201"]));
  await act(async () => renderer.root.findByType("tree").props.onCheck(["document:201", "document:202"]));
  assert.match(warnings.at(-1), /最多选择12份材料/);
  assert.deepEqual(Array.from(renderer.root.findByType("tree").props.checkedKeys), ["document:201"], "案件材料加本人上传继续共用12份上限");
  await act(async () => confirm().props.onClick());
  assert.equal(closed, 2);
  assert.deepEqual(JSON.parse(JSON.stringify(selected)), [{ item: cases[0], materials: [{ id: 201, name: documents[0].original_name, case_id: 42 }] }], "只返回勾选文件，不注入同案其他文件");
  fail = true;
  await act(async () => renderer.update(React.createElement(CaseMaterialsPicker, { ...props, mode: "materials", selectedCase: { id: 43, serial_no: "CODEX-DENIED", title: "已失权案件" } })));
  await act(async () => { for (const [id, callback] of [...timers]) { timers.delete(id); await callback(); } });
  assert.equal(requests.at(-1), "/case-spaces/43/context");
  assert.equal(confirm().props.disabled, true);
  assert.ok(renderer.root.findAll((item) => item.props.className === "workspace-picker-error").some((item) => item.props.children === "案件文件权限已撤销"));
  assert.equal(selected.length, 1, "失败不能伪造成功或重复引用上案文件");
  await act(async () => renderer.unmount());
});

test("project drafts and selected file payload stay scoped when a background generation finishes", async () => {
  const personal = { kind: "personal" }, caseA = { kind: "case", case_id: 42 }, caseB = { kind: "case", case_id: 43 };
  const caseRecord = { id: 42, serial_no: "CODEX-CASE-A", title: "测试案件A" };
  const empty = (workspace) => ({ conversation_id: null, workspace, messages: [], pending_actions: [], dismissed_action_ids: [] });
  const key = (workspace) => workspace.kind === "personal" ? "personal" : `case:${workspace.case_id}`;
  const states = new Map(), activeByScope = new Map(), requests = [], generations = [], errors = [];
  const projects = [{ ...personal, title: "个人空间", available: true }, { ...caseA, title: "测试案件A", available: true }, { ...caseB, title: "测试案件B", available: true }];
  const snapshot = (workspace) => ({ workspace, workspaces: projects, items: [...states.values()].filter((state) => key(state.workspace) === key(workspace)).map((state) => ({ id: state.conversation_id, title: state.conversation_id, workspace: state.workspace })), state: activeByScope.get(key(workspace)) || empty(workspace) });
  let finishGeneration;
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning: (text) => errors.push(text), error: (text) => errors.push(text), success() {} } },
    "../api": { api: {
      get: async (path, config) => {
        requests.push({ method: "GET", path, config });
        if (path === "/agent/skills") return { data: { items: [{ id: "general-office", name: "通用办公", available: true }] } };
        if (path === "/personal-agent/status") return { data: { ready: true, commands: [{ id: "cases" }] } };
        assert.equal(path, "/personal-agent/conversations");
        const params = config?.params;
        return { data: snapshot(params?.workspace_kind === "case" ? { kind: "case", case_id: params.workspace_case_id } : personal) };
      },
      post: async (path, body, config) => {
        requests.push({ method: "POST", path, body, config });
        if (path === "/personal-agent/workspaces") return { data: snapshot(body.workspace) };
        assert.equal(path, "/personal-agent/conversations");
        const state = { ...empty(body.workspace), conversation_id: "CODEX-generated-A" };
        states.set(state.conversation_id, state); activeByScope.set(key(body.workspace), state);
        return { data: snapshot(body.workspace) };
      },
    } },
    "./useConversationRuntime": { useConversationRuntime: () => {
      const [state, setState] = React.useState(() => empty(personal));
      return { state, activities: {}, activate: setState, remember() {}, reset() {}, anyRunning: () => false, running: () => false, stopping: () => false, get: (id) => states.get(id),
        generate: (conversation, payload) => { generations.push({ conversation, payload }); return new Promise((resolve) => { finishGeneration = () => resolve(conversation); }); } };
    } },
    "../legal/constants": { aiWordDocumentName: () => "", isAiWordGenerationRequest: () => false, isUsableAiDocumentContent: () => false },
    "../legal/services/agentDocumentConfirmation": { confirmCaseAgentDocument: () => assert.fail("材料引用不能自动保存业务文档") },
  });
  let workspace;
  function Probe() { workspace = usePersonalWorkspace(); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => { await workspace.setProjectMode(true); });
  await act(async () => workspace.setInput("个人空间未发草稿"));
  await act(async () => { await workspace.selectWorkspace(caseA); });
  assert.equal(workspace.input, "", "个人空草稿不能带入案件A");
  await act(async () => workspace.setInput("案件A未发草稿"));
  await act(async () => { await workspace.selectWorkspace(personal); });
  assert.equal(workspace.input, "个人空间未发草稿");
  await act(async () => { await workspace.selectWorkspace(caseA); });
  assert.equal(workspace.input, "案件A未发草稿");
  assert.equal(requests.filter((item) => item.method === "POST" && item.path === "/personal-agent/conversations").length, 0, "登记和切换项目不虚建会话");
  assert.equal(workspace.caseMaterials.length, 0, "打开案件项目不自动引用文件");
  await act(async () => workspace.chooseCaseMaterials(caseRecord, [{ id: 201, name: "明确勾选.docx", case_id: 42 }]));
  let sending;
  await act(async () => { sending = workspace.send(); });
  const creation = requests.find((item) => item.method === "POST" && item.path === "/personal-agent/conversations");
  assert.deepEqual(JSON.parse(JSON.stringify(creation.body)), { workspace: caseA });
  assert.deepEqual(JSON.parse(JSON.stringify(generations[0].payload.workspace)), caseA);
  assert.deepEqual(Array.from(generations[0].payload.document_ids), [201], "真实 send payload 仅包含明确选中文件，不注入同案其他文件");
  assert.equal(generations[0].payload.case_id, 42);
  await act(async () => { await workspace.selectWorkspace(caseB); });
  await act(async () => workspace.setInput("案件B当前草稿"));
  await act(async () => { finishGeneration(); await sending; });
  const refresh = requests.at(-1);
  assert.equal(refresh.path, "/personal-agent/conversations");
  assert.deepEqual(JSON.parse(JSON.stringify(refresh.config.params)), { workspace_kind: "case", workspace_case_id: 42 }, "后台A生成结束只刷新它捕获的A视图");
  assert.equal(workspace.currentWorkspace.case_id, 43);
  assert.equal(workspace.state.conversation_id, null);
  assert.equal(workspace.conversations.length, 0, "A的新会话不能出现在B历史");
  assert.equal(workspace.input, "案件B当前草稿");
  assert.deepEqual(errors, []);
  await act(async () => renderer.unmount());
});

test("homepage pending summary is shown once and direct cancellation retains failures", async () => {
  const component = (name) => ({ children, ...props }) => React.createElement(name, props, children);
  const List = ({ dataSource, renderItem }) => React.createElement("list", null, dataSource.map((item) => React.cloneElement(renderItem(item), { key: item.id })));
  List.Item = ({ actions, children }) => React.createElement("list-item", null, children, actions);
  List.Item.Meta = ({ title, description }) => React.createElement("list-meta", { title, description }, description);
  const dependencies = {
    antd: { ...require("antd"), Alert: component("alert"), Button: component("button"), Input: { TextArea: component("textarea") }, List, Tag: component("tag"), Tooltip: component("tooltip") },
    "./AssistantStart": { __esModule: true, default: component("start"), shortcuts: [] },
    "./ConversationManager": { ConversationManager: ({ navigation, ...props }) => React.createElement("conversation-manager", props, navigation) },
    "./AssistantWorkspaceTools": { AssistantWorkspaceTools: component("workspace-tools") },
    "./ConfirmationHistory": { ConfirmationHistory: component("confirmation-history") },
    "./PersonalAiSpace": { PersonalAiSpace: component("personal-ai-space") },
    "./CaseWorkspaceSelector": { CaseWorkspaceSelector: component("case-workspace-selector") },
    "./ActionConfirmation": { ActionConfirmation: component("action-confirmation") },
  };
  const { default: AssistantPanel } = loadModule("../personal-agent/AssistantPanel.tsx", dependencies);
  const action = { id: "a1", type: "mcp.call", summary: "为2个案件新增期限提醒", status: "pending" };
  const decisions = [];
  const workspace = {
    mcpConnection: { open: false, show() {}, close() {}, intercept() { return false; } },
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

  const requests = [], routes = [], spaces = [], projectModes = [];
  let desktopWorkspace = { ...workspace, status: { ready: true, commands: [{ id: "cases" }] }, selectedCase: { id: 42, serial_no: "CODEX-CASE", title: "可访问案件" }, currentWorkspace: { kind: "personal" },
    workspaceProjects: [{ kind: "personal", title: "个人空间", available: true }, { kind: "case", case_id: 42, serial_no: "CODEX-CASE", title: "可访问案件", available: true }, { kind: "case", case_id: 43, serial_no: "CODEX-DENIED", title: "失权案件", available: false, unavailable_reason: "案件权限已撤销" }],
    selectWorkspace: async (scope) => spaces.push(JSON.parse(JSON.stringify(scope))), setProjectMode: async (enabled) => projectModes.push(enabled), createConversation() {}, selectConversation() {}, deleteConversation() {} };
  const { default: AiChatPage } = loadModule("../personal-agent/AiChatPage.tsx", {
    ...dependencies,
    "./PersonalWorkspaceProvider": { usePersonalWorkspaceContext: () => desktopWorkspace },
    "../api": { api: { get: async path => { requests.push(path); return { data: { items: [] } }; } } },
  });
  const chatProps = { desktop: true, onReturnWorkbench: () => routes.push("dashboard"), focusRequested: false, onFocusHandled() {}, onOpenAgentCenter: () => routes.push("agent-center") };
  await act(async () => { renderer = create(React.createElement(AiChatPage, chatProps)); });
  assert.equal(renderer.root.findByType("aside").props["aria-label"], "AI 工作区导航");
  assert.equal(renderer.root.findAllByType("start").length, 0, "PC不挂载旧快捷卡片组件");
  assert.equal(renderer.root.findAll(item => item.props.className === "assistant-mobile-suggestions").length, 0, "PC不保留隐藏快捷卡片");
  assert.equal(renderer.root.findByType("conversation-manager").props.presentation, "sidebar");
  assert.equal(renderer.root.findByType("conversation-manager").props.onSelect, desktopWorkspace.selectConversation);
  assert.equal(renderer.root.findAllByType("confirmation-history").length, 1, "历史确认入口移入侧栏且不重复");
  const byClass = name => renderer.root.findAllByType("button").find(item => item.props.className === name);
  const selectCaseSpace = () => renderer.root.findAllByType("button").find(item => item.props["aria-label"] === "选择案件空间");
  const projects = () => renderer.root.findAllByType("button").filter(item => item.props.className === "assistant-workspace-project");
  const navigationOrder = renderer.root.findByType("conversation-manager").findAll((item) => item.type === "confirmation-history" || (item.type === "button" && (
    ["assistant-workspace-generated-entry", "assistant-workspace-personal-entry", "assistant-workspace-project"].includes(item.props.className)
    || ["导入技能", "智能体设置", "案件空间"].includes(item.props.children) || item.props["aria-label"] === "选择案件空间"
  ))).map((item) => item.type === "confirmation-history" ? "历史确认记录" : item.props.className === "assistant-workspace-project" ? "案件项目" : item.props["aria-label"] === "选择案件空间" ? "添加案件" : item.props.children);
  assert.deepEqual(navigationOrder, ["AI生成文件夹", "历史确认记录", "导入技能", "智能体设置", "个人空间", "案件空间", "添加案件", "案件项目", "案件项目"], "个人空间、案件标题、添加按钮及全部项目整体移到智能体设置后，不隐藏或拆散项目");
  assert.deepEqual(projectModes, [true], "PC进入真实默认个人项目模式");
  assert.equal(selectCaseSpace().props.disabled, false);
  assert.equal(projects()[0].props.disabled, false);
  assert.equal(projects()[1].props.disabled, true, "保留失权项目但禁止打开，不用假个人空间掩盖失权");
  assert.equal(byClass("assistant-workspace-personal-entry").props["aria-current"], "page");
  assert.equal(byClass("assistant-workspace-case-materials"), undefined, "材料引用不再冒充左栏项目入口");
  await act(async () => { byClass("assistant-workspace-personal-entry").props.onClick(); });
  assert.deepEqual(spaces.at(-1), { kind: "personal" });
  assert.equal(renderer.root.findByType("personal-ai-space").props.open, false, "个人空间切换不打开生成文件弹窗");
  await act(async () => { projects()[0].props.onClick(); });
  assert.deepEqual(spaces.at(-1), { kind: "case", case_id: 42 });
  assert.equal(renderer.root.findByType("personal-ai-space").props.open, false, "案件项目也不借用文件弹窗");
  await act(async () => selectCaseSpace().props.onClick());
  assert.equal(renderer.root.findByType("case-workspace-selector").props.open, true);
  await act(async () => { renderer.root.findByType("case-workspace-selector").props.onClose(); });
  await act(async () => { byClass("assistant-workspace-generated-entry").props.onClick(); });
  assert.equal(byClass("assistant-workspace-generated-entry").props.children, "AI生成文件夹");
  assert.equal(renderer.root.findByType("personal-ai-space").props.open, true, "生成文件夹独立复用原受权文件组件");
  await act(async () => renderer.root.findByType("personal-ai-space").props.onClose());
  await act(async () => { button("智能体设置").props.onClick(); button("返回工作台").props.onClick(); });
  assert.deepEqual(routes, ["agent-center", "dashboard"], "侧栏沿用上层授权的真实导航回调");
  desktopWorkspace = { ...desktopWorkspace, status: { ready: true, commands: [] } };
  await act(async () => { renderer.update(React.createElement(AiChatPage, { ...chatProps, onOpenAgentCenter: undefined })); });
  assert.equal(selectCaseSpace().props.disabled, true, "案件入口使用真实命令权限，而非只改标签");
  assert.ok(projects().every(item => item.props.disabled), "没有命令权限时不能借项目书签绕过");
  assert.equal(byClass("assistant-workspace-case-materials"), undefined, "无案件权限不展示既有选中案件材料入口");
  assert.equal(button("智能体设置"), undefined, "上层未授导航回调时不制造设置入口，稳定route和权限链不因更名改变");
  desktopWorkspace = { ...desktopWorkspace, status: { ready: true, commands: [{ id: "cases" }] }, loadError: "工作区读取失败" };
  await act(async () => { renderer.update(React.createElement(AiChatPage, chatProps)); });
  assert.equal(selectCaseSpace().props.disabled, true);
  assert.ok(projects().every(item => item.props.disabled), "工作区读取失败不得借新项目入口继续操作");
  desktopWorkspace = { ...desktopWorkspace, loadError: "" };
  await act(async () => { renderer.update(React.createElement(AiChatPage, { ...chatProps, desktop: false })); });
  assert.equal(renderer.root.findAllByType("aside").length, 0, "手机不挂载PC常驻侧栏");
  assert.equal(renderer.root.findAll(item => item.props.className === "assistant-bar-actions").length, 1);
  assert.equal(renderer.root.findAllByType("confirmation-history").length, 1);
  assert.equal(renderer.root.findAllByType("conversation-manager").length, 1);
  assert.equal(renderer.root.findAllByType("start").length, 1, "手机保留原空态入口");
  assert.deepEqual(projectModes, [true, false], "离开PC项目模式后恢复旧unscoped路径，不强改手机global active");
  assert.deepEqual(requests, [], "独立AI页面不再请求dashboard suggestions来生成PC卡片");
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

test("chat MCP uses server scope defaults and preserves personal edits without settings permissions", async () => {
  const base = "/capability-market/personal-mcp";
  const requests = [];
  let defaultScope = "global", managementAllowed = true, hook;
  const metadata = (value, canManage = true) => ({ id: "CODEX-SCOPED", name: "CODEX连接", scope: value, revision: `revision-${value}`, status: "configured", can_manage: canManage });
  const state = value => ({ ...metadata(value, managementAllowed), servers: [], capabilities: { discovery: true, tool_call: true }, configuration: { "mcp.json": { mcpServers: { default: { url: "https://example.com/mcp", type: "streamableHttp", headers: { Authorization: "" } } } } }, secret_fields: [{ configured: true, path: ["mcp.json", "mcpServers", "default", "headers", "Authorization"], template: "" }] });
  const { usePersonalMcpConnection } = loadModule("../personal-agent/usePersonalMcpConnection.ts", {
    "../api": { api: {
      get: async (path, options) => {
        requests.push({ method: "GET", path, params: options?.params });
        return { data: path === base ? { items: [state("personal")], available_connections: [metadata("personal"), metadata("global", defaultScope === "global")], default_scope: defaultScope, can_manage_global: defaultScope === "global" } : state(options.params.scope) };
      },
      post: async (path, body, options) => {
        requests.push({ method: "POST", path, body, params: options?.params });
        return { data: path === base ? state(defaultScope) : { ok: true, configuration: { ...state(options.params.scope), status: "verified" } } };
      },
      put: async (path, body, options) => { requests.push({ method: "PUT", path, body, params: options.params }); return { data: state(options.params.scope) }; },
      delete: async (path, options) => { requests.push({ method: "DELETE", path, params: options.params }); return { data: { id: "CODEX-SCOPED", scope: options.params.scope, deleted: true } }; },
    } },
  }, { URL, URLSearchParams, structuredClone });
  function Probe() { hook = usePersonalMcpConnection("CODEX-CONVERSATION"); return null; }
  let renderer;
  await act(async () => { renderer = create(React.createElement(Probe)); });
  await act(async () => hook.show());
  assert.equal(hook.scope, "global");
  assert.equal(hook.items.length, 2);
  assert.equal(Object.hasOwn(hook.items[0], "configuration"), false);
  const fill = () => hook.update({ ...hook.draft, name: "CODEX新连接", server_url: "https://example.com/mcp" });
  await act(async () => fill());
  await act(async () => hook.saveAndConnect());
  assert.equal(hook.connection.scope, "global");
  assert.equal(Object.hasOwn(requests.find(item => item.method === "POST" && item.path === base).body, "scope"), false);
  await act(async () => hook.edit(hook.items.find(item => item.scope === "personal")));
  assert.equal(hook.scope, "personal", "管理员编辑旧个人连接仍保留个人范围");
  await act(async () => hook.saveAndConnect());
  const put = requests.find(item => item.method === "PUT");
  assert.equal(put.params.scope, "personal");
  assert.equal(Object.hasOwn(put.body, "scope"), false);
  assert.deepEqual(JSON.parse(JSON.stringify(put.body.keep_credentials)), [["mcp.json", "mcpServers", "default", "headers", "Authorization"]]);
  assert.equal(put.body.configuration["mcp.json"].mcpServers.default.headers.Authorization, "");
  assert.equal(requests.filter(item => item.path?.endsWith("/verify")).at(-1).params.scope, "personal");
  await act(async () => hook.remove(hook.items.find(item => item.scope === "personal")));
  assert.equal(hook.items.length, 1, "相同ID的其他scope不受删除影响");
  const removed = requests.find(item => item.method === "DELETE");
  assert.equal(removed.params.scope, "personal");
  assert.equal(removed.params.revision, "revision-personal");
  defaultScope = "personal";
  await act(async () => hook.close());
  await act(async () => hook.show());
  assert.equal(hook.scope, "personal");
  const readOnlyGlobal = hook.items.find(item => item.scope === "global");
  const before = requests.length;
  await act(async () => { await hook.edit(readOnlyGlobal); await hook.remove(readOnlyGlobal); await hook.retryTest(readOnlyGlobal); });
  assert.equal(requests.length, before, "普通用户不读取全局配置或发起管理请求");
  await act(async () => fill());
  await act(async () => hook.saveAndConnect());
  assert.equal(hook.connection.scope, "personal", "无设置菜单权限的普通用户仍能创建个人连接");
  await act(async () => hook.edit(hook.items.find(item => item.scope === "personal")));
  await act(async () => hook.saveAndConnect());
  assert.equal(hook.connection.scope, "personal");
  await act(async () => hook.remove(hook.items.find(item => item.scope === "personal")));
  assert.equal(hook.items.every(item => item.scope === "global"), true);
  managementAllowed = false;
  await act(async () => hook.refresh());
  await act(async () => hook.edit(hook.items.find(item => item.scope === "personal")));
  assert.equal(hook.editing, false, "管理响应明确拒绝时不能由前端合成授权");
  assert.equal(hook.draft.server_url, "", "无管理权的响应不能填入配置表单");
  assert.ok(hook.error);
  assert.equal(requests.some(item => item.path.includes("/auth/me") || item.path.includes("settings")), false);
  await act(async () => renderer.unmount());
});

test("chat MCP scope labels and global management controls use per-connection permissions", async () => {
  const component = name => ({ children, ...props }) => React.createElement(name, props, children);
  const Form = component("form"); Form.Item = component("form-item");
  const Input = component("input"); Input.Password = component("password");
  const { PersonalMcpConnectionCard } = loadModule("../personal-agent/PersonalMcpConnectionCard.tsx", { antd: { Alert: component("alert"), Button: component("button"), Form, Input, Popconfirm: component("popconfirm"), Select: component("select"), Spin: component("spin"), Tag: component("tag"), Tooltip: component("tooltip") } });
  const mcp = { draft: { name: "", server_url: "", transport: "streamable_http", auth_type: "none", credential: "", api_key_header: "X-API-Key" }, scope: "global", defaultScope: "global", items: [{ id: "shared", name: "全局服务", scope: "global", status: "verified", can_manage: false }], editing: false, busy: false, listing: false, error: "", listError: "", connection: null, credentialSaved: false, close() {}, update() {}, newConnection() {}, refresh() {}, importConfig() {}, saveAndConnect() {} };
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalMcpConnectionCard, { connection: mcp })); });
  const buttons = () => renderer.root.findAllByType("button");
  assert.ok(buttons().some(item => item.props.children === "确认全局保存并连接"));
  assert.equal(buttons().some(item => item.props["aria-label"] === "修改配置：全局服务"), false);
  assert.equal(buttons().some(item => item.props["aria-label"] === "删除连接：全局服务"), false);
  assert.equal(buttons().some(item => item.props["aria-label"] === "检测连接：全局服务"), false);
  assert.ok(renderer.root.findAllByType("tag").some(item => item.props.children === "全局共享"));
  assert.ok(renderer.root.findAllByType("form-item").some(item => item.props.label === "粘贴 MCP 配置"), "个人入口仍提供配置导入");
  await act(async () => renderer.update(React.createElement(PersonalMcpConnectionCard, { connection: { ...mcp, editing: true }, allowNewConnection: false, allowConfigImport: false })));
  assert.equal(renderer.root.findAllByType("form-item").some(item => item.props.label === "粘贴 MCP 配置"), false, "全局编辑入口不提供清除编辑范围的配置导入");
  assert.equal(buttons().some(item => item.props.children === "取消修改"), false, "全局编辑入口不转入新建连接");
  assert.ok(buttons().some(item => item.props.children === "确认更新并连接"));
  await act(async () => renderer.update(React.createElement(PersonalMcpConnectionCard, { connection: { ...mcp, scope: "personal", defaultScope: "global", editing: true, items: mcp.items.map(item => ({ ...item, can_manage: true })) } })));
  assert.ok(renderer.root.findAllByType("span").some(item => item.props.children === "正在修改既有个人连接，保存后仍为个人专用"));
  assert.ok(buttons().some(item => item.props["aria-label"] === "修改配置：全局服务"));
  assert.ok(buttons().some(item => item.props.children === "确认更新并连接"));
  await act(async () => renderer.unmount());
});

test("global MCP drawer blocks a writable form when delegated admin cannot load global configuration", async () => {
  const shared = { id: "shared", name: "全局服务", scope: "global", status: "verified", can_manage: true };
  const model = {
    open: false, items: [shared], defaultScope: "personal", scope: "personal", editing: false,
    connection: null, busy: false, listing: false, error: "", listError: "",
    refresh() {}, show() { model.open = true; }, close() { model.open = false; },
    edit() { model.error = "全局配置读取失败"; model.editing = false; model.connection = null; },
    retryTest() {}, remove() {}, newConnection() {},
  };
  const { GlobalMcpWorkspace } = loadModule("../capability-market/GlobalMcpWorkspace.tsx", {
    antd: { Alert: "alert", Button: "button", Drawer: ({ open, children }) => open ? React.createElement("drawer", null, children) : null, Empty: "empty", Modal: { confirm() {} }, Tag: "tag", Tooltip: "tooltip" },
    "./ConnectorConfigPanel": { connectionLabel: () => "已验证" },
    "../personal-agent/PersonalMcpConnectionCard": { PersonalMcpConnectionCard: "editable-card" },
    "../personal-agent/usePersonalMcpConnection": { usePersonalMcpConnection: () => model },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(GlobalMcpWorkspace, { active: true, canManage: true })); });
  const button = label => renderer.root.findAllByType("button").find(item => item.props["aria-label"] === label || item.props.children === label);
  assert.equal(button("新增全局 MCP"), undefined, "委派管理员不能从服务端个人默认范围新建全局连接");
  await act(async () => { button("修改配置：全局服务").props.onClick(); });
  assert.equal(renderer.root.findAllByType("editable-card").length, 0, "GET 失败后不显示可保存表单");
  assert.ok(renderer.root.findAllByType("drawer").length);
  assert.ok(renderer.root.findAllByType("alert").some(item => item.props.title === "全局配置读取失败"));
  assert.ok(button("重试"));
  model.edit = () => { model.error = ""; model.editing = true; model.scope = "global"; };
  await act(async () => { button("重试").props.onClick(); renderer.update(React.createElement(GlobalMcpWorkspace, { active: true, canManage: true })); });
  assert.equal(renderer.root.findByType("editable-card").props.connection.scope, "global");
  assert.equal(renderer.root.findByType("editable-card").props.allowConfigImport, false);
  assert.equal(renderer.root.findByType("editable-card").props.allowNewConnection, false);
  await act(async () => { renderer.unmount(); });

  model.open = false; model.editing = false; model.scope = "global"; model.defaultScope = "global";
  await act(async () => { renderer = create(React.createElement(GlobalMcpWorkspace, { active: true, canManage: true })); });
  await act(async () => { button("新增全局 MCP").props.onClick(); });
  assert.ok(renderer.root.findByType("editable-card"), "实际管理员仍可新建全局连接");
  await act(async () => { renderer.unmount(); });
});

test("personal MCP intent preserves ordinary URLs and API JSON while isolating credentials", () => {
  const mcp = loadModule("../personal-agent/personalMcpConfig.ts", {}, { URL, URLSearchParams });
  for (const text of ["https://example.com/article", "分析 https://example.com/article", "https://example.com/search?keyword=合同", "分析 https://example.com/search?monkey=合同", "https://example.com/search?tokenizer=plain", JSON.stringify({ headers: { "Content-Type": "application/json" }, body: { q: "普通API" } })]) {
    assert.equal(mcp.isMcpConnectionInput(text), false);
    assert.equal(mcp.hasConnectionCredential(text), false);
  }
  for (const text of ["连接自己的MCP", "connect my MCP", "https://example.com/mcp", JSON.stringify({ mcpServers: { mine: { url: "https://example.com/service" } } })]) assert.equal(mcp.isMcpConnectionInput(text), true);
  for (const verb of ["创建", "新建", "链接", "接通", "导入"]) {
    assert.equal(mcp.isMcpConnectionInput(`${verb}MCP`), true);
    assert.equal(mcp.isMcpConnectionInput(`MCP${verb}`), true);
  }
  assert.equal(mcp.isMcpConnectionInput("创建网页链接 https://example.com/article"), false);
  assert.equal(mcp.isMcpConnectionInput("https://example.com/service", true), true);
  for (const name of ["key", "credential", "credentials", "signature", "accessKey", "apiKey", "api_key", "x-api-key", "client_secret", "private_key", "clientKeyId", "passwd", "sig", "auth", "x-amz-credential", "x_amz_security_token", "token", "access_token", "%6bey"]) {
    const url = `https://example.com/mcp?${name}=CODEX-NONSECRET`;
    assert.equal(mcp.hasConnectionCredential(url), true);
    assert.throws(() => mcp.parsePersonalMcpConfig(url));
  }
  assert.equal(mcp.hasConnectionCredential("https://example.com/search?key=CODEX-NONSECRET"), true);
  assert.equal(mcp.hasConnectionCredential("https://invalid:port/search?keyword=合同"), false);
  assert.equal(mcp.hasConnectionCredential("https://invalid:port/search?key=CODEX-NONSECRET"), true);
  const draft = mcp.parsePersonalMcpConfig(JSON.stringify({ mcpServers: { mine: { url: "https://example.com/mcp", type: "streamableHttp", headers: { Authorization: "Bearer CODEX-NONSECRET" } } } }));
  assert.equal(draft.credential, "CODEX-NONSECRET");
  assert.equal(mcp.validatePersonalMcpDraft(draft), "");
  assert.equal(mcp.personalMcpConfiguration({ ...draft, credential: "" })["mcp.json"].mcpServers.mine.headers.Authorization, "");
});

test("personal remote MCP confirmation uses generic preview and decision without local tool request APIs", async () => {
  const component = name => ({ children, ...props }) => React.createElement(name, props, children);
  const requests = [], decisions = [];
  const { ActionConfirmation } = loadModule("../personal-agent/ActionConfirmation.tsx", {
    antd: { Alert: component("alert"), Button: component("button"), Modal: ({ footer, children, ...props }) => React.createElement("modal", props, children, footer), Space: component("space"), Spin: component("spin"), Tag: component("tag"), message: { error() {} } },
    "../api": { api: { get: async path => { requests.push(path); throw new Error("禁止读取本地工具请求"); } } },
    "../AgentOperationPreview": { AgentOperationPreview: component("preview"), agentOperationError: error => error.message, agentOperationMessage: String, hasAgentOperationPreview: () => true },
  });
  const action = { id: "CODEX-REMOTE", type: "personal_mcp.call", status: "pending", summary: "调用个人 MCP", preview: { operation_name: "外部查询", method: "tools/call", path: "remote-tool", params: { arguments: { query: "公开资料" } }, requires_confirmation: true } };
  let renderer;
  const props = { action, deciding: false, onDecide: async (item, decision) => { decisions.push([item.id, decision]); return true; }, onClose() {} };
  await act(async () => { renderer = create(React.createElement(ActionConfirmation, props)); });
  const confirm = () => renderer.root.findAllByType("button").find(item => item.props.children === "确认并执行");
  assert.equal(confirm().props.disabled, false);
  await act(async () => confirm().props.onClick());
  assert.deepEqual(decisions, [["CODEX-REMOTE", "approved"]]);
  assert.deepEqual(requests, []);
  await act(async () => renderer.update(React.createElement(ActionConfirmation, { ...props, action: { ...action, preview: undefined } })));
  assert.equal(confirm().props.disabled, true);
  await act(async () => renderer.unmount());
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
      items: [], projects: [], busy: false, loading: false, error: "", capture: () => ({ revision: 0 }), locked: () => false, load: async () => activate(initial), refresh: async () => {},
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
  const api = {
      get: async (path, options) => {
        calls.push(["get", path]);
        if (path === "/personal-agent/conversations") {
          assert.equal(options.timeout, 15000);
          return await new Promise((resolve) => { resolveRead = resolve; });
        }
        return { data: path === "/agent/skills" ? { items: [] } : { ready: true } };
      },
      post: async (path) => { calls.push(["post", path]); throw failure; },
  };
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("失败不能伪造成功") } },
    "../api": { api },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace: (next) => { current = next; } }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], projects: [], busy: false, loading: false, error: "", capture: () => ({ revision: 0 }), locked: () => false, load: async () => {}, refresh: async () => {},
      read: async (_view, timeout) => (await api.get("/personal-agent/conversations", { timeout })).data,
    }) },
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
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], projects: [], busy: false, loading: false, error: "", capture: () => ({ revision: 0 }), locked: () => false, load: async () => {}, refresh: async () => {}, select: async (id) => { calls.push(["select", id]); return current; } }) },
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
  const api = {
    get: async (path) => { if (path === "/personal-agent/conversations") throw new Error("只读状态读取超时"); return { data: path === "/agent/skills" ? { items: [] } : { ready: true } }; },
    post: async () => { posts++; throw new Error("网络断开，执行结果未知"); },
  };
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("未知结果不能报告成功") } },
    "../api": { api },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace() {} }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], projects: [], busy: false, loading: false, error: "", capture: () => ({ revision: 0 }), locked: () => false, load: async () => {}, refresh: async () => {}, read: async (_view, timeout) => (await api.get("/personal-agent/conversations", { timeout })).data }) },
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
  const api = {
      get: async (path) => { if (path === "/personal-agent/conversations") throw new Error("只读回查失败"); return { data: path === "/agent/skills" ? { items: [] } : { ready: true } }; },
      post: async (path, body) => {
        posts.push([path, body]);
        if (path.endsWith("/actions/dismiss")) return { data: { state: { ...current, dismissed_action_ids: body.action_ids } } };
        throw new Error(`网络未知：${path}`);
      },
  };
  const { usePersonalWorkspace } = loadModule("../personal-agent/usePersonalWorkspace.ts", {
    antd: { ...require("antd"), message: { warning() {}, error() {}, success: () => assert.fail("未知结果不能报告成功") } },
    "../api": { api },
    "./useConversationRuntime": { useConversationRuntime: () => ({ state: current, activities: {}, anyRunning: () => false, running: () => false, reset() {}, get: () => current, replace: (next) => { current = next; } }) },
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], projects: [], busy: false, loading: false, error: "", capture: () => ({ revision: 0 }), locked: () => false, load: async () => {}, refresh: async () => {}, read: async (_view, timeout) => (await api.get("/personal-agent/conversations", { timeout })).data, select: async () => { if (failSelect) throw new Error("原会话读取失败"); return current; } }) },
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
    "./usePersonalConversations": { usePersonalConversations: () => ({ items: [], projects: [], busy: false, loading: false, error: "", capture: () => ({ revision: 0 }), locked: () => false, load: async () => {}, refresh: async () => {} }) },
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
  const chosenSkills = [];
  const workspace = { status: { commands: [] }, loading: false, stopping: false, uploading: false, decisionId: "", conversationBusy: false, skills: [], skillId: "general-office", setSkillId: value => chosenSkills.push(value), selectedCase: null, materials: [], caseMaterials: [] };
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
  assert.equal(renderer.root.findByType("case-picker").props.onSelection, undefined, "原手机材料流程保持unscoped旧回调");
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
  assert.equal(renderer.root.findByType("select").props.allowClear, true);
  await act(async () => { renderer.root.findByType("select").props.onChange(undefined); });
  assert.deepEqual(chosenSkills, [""], "实际Select清空传空ID而不是undefined/default");
  assert.equal(renderer.root.findAllByType("button").some((item) => item.props.className === "personal-ai-space-mobile-entry"), false, "桌面工具组不重复挂入口");
  const selections = [];
  const desktop = { ...workspace, status: { commands: [{ id: "cases" }] }, chooseCaseMaterials: (item, files) => selections.push({ item, files }) };
  await act(async () => renderer.update(React.createElement(AssistantWorkspaceTools, { workspace: desktop, desktopWorkspace: true, onOpenPersonalAiSpace: () => { opened++; } })));
  const caseFiles = () => renderer.root.findAllByType("button").find((item) => item.props.className === "assistant-case-select");
  assert.equal(caseFiles().props.children, "案件文件");
  assert.equal(renderer.root.findByType("case-picker").props.onSelection, desktop.chooseCaseMaterials, "PC用独立原子回调提交案件与具体文件");
  await act(async () => caseFiles().props.onClick());
  assert.equal(renderer.root.findByType("case-picker").props.mode, "case");
  const item = { id: 42, serial_no: "CODEX-CASE", title: "测试案件" };
  const files = [{ id: 201, name: "明确选择.docx", case_id: 42 }];
  await act(async () => renderer.root.findByType("case-picker").props.onSelection(item, files));
  assert.deepEqual(selections, [{ item, files }]);
  await act(async () => renderer.root.findByType("case-picker").props.onClose());
  await act(async () => renderer.update(React.createElement(AssistantWorkspaceTools, { workspace: { ...desktop, loadError: "工作区读取失败" }, desktopWorkspace: true, onOpenPersonalAiSpace() {} })));
  assert.equal(caseFiles().props.disabled, true);
  await act(async () => caseFiles().props.onClick());
  assert.equal(renderer.root.findByType("case-picker").props.mode, null, "读取失败不能打开材料选择器");
  await act(async () => renderer.update(React.createElement(AssistantWorkspaceTools, { workspace: { ...desktop, status: { commands: [] } }, desktopWorkspace: true, onOpenPersonalAiSpace() {} })));
  assert.equal(caseFiles(), undefined, "原cases命令权限继续限制输入区案件文件入口");
  await act(async () => renderer.unmount());
});

test("personal AI space shows known Chinese source labels and preserves unknown source values", () => {
  const { PersonalAiSpaceFiles } = loadModule("../personal-agent/PersonalAiSpaceFiles.tsx", { antd: { Button: () => null, Empty: () => null, Tag: () => null, Tooltip: () => null } });
  const text = (node) => typeof node === "string" || typeof node === "number" ? String(node) : React.Children.toArray(node?.props?.children).map(text).join("");
  for (const [source, label] of [["mcp_export", "案件导出"], ["mcp_generated", "智能体生成文件"], ["case_draft", "案件AI草稿"], ["case_upload", "案件AI上传"], ["case_migration", "案件AI迁移"], ["assistant_message", "助手回答"], ["personal_identity", "个人身份文件"], ["personal_edit", "在线编辑新版本"], ["future_source", "future_source"], ["toString", "toString"]]) {
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

test("personal AI file deletion requires confirmation, sends one exact hash and hides logical deletes", async () => {
  const base = { name: "个人文稿.txt", status: "available", size: 12, sha256: "d".repeat(64), created_at: "2026-10-14T00:00:00Z", source_kind: "personal_edit", conversation_id: null, source_request_id: null, error: null, can_delete: true };
  const owned = { ...base, id: "d".repeat(32), download_url: "/owned/download" };
  const previous = { ...base, id: "e".repeat(32), name: "保留旧版本.txt", download_url: "/previous/download" };
  const denied = [{ ...base, id: "f".repeat(32), name: "案件原附件.txt", case_id: 42, can_delete: false }, { ...base, id: "1".repeat(32), name: "IDENTITY.md", source_kind: "personal_identity", can_delete: false }];
  let items = [owned, previous, ...denied], finishDelete;
  const deletions = [], notices = [];
  const { PersonalAiSpace } = loadModule("../personal-agent/PersonalAiSpace.tsx", {
    antd: { Alert: "alert", Button: "button", Drawer: "drawer", Empty: "empty", Pagination: "pagination", Spin: "spin", Tag: "tag", Tooltip: "tooltip",
      Modal: ({ open, children, ...props }) => open ? React.createElement("modal", props, children) : null, message: { success: value => notices.push(value) } },
    "./types": { errorText: (error, fallback) => error.message || fallback },
    "./PersonalAiDocumentEditor": { PersonalAiDocumentEditor: "document-editor" },
    "../components/common/AttachmentContent": { AttachmentPreviewContent: () => null },
    "../api": { api: {
      get: async path => {
        if (path === "/personal-agent/ai-space") return { data: { configured: true, owner_name: "本人" } };
        if (path === "/personal-agent/ai-space/files") return { data: { items, total: items.length, page: 1, page_size: 20 } };
        if (path === `/personal-agent/ai-space/files/${owned.id}/content`) return { data: { id: owned.id, name: owned.name, content: "原版本正文" } };
        throw new Error(`未预期请求：${path}`);
      },
      delete: (path, options) => { deletions.push({ path, options }); return new Promise((resolve, reject) => { finishDelete = { resolve, reject }; }); },
    } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalAiSpace, { open: true, revision: 0, busy: false, onClose() {}, onOpenConversation: async () => {}, label: "AI生成文件夹" })); });
  const remove = name => renderer.root.findAllByType("button").find(item => item.props["aria-label"] === `删除生成文件：${name}`);
  assert.ok(remove(owned.name));
  for (const file of denied) assert.equal(remove(file.name), undefined, "服务端未授权的案件或身份文件没有删除入口");
  const row = renderer.root.findAllByType("li").find(item => item.findByType("strong").props.children === owned.name);
  await act(async () => { row.findAllByType("button").find(item => item.props.children === "在线编辑").props.onClick(); });
  assert.equal(renderer.root.findByType("document-editor").props.document.id, owned.id);
  const newVersion = { ...base, id: "2".repeat(32), name: "回读新版本.txt", supersedes: owned.id, download_url: "/new/download" };
  items = [newVersion, ...items];
  await act(async () => { renderer.root.findByType("document-editor").props.onVersionCreated(newVersion); });
  assert.equal(renderer.root.findByType("document-editor").props.document.id, owned.id, "仅创建新版本还不能切换未回读的编辑目标");
  assert.ok(renderer.root.findAllByType("tag").some(item => item.props.children === "本次保存的新版本"));
  await act(async () => { renderer.root.findByType("document-editor").props.onSaved(newVersion, { id: newVersion.id, name: newVersion.name, content: "服务端已回读正文" }); });
  assert.equal(renderer.root.findByType("document-editor").props.document.id, newVersion.id);
  assert.equal(renderer.root.findByType("document-editor").props.document.content, "服务端已回读正文");
  await act(async () => { renderer.root.findByType("document-editor").props.onClose(); });
  await act(async () => { remove(owned.name).props.onClick(); });
  assert.equal(deletions.length, 0, "打开确认不发送删除");
  await act(async () => { renderer.root.findByType("modal").props.onCancel(); });
  assert.equal(deletions.length, 0, "取消确认零请求");
  await act(async () => { remove(owned.name).props.onClick(); });
  await act(async () => {
    const modal = renderer.root.findByType("modal");
    modal.props.onOk(); modal.props.onOk();
  });
  assert.equal(deletions.length, 1, "同一次确认连点只发送一次");
  assert.equal(deletions[0].path, `/personal-agent/ai-space/files/${owned.id}`);
  assert.deepEqual(JSON.parse(JSON.stringify(deletions[0].options)), { data: { expected_sha256: owned.sha256 }, headers: { "X-OA-Agent-Confirmation": "frontend" } });
  assert.equal(remove(owned.name).props.disabled, true);
  items = items.filter(file => file.id !== owned.id);
  await act(async () => { finishDelete.resolve({ data: { id: owned.id, status: "deleted", blob_status: "retained" } }); });
  assert.equal(renderer.root.findAllByType("modal").length, 0);
  assert.equal(remove(owned.name), undefined);
  assert.ok(remove(previous.name), "仅删除被确认 ID，不级联旧版本");
  assert.equal(notices.length, 1);
  await act(async () => { renderer.unmount(); });
});

test("personal DOCX enters Office before content extraction and guards folder actions while Office is busy", async () => {
  const file = { id: "a".repeat(32), name: "含表格原文.docx", case_id: null, owner_user_id: 7, owner_name: "本人", status: "available", size: 20, sha256: "b".repeat(64), created_at: "2026-10-14T00:00:00Z", source_kind: "personal_edit", can_delete: true, download_url: "/original/download" };
  const saved = { ...file, id: "c".repeat(32), name: "完整新版本.docx", supersedes: file.id, download_url: "/new/download" };
  const blob = new Blob(["opaque complete DOCX bytes"]);
  const reads = [];
  let items = [file], closed = 0, deleted = 0;
  const { PersonalAiSpace } = loadModule("../personal-agent/PersonalAiSpace.tsx", {
    antd: { Alert: "alert", Button: "button", Drawer: "drawer", Empty: "empty", Pagination: "pagination", Spin: "spin", Tag: "tag", Tooltip: "tooltip",
      Modal: ({ open, children, ...props }) => open ? React.createElement("modal", props, children) : null, message: { success() {} } },
    "./types": { errorText: (error, fallback) => error.message || fallback },
    "./PersonalAiDocumentEditor": { PersonalAiDocumentEditor: "document-editor" },
    "./PersonalAiOfficeEditor": { PersonalAiOfficeEditor: "office-editor" },
    "../components/common/AttachmentContent": { AttachmentPreviewContent: "attachment-preview" },
    "../api": { api: {
      get: async (path, options) => {
        reads.push({ path, options });
        if (path === "/personal-agent/ai-space") return { data: { configured: true, owner_name: "本人" } };
        if (path === "/personal-agent/ai-space/files") return { data: { items, total: items.length, page: 1, page_size: 20 } };
        throw new Error("个人完整 Word 不得读取受限 content");
      },
      delete: async () => { deleted++; throw new Error("忙态不能删除"); },
    } },
  });
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalAiSpace, { open: true, revision: 0, busy: false, onClose: () => { closed++; }, onOpenConversation: async () => {} })); });
  await act(async () => { renderer.root.findAllByType("button").find(item => item.props.children === "在线编辑").props.onClick(); });
  const office = renderer.root.findByType("office-editor");
  assert.equal(office.props.file.id, file.id);
  assert.equal(renderer.root.findAllByType("document-editor").length, 0);
  assert.equal(reads.length, 2, "DOCX进入Office不发起旧/content正文解析");
  await act(async () => { office.props.onBusy(true); });
  const remove = () => renderer.root.findAllByType("button").find(item => item.props["aria-label"] === `删除生成文件：${file.name}`);
  assert.equal(remove().props.disabled, true);
  await act(async () => { remove().props.onClick(); renderer.root.findByType("drawer").props.onClose(); office.props.onClose(); });
  assert.equal(deleted, 0);
  assert.equal(closed, 0);
  assert.equal(renderer.root.findAllByType("office-editor").length, 1);
  assert.equal(renderer.root.findAllByType("modal").length, 0, "Office忙态即使旧回调被触发也不打开删除确认");
  items = [saved, file];
  await act(async () => { office.props.onVersionCreated(saved); });
  assert.equal(reads.at(-1).options.params.page, 1);
  assert.ok(renderer.root.findAllByType("tag").some(item => item.props.children === "本次保存的新版本"));
  await act(async () => { office.props.onSaved(saved, blob); office.props.onBusy(false); });
  assert.equal(renderer.root.findAllByType("office-editor").length, 0);
  assert.equal(renderer.root.findByType("attachment-preview").props.preview.kind, "docx");
  assert.equal(renderer.root.findByType("attachment-preview").props.preview.name, saved.name);
  assert.equal(renderer.root.findByType("attachment-preview").props.preview.blob, blob);
  assert.equal(reads.some(item => item.path.endsWith("/content")), false);
  await act(async () => { renderer.root.findByType("modal").props.onCancel(); remove().props.onClick(); });
  assert.ok(renderer.root.findAllByType("p").some(item => item.props.children === "钉钉编辑副本不在本次删除范围。"));
  await act(async () => { renderer.root.findByType("modal").props.onCancel(); });
  assert.equal(deleted, 0, "OA删除确认取消不操作OA或远端钉钉副本");
  await act(async () => { renderer.unmount(); });
});

test("Office save verifies the new ID metadata and complete bytes and retries failed readback with GET only", async () => {
  const { createHash, webcrypto } = require("node:crypto");
  const blob = new Blob(["complete DOCX bytes including opaque table content"]);
  const bytes = Buffer.from(await blob.arrayBuffer());
  const file = { id: "d".repeat(32), name: "原Word.docx", owner_user_id: 7, case_id: null, sha256: "e".repeat(64) };
  const saved = { ...file, id: "f".repeat(32), name: "回存Word.docx", status: "available", size: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex"), supersedes: file.id, can_delete: true, download_url: "/new/download" };
  const requests = [], created = [], verified = [], notices = [], busy = [];
  let finishOpen, finishOperation, failMetadata = true, corrupt = false, closed = 0;
  const popup = { location: { replace: value => { popup.url = value; } }, close: () => { popup.closed = true; } };
  const { PersonalAiOfficeEditor } = loadModule("../personal-agent/PersonalAiOfficeEditor.tsx", {
    antd: { Alert: "alert", Button: "button", Modal: ({ footer, children, ...props }) => React.createElement("modal", props, children, footer), message: { success: value => notices.push(value) } },
    "./types": { errorText: (error, fallback) => error.message || fallback },
    "../api": { api: {
      post: (path, body, options) => {
        requests.push({ method: "POST", path, body, options });
        if (path.endsWith("/open")) return new Promise(resolve => { finishOpen = resolve; });
        return Promise.resolve({ data: { file: saved, supersedes: file.id, unchanged: false } });
      },
      get: async (path, options) => {
        requests.push({ method: "GET", path, options });
        if (path === `/personal-agent/ai-space/files/${saved.id}`) {
          if (failMetadata) throw new Error("新Word详情暂未读到");
          return { data: saved };
        }
        if (path === `/personal-agent/ai-space/files/${saved.id}/download`) return { data: corrupt ? new Blob([Buffer.alloc(bytes.length, 0)]) : blob };
        throw new Error("不得读取原ID或受限/content");
      },
    } },
  }, { URL, Blob, crypto: webcrypto, window: { open: () => popup } });
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalAiOfficeEditor, { file, onClose: () => { closed++; }, onBusy: value => { busy.push(value); if (!value) finishOperation?.(); }, onVersionCreated: value => created.push(value), onSaved: (value, body) => verified.push({ file: value, blob: body }) })); });
  const button = label => renderer.root.findAllByType("button").find(item => item.props.children === label);
  // WebCrypto 在原生任务中完成，等待真实忙态结束后再检查完整摘要。
  const readback = async () => act(async () => {
    const complete = new Promise(resolve => { finishOperation = resolve; });
    button("重新读取已回存的新版本").props.onClick();
    await complete;
    finishOperation = undefined;
  });
  await act(async () => { button("在线编辑").props.onClick(); button("在线编辑").props.onClick(); });
  assert.equal(requests.length, 1, "上传副本连点只发送一次");
  assert.equal(requests[0].body.expected_sha256, file.sha256);
  await act(async () => { renderer.root.findByType("modal").props.onCancel(); button("关闭").props.onClick(); });
  assert.equal(closed, 0, "Office忙态不能提前解除父级互斥");
  await act(async () => { finishOpen({ data: { session_id: "1".repeat(32), name: file.name, url: "https://alidocs.dingtalk.com/CODEX" } }); });
  assert.equal(popup.url, "https://alidocs.dingtalk.com/CODEX", "上传确认后立即打开钉钉编辑页");
  assert.equal(button("打开钉钉编辑").props.rel, "noopener noreferrer");
  await act(async () => { button("同步已保存内容").props.onClick(); button("同步已保存内容").props.onClick(); });
  assert.equal(requests.filter(item => item.method === "POST").length, 2);
  assert.equal(requests.find(item => item.path.endsWith("/save")).body.session_id, "1".repeat(32));
  assert.equal(created[0].id, saved.id);
  assert.equal(verified.length, 0);
  assert.equal(notices.length, 0);
  assert.ok(renderer.root.findAllByType("alert").some(item => item.props.description === "新Word详情暂未读到"));
  assert.equal(button("同步已保存内容").props.disabled, true);
  await act(async () => { button("同步已保存内容").props.onClick(); });
  assert.equal(requests.filter(item => item.method === "POST").length, 2);
  failMetadata = false; corrupt = true;
  await readback();
  assert.equal(verified.length, 0, "大小相同但哈希不同不能确认完整Word读取成功");
  assert.ok(renderer.root.findAllByType("alert").some(item => String(item.props.description).includes("SHA256 不一致")));
  corrupt = false;
  await readback();
  assert.equal(requests.filter(item => item.method === "POST").length, 2, "新版本回读重试没有重复回存POST");
  assert.equal(verified.length, 1);
  assert.equal(verified[0].file.id, saved.id);
  assert.equal(verified[0].blob, blob);
  assert.equal(notices.length, 1);
  assert.equal(requests.some(item => item.path.endsWith("/content")), false);
  assert.ok(requests.filter(item => item.method === "GET").every(item => item.path.includes(saved.id)));
  assert.equal(busy.at(-1), false);
  await act(async () => { renderer.unmount(); });
});

test("Office structured writer failures block replay unlike definite prewrite rejection", async () => {
  for (const definite of [true, false]) {
    const file = { id: "2".repeat(32), name: "原Word.docx", owner_user_id: 7, case_id: null, sha256: "3".repeat(64) };
    let saves = 0;
    const { PersonalAiOfficeEditor } = loadModule("../personal-agent/PersonalAiOfficeEditor.tsx", {
      antd: { Alert: "alert", Button: "button", Modal: ({ footer, children, ...props }) => React.createElement("modal", props, children, footer), message: { success: () => assert.fail("未确认的新文件不能提示成功") } },
      "./types": { errorText: (error, fallback) => error.message || fallback },
      "../api": { api: { post: async path => {
        if (path.endsWith("/open")) return { data: { session_id: "4".repeat(32), name: file.name, url: "https://alidocs.dingtalk.com/CODEX" } };
        saves++;
        throw new AxiosError("回存未完成", undefined, undefined, undefined, { status: 409, data: { detail: definite ? "回存前置拒绝" : { file_id: "5".repeat(32), status: "uncertain", detail: "对象计划已保留" } } });
      }, get: async () => assert.fail("失败回存不能读取未确认的新版本") } },
    }, { URL });
    let renderer;
    await act(async () => { renderer = create(React.createElement(PersonalAiOfficeEditor, { file, onClose() {}, onBusy() {}, onVersionCreated: () => assert.fail("失败不登记成功新版本"), onSaved: () => assert.fail("失败不确认读取") })); });
    const button = label => renderer.root.findAllByType("button").find(item => item.props.children === label);
    await act(async () => { button("在线编辑").props.onClick(); });
    await act(async () => { button("同步已保存内容").props.onClick(); });
    assert.equal(button("同步已保存内容").props.disabled, !definite);
    assert.ok(renderer.root.findAllByType("alert").some(item => item.props.description === "回存未完成"));
    await act(async () => { button("同步已保存内容").props.onClick(); });
    assert.equal(saves, definite ? 2 : 1, "仅确定未写入的拒绝允许再次人工确认；含file_id/status的计划不得重放");
    await act(async () => { renderer.unmount(); });
  }
});

test("agent workspace releases screenshot URLs on removal and unmount, and reports upload failures", async () => {
  const skillCatalog = loadModule("../agentSkillCatalog.ts", {});
  const notices = [];
  const urls = [];
  let failUpload = false;
  let pendingUpload = false;
  let resolveUpload;
  let uploadSignal;
  let streamController;
  const api = { get: async path => { assert.equal(path, "/agent/skills"); return { data: { items: [{ id: "other", available: true }] } }; }, post: async (_path, _form, options) => {
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
    "../../agentSkillRouting": { ...loadModule("../agentSkillRouting.ts", {}), DEFAULT_AGENT_SKILL: "qa" },
    "../../agentSkillCatalog": skillCatalog,
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
  await act(async () => { await skillCatalog.refreshAgentSkillCatalogConsumers(); });
  assert.equal(current.drawerProps.agentSkillId, "", "案件窗口接收真实目录刷新，删除当前选项后清空而不选其他技能");
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

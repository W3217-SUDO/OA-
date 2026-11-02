// 连接 MCP 面板：整段多服务 mcpServers 当成一个 MCP 分组（陶威 11-02，企查查 10 个远程服务 + 1 个 npx）；只用假 Key。
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

const FAKE_KEY = "CODEX-fake-qcc-key";
const QCC = ["company", "risk", "ipr", "operation", "history", "executive", "regulation", "case", "tender", "document"];
const qccPaste = () => JSON.stringify({ mcpServers: {
  ...Object.fromEntries(QCC.map(name => [`qcc-${name}`, { type: "streamableHttp", url: `https://agent.qcc.com/mcp/${name}/stream`, headers: { Authorization: `Bearer ${FAKE_KEY}` } }])),
  "qcc-local": { command: "npx", args: ["-y", "some-local-mcp"], env: { KEY: FAKE_KEY } },
} }, null, 2);

const config = loadModule("personalMcpConfig.ts");
// 被测模块运行在独立 vm 上下文，数组比较前先转成本上下文的普通值。
const plain = value => JSON.parse(JSON.stringify(value));

test("整段企查查配置载入为一个分组：10 个远程服务共用一个 Key，npx 服务跳过不报错", () => {
  const draft = config.parsePersonalMcpConfig(qccPaste());
  assert.equal(draft.name, "企查查", "分组名默认取服务商名称");
  assert.deepEqual(plain(draft.services.map(service => service.server_name)), QCC.map(name => `qcc-${name}`));
  assert.equal(draft.auth_type, "bearer");
  assert.equal(draft.credential, FAKE_KEY);
  assert.deepEqual(plain(draft.skipped), ["qcc-local"]);
  assert.match(config.LOCAL_COMMAND_SKIPPED, /服务器不支持本机命令型 MCP，已跳过/);
  assert.equal(config.validatePersonalMcpDraft(draft), "");
  const servers = config.personalMcpConfiguration(draft)["mcp.json"].mcpServers;
  assert.equal(Object.keys(servers).length, 10);
  assert.ok(Object.values(servers).every(server => server.headers.Authorization === `Bearer ${FAKE_KEY}` && server.type === "streamableHttp"));
  assert.equal(servers["qcc-tender"].url, "https://agent.qcc.com/mcp/tender/stream");
  assert.equal(servers["qcc-local"], undefined);
});

test("分组名：无已知服务商时取共同前缀，再退到域名；不同 Key 不能合成一组；只有本机服务时提示", () => {
  const services = names => names.map(name => ({ server_name: name, server_url: `https://mcp.example.org/${name}`, transport: "streamable_http" }));
  assert.equal(config.defaultGroupName(services(["acme-search", "acme-docs"])), "acme");
  assert.equal(config.defaultGroupName(services(["search", "docs"])), "example");
  const mixed = JSON.stringify({ mcpServers: { a: { url: "https://x.example.org/a", headers: { Authorization: "Bearer CODEX-fake-1" } }, b: { url: "https://x.example.org/b", headers: { Authorization: "Bearer CODEX-fake-2" } } } });
  assert.throws(() => config.parsePersonalMcpConfig(mixed), /Key 不一致/);
  const local = JSON.stringify({ mcpServers: { only: { command: "npx", args: [] } } });
  assert.throws(() => config.parsePersonalMcpConfig(local), /服务器不支持本机命令型 MCP，已跳过：only/);
  const single = config.parsePersonalMcpConfig(JSON.stringify({ mcpServers: { baidu: { url: "https://qianfan.baidubce.com/mcp", description: "说明" } } }));
  assert.equal(single.services.length, 0, "单个服务仍按原单连接表单");
  assert.equal(single.name, "baidu");
});

test("列表把分组显示成一个 MCP：服务与工具可展开，整组启停、删除", async () => {
  const calls = [];
  const Form = Object.assign(props => React.createElement("form", props), { Item: "form-item" });
  const Input = Object.assign(props => React.createElement("input", props), { Password: "password" });
  const { PersonalMcpConnectionCard } = loadModule("PersonalMcpConnectionCard.tsx", {
    antd: { Alert: "alert", Button: "button", Form, Input, Popconfirm: "confirm", Select: "select", Spin: "spin", Switch: "switch", Tag: "tag", Tooltip: ({ children }) => children },
    "@ant-design/icons": new Proxy({}, { get: () => "icon" }),
  });
  const group = { id: "personal-mcp-" + "a".repeat(32), name: "企查查", revision: "r".repeat(32), status: "verified", scope: "global", can_manage: true, enabled: true,
    services: [{ name: "qcc-company", tool_count: 2, tools: ["get_company", "search"], error: "" }, { name: "qcc-risk", tool_count: null, tools: [], error: "服务返回HTTP401" }] };
  const draft = { ...config.parsePersonalMcpConfig(qccPaste()), credential: "" };
  const mcp = { draft, error: "", connection: null, items: [group], listError: "", listing: false, busy: false, scope: "global", editing: false, credentialSaved: false,
    update() {}, importConfig() {}, close() {}, saveAndConnect() {}, retryTest() {}, refresh() {}, edit() {}, newConnection() {},
    remove: item => calls.push(["remove", item.id]), setEnabled: (item, enabled) => calls.push(["enabled", item.id, enabled]) };
  let renderer;
  await act(async () => { renderer = create(React.createElement(PersonalMcpConnectionCard, { connection: mcp })); });
  const texts = renderer.root.findAllByType("tag").map(tag => [].concat(tag.props.children).join(""));
  assert.ok(texts.includes("分组 · 2 个服务"));
  const details = renderer.root.findAllByType("details");
  assert.equal(details.length, 1);
  const summary = details[0].findByType("summary").props.children.join("");
  assert.equal(summary, "2 个服务 · 2 个工具");
  assert.ok(details[0].findAllByType("small").some(item => item.props.children === "get_company、search"));
  assert.ok(details[0].findAllByType("span").some(item => item.props.children === "检测失败：服务返回HTTP401"));
  assert.ok(renderer.root.findAllByType("alert").some(alert => alert.props.title === "服务器不支持本机命令型 MCP，已跳过：qcc-local"));
  const services = renderer.root.findByProps({ "aria-label": "分组内服务" });
  assert.equal(services.findAllByType("li").length, 10, "表单列出分组内全部服务，不显示完整地址");
  assert.ok(renderer.root.findAllByType("form-item").some(item => item.props.label === "Bearer Token（整组共用）"));
  assert.equal(renderer.root.findAllByProps({ id: "personal-mcp-url" }).length, 0);
  const toggle = renderer.root.findByType("switch");
  await act(async () => { toggle.props.onChange(false); });
  assert.deepEqual(plain(calls.at(-1)), ["enabled", group.id, false]);
  const confirm = renderer.root.findByType("confirm");
  assert.match(confirm.props.description, /整组 2 个服务一起删除/);
  assert.ok(!renderer.root.findAllByType("password").some(item => String(item.props.value).includes(FAKE_KEY)) && !renderer.root.findAll(node => typeof node.type === "string" && Object.values(node.props).some(value => typeof value === "string" && value.includes(FAKE_KEY))).length, "Key 不出现在界面上");
  await act(async () => { renderer.unmount(); });
});

// 501634（tgn 11-06 15:31 确认）：确认和追问都在对话框里解决——修改卡片在对话里，输入框上方问题条点选（编号选项 + 其他补充，多题分页答完一起发）。
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import Module, { createRequire } from "node:module";
import { build } from "esbuild";
import React from "react";
import { act, create } from "react-test-renderer";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

async function load(entry, name) {
  const output = await build({
    entryPoints: [fileURLToPath(new URL(entry, import.meta.url))],
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", loader: { ".css": "empty" },
    plugins: [{ name: "stub-501634q", setup(builder) {
      builder.onResolve({ filter: /^antd$|^@ant-design\/icons$/ }, ({ path }) => ({ path, namespace: "stub" }));
      builder.onLoad({ filter: /.*/, namespace: "stub" }, ({ path }) => ({ resolveDir: fileURLToPath(new URL(".", import.meta.url)), contents:
        path === "antd"
          ? 'import React from "react"; export const Button=p=>React.createElement("button",p,p.children); export const Tooltip=p=>p.children; export const Input=p=>React.createElement("input",{...p,onKeyDown:undefined});'
          : 'const I=()=>null; export const ArrowRightOutlined=I,CloseOutlined=I,EditOutlined=I,LeftOutlined=I,RightOutlined=I;' }));
    } }],
  });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL(".", import.meta.url)));
  target.require = createRequire(import.meta.url);
  target._compile(output.outputFiles[0].text, fileURLToPath(import.meta.url));
  return name ? target.exports[name] : target.exports;
}

const textOf = (node) => node == null ? "" : typeof node === "string" ? node : Array.isArray(node) ? node.map(textOf).join("") : textOf(node.children);

test("追问格式：拆出正文和问题，格式不对就当普通文字", async () => {
  const { parseAgentAsk, formatAgentAnswers } = await load("../src/legal/caseAgentAsk.ts");
  const reply = '找到两个相近案件，请选一个。\n【追问】{"questions":[{"question":"是哪个案件？","options":["HZMS2600001","HZMS2600002","其他"]},{"question":"合同建好后是否直接送审？","options":["先留草稿，不送审","建好直接送审"]}]}';
  const parsed = parseAgentAsk(reply);
  assert.equal(parsed.text, "找到两个相近案件，请选一个。");
  assert.deepEqual(parsed.questions.map((item) => item.options), [["HZMS2600001", "HZMS2600002"], ["先留草稿，不送审", "建好直接送审"]], "“其他”由界面统一加，不重复");
  assert.deepEqual(parseAgentAsk("【追问】不是 JSON").questions, []);
  assert.equal(parseAgentAsk("普通回复").text, "普通回复");
  assert.equal(formatAgentAnswers(parsed.questions, ["HZMS2600002", "建好直接送审"]),
    "1. 是哪个案件？\nHZMS2600002\n2. 合同建好后是否直接送审？\n建好直接送审");
});

test("问题条：一题一页，点选项进下一题，全部答完一起交；可打字补充；关掉不算回答", async () => {
  const CaseAgentQuestionBar = await load("../src/legal/CaseAgentQuestionBar.tsx", "CaseAgentQuestionBar");
  const submitted = [];
  let closed = 0;
  const questions = [{ question: "是哪个案件？", options: ["HZMS2600001", "HZMS2600002"] }, { question: "是否直接送审？", options: ["先留草稿，不送审", "建好直接送审"] }];
  let renderer;
  await act(async () => { renderer = create(React.createElement(CaseAgentQuestionBar, { questions, onSubmit: (a, t) => submitted.push([a, t]), onClose: () => { closed += 1; } })); });
  const option = (label) => renderer.root.findAll((node) => node.type === "button" && node.props.role === "option").find((node) => textOf(node.children).includes(label));
  assert.match(textOf(renderer.toJSON()), /是哪个案件？1\/2/);
  await act(async () => option("HZMS2600002").props.onClick());
  assert.equal(submitted.length, 0, "还有题没答，不提交");
  assert.match(textOf(renderer.toJSON()), /是否直接送审？2\/2/);
  const input = renderer.root.findByProps({ "aria-label": "其他补充" });
  await act(async () => input.props.onChange({ target: { value: "先给我看合同草稿" } }));
  await act(async () => renderer.root.findByProps({ "aria-label": "其他补充" }).props.onPressEnter());
  assert.deepEqual(submitted, [[["HZMS2600002", "先给我看合同草稿"], [false, true]]]);
  await act(async () => renderer.root.findByProps({ "aria-label": "关闭问题条" }).props.onClick());
  assert.equal(closed, 1);
});

test("案件智能体：不再弹浮动确认窗口；卡片在对话里，确认问题条给批准/驳回/补充，关掉留“待确认 N”", () => {
  const drawer = read("../src/legal/CaseAgentDrawer.tsx");
  assert.doesNotMatch(drawer, /CaseAgentConfirmFloat/);
  assert.equal(fs.existsSync(new URL("../src/legal/CaseAgentConfirmFloat.tsx", import.meta.url)), false);
  assert.match(drawer, /single \? \["批准并执行", "驳回，不修改"\] : \["全部批准并执行", "全部驳回"\]/);
  assert.match(drawer, /if \(await decideAll\("rejected"\)\) void sendOrGenerate\(`对刚才的修改补充：\$\{answers\[0\]\}`\)/, "补充：先驳回这一版，再按补充重新出卡片");
  assert.match(drawer, /待确认 \{waitingActions\.length\}/);
  assert.match(drawer, /const askOpen = Boolean\(lastAsk\.length\) && !waitingActions\.length && !agentSending/);
  assert.match(drawer, /item\.role === "assistant" \? parseAgentAsk\(item\.content \|\| ""\)\.text : item\.content/, "追问 JSON 不显示在气泡里");
  const card = read("../src/legal/CaseAgentConfirmCard.tsx");
  assert.match(card, /驳回此项/);
  const css = read("../src/agentPending.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(css, /case-agent-confirm-float|position: fixed/);
  assert.doesNotMatch(css, /color-mix\(|:has\(|@container|dvh/);
});

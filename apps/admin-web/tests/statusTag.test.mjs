import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import Module, { createRequire } from "node:module";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import React from "react";
import { act, create } from "react-test-renderer";
import { POPUP_WIDTH } from "../src/components/common/popupSize.ts";
import { STATUS_GROUPS, STATUS_TONE, STATUS_TONE_COLOR, statusToneOf } from "../src/components/common/statusTone.ts";

// 诉讼阶段不进状态总表，迁移时这些值走 StageTag。
const CASE_STAGES = new Set(["文书准备", "一审立案受理", "一审准备开庭", "待上诉", "二审", "执行"]);
// 尚未迁移的模块里的中文状态表，迁移前每个状态都必须在总表里有归属；迁完一个就从这里删掉。
const LEGACY_MAPS = ["BusinessPage.tsx", "WarehousePage.tsx", "feedback/FeedbackManager.tsx"];

test("弹窗四档宽度固定为 520/760/960/1200", () => {
  assert.deepEqual(POPUP_WIDTH, { sm: 520, md: 760, lg: 960, xl: 1200 });
});

test("每个状态只属于一种含义，含义都有颜色", () => {
  const seen = new Map();
  for (const [tone, statuses] of Object.entries(STATUS_GROUPS)) {
    assert.ok(STATUS_TONE_COLOR[tone], `${tone} 缺少颜色`);
    for (const status of statuses) {
      assert.ok(!seen.has(status), `${status} 同时出现在 ${seen.get(status)} 和 ${tone}`);
      seen.set(status, tone);
    }
  }
  assert.equal(Object.keys(STATUS_TONE).length, seen.size);
  assert.equal(statusToneOf(" 已取消 "), "neutral");
  assert.equal(statusToneOf("已归档"), "success");
  assert.equal(statusToneOf("二审"), undefined);
  assert.equal(statusToneOf(null), undefined);
});

test("各模块旧状态表里的中文状态都已收进总表或属于诉讼阶段", () => {
  const missing = [];
  for (const file of LEGACY_MAPS) {
    const source = readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8");
    for (const block of source.matchAll(/(?:status|asset)\w*colou?rs?\s*(?::[^=\n]+)?=\s*\{([^}]*)\}/gi)) {
      for (const key of block[1].matchAll(/['"]?([一-龥]+)['"]?\s*:/g)) {
        if (!STATUS_TONE[key[1]] && !CASE_STAGES.has(key[1])) missing.push(`${file}：${key[1]}`);
      }
    }
  }
  assert.deepEqual(missing, []);
});

async function loadStatusTag() {
  const result = await build({
    entryPoints: [fileURLToPath(new URL("../src/components/common/StatusTag.tsx", import.meta.url))],
    bundle: true, write: false, platform: "node", format: "cjs", packages: "external", jsx: "automatic",
    plugins: [{ name: "stub-antd", setup(builder) {
      builder.onResolve({ filter: /^antd$/ }, () => ({ path: "antd", namespace: "test" }));
      builder.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: 'export const Tag="Tag";' }));
    } }],
  });
  const target = new Module(fileURLToPath(import.meta.url));
  target.paths = Module._nodeModulePaths(fileURLToPath(new URL(".", import.meta.url)));
  target.require = createRequire(import.meta.url);
  target._compile(result.outputFiles[0].text, fileURLToPath(import.meta.url));
  return target.exports;
}

test("StatusTag 按总表上色，查不到时按灰色或阶段标签显示", async () => {
  const { StatusTag } = await loadStatusTag();
  const render = (props) => {
    let rendered;
    act(() => { rendered = create(React.createElement(StatusTag, props)); });
    const tag = rendered.root.findByType("Tag");
    return { color: tag.props.color, variant: tag.props.variant, text: tag.props.children };
  };
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  try {
    assert.deepEqual(render({ status: "待审批" }), { color: "orange", variant: undefined, text: "待审批" });
    assert.deepEqual(render({ status: "待审批", label: "待审核" }), { color: "orange", variant: undefined, text: "待审核" });
    assert.deepEqual(render({ status: "已取消" }), { color: "default", variant: undefined, text: "已取消" });
    assert.deepEqual(render({ status: "未知状态" }), { color: "default", variant: undefined, text: "未知状态" });
    assert.deepEqual(render({ status: "二审", fallback: "stage" }), { color: undefined, variant: "outlined", text: "二审" });
    assert.deepEqual(render({ status: "已归档", fallback: "stage" }), { color: "green", variant: undefined, text: "已归档" });
    assert.deepEqual(render({ status: "已驳回", tone: "neutral" }), { color: "default", variant: undefined, text: "已驳回" });
    assert.deepEqual(render({ status: "" }), { color: "default", variant: undefined, text: "—" });
  } finally {
    delete globalThis.IS_REACT_ACT_ENVIRONMENT;
  }
});

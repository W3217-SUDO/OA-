// 钉钉 Android 内置浏览器（Chrome 100）不支持 color-mix/dvh：构建期回退插件的计算和产出。
import assert from "node:assert/strict";
import test from "node:test";
import postcss from "postcss";
import legacyWebviewCss, { LEGACY_SUPPORTS, formatColor, mixColors, parseColor, staticValue } from "../scripts/legacy-webview-css.mjs";

const themeVars = () => ({
  light: new Map([["--oa-primary", "#00a65a"], ["--oa-ink", "100%"], ["--oa-surface", "#ffffff"]]),
  dark: new Map([["--oa-primary", "#2fbf7f"], ["--oa-ink", "42%"], ["--oa-surface", "#111113"]]),
});
const run = (css) => postcss([legacyWebviewCss({ themeVars: themeVars() })]).process(css, { from: undefined }).css;

test("srgb 混色与浏览器一致：按比例混合、透明度预乘、百分比不足 100% 时降低不透明度", () => {
  assert.equal(formatColor(mixColors(parseColor("#00a65a"), 10, parseColor("#ffffff"), undefined)), "#e6f6ef");
  assert.equal(formatColor(mixColors(parseColor("#000000"), undefined, parseColor("#ffffff"), undefined)), "#808080");
  assert.equal(formatColor(mixColors(parseColor("#00a65a"), 16, parseColor("transparent"), undefined)), "rgba(0, 166, 90, 0.16)");
  assert.equal(formatColor(mixColors(parseColor("#ff0000"), 30, parseColor("#0000ff"), 30)), "rgba(128, 0, 128, 0.6)");
  assert.equal(parseColor("currentColor"), null);
});

test("变量和嵌套 color-mix 都能展开；只替换 color-mix，其余 var() 保留", () => {
  const lookup = (name) => themeVars().light.get(name);
  assert.equal(staticValue("0 0 0 3px color-mix(in srgb, var(--oa-primary) 16%, transparent)", lookup), "0 0 0 3px rgba(0, 166, 90, 0.16)");
  assert.equal(staticValue("color-mix(in srgb, color-mix(in srgb, var(--oa-primary) 76%, #000) var(--oa-ink), #fff)", lookup), "#007e44");
  assert.equal(staticValue("linear-gradient(var(--x), color-mix(in srgb, 50% var(--oa-primary), #fff))", lookup), "linear-gradient(var(--x), #80d3ad)");
  assert.throws(() => staticValue("color-mix(in srgb, var(--missing) 10%, #fff)", lookup));
});

test("普通属性在原声明前插静态值，夜间值放进只有旧内核生效的 @supports 规则", () => {
  const output = run(".a{color:color-mix(in srgb, var(--oa-primary) 10%, var(--oa-surface))}");
  assert.match(output, /\.a\{color:#e6f6ef;color:color-mix\(in srgb, var\(--oa-primary\) 10%, var\(--oa-surface\)\)\}/);
  assert.ok(output.includes(`@supports ${LEGACY_SUPPORTS}`));
  assert.match(output, /:root\[data-theme="dark"\] \.a\{color:#14221e\}/);
});

test("自定义属性改在 @supports 里给同一选择器写静态值；:root 的夜间版本加在 :root 上", () => {
  const output = run(":root{--tint:color-mix(in srgb, var(--oa-primary) 10%, var(--oa-surface))}");
  assert.ok(!/--tint:#e6f6ef;--tint:/.test(output), "自定义属性不能用前置回退");
  assert.match(output, /@supports not \(color: color-mix\(in srgb, red 50%, blue\)\)\{\s*:root\{--tint:#e6f6ef\}\s*:root\[data-theme="dark"\]\{--tint:#14221e\}/);
});

test("只在夜间生效的规则按夜间变量计算；关键帧只插静态值", () => {
  const dark = run(':root[data-theme="dark"] .b{background:color-mix(in srgb, var(--oa-primary) 10%, var(--oa-surface))}');
  assert.match(dark, /\.b\{background:#14221e;background:color-mix/);
  assert.ok(!dark.includes("@supports"));
  const frames = run("@keyframes glow{50%{box-shadow:0 0 0 4px color-mix(in srgb, var(--oa-primary) 20%, transparent)}}");
  assert.match(frames, /50%\{box-shadow:0 0 0 4px rgba\(0, 166, 90, 0.2\);box-shadow:0 0 0 4px color-mix/);
  assert.ok(!frames.includes("@supports"));
});

test("dvh/svh 前插一条 vh 版本，重复处理不会重复插入", () => {
  const output = run(".c{height:calc(100dvh - 50px)}");
  assert.equal(output, ".c{height:calc(100vh - 50px);height:calc(100dvh - 50px)}");
  assert.equal(run(output), output);
});

// 店铺链接、产品链接：从分享文案里认出 http(s) 网址做成可点链接，其余文字照常显示。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const source = read("../src/components/LinkifiedText.tsx");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const module = { exports: {} };
new Function("exports", "require", "module", compiled)(module.exports, () => ({ jsx: () => null, jsxs: () => null, Fragment: "f" }), module);
const { splitLinkText } = module.exports;

test("淘宝分享文案只把网址做成链接", () => {
  const parts = splitLinkText("【淘宝】17🔒mMjFTzuCvMe🔒 https://m.tb.cn/h.jU9ghQLNXK9U38f CZ225 我分享给你了一个超赞的内容");
  assert.deepEqual(parts.filter((p) => p.href).map((p) => p.href), ["https://m.tb.cn/h.jU9ghQLNXK9U38f"]);
  assert.equal(parts.map((p) => p.text).join(""), "【淘宝】17🔒mMjFTzuCvMe🔒 https://m.tb.cn/h.jU9ghQLNXK9U38f CZ225 我分享给你了一个超赞的内容");
});

test("网址紧跟中文、结尾标点不算进链接；多个网址都识别", () => {
  const parts = splitLinkText("店铺https://v.douyin.com/abc/，商品 http://a.com/x?y=1.");
  assert.deepEqual(parts.filter((p) => p.href).map((p) => p.text), ["https://v.douyin.com/abc/", "http://a.com/x?y=1"]);
});

test("javascript: 等不是 http/https 的不做成链接", () => {
  assert.deepEqual(splitLinkText("javascript:alert(1) data:text/html,x").filter((p) => p.href), []);
});

test("三个显示位置都用同一个组件", () => {
  assert.match(read("../src/legal/CaseDetail/CaseClueDetails.tsx"), /label: "店铺链接", children: <LinkifiedText/);
  assert.match(read("../src/legal/CaseDetail/CaseClueDetails.tsx"), /label: "产品链接", children: <LinkifiedText/);
  assert.match(read("../src/investigation/ClueDetail/ClueDetailHeader.tsx"), /children: <LinkifiedText value=\{investigationDetail\.data\.store_url\} \/>/);
  assert.match(read("../src/legal/CaseDetail/CaseCluesPanel.tsx"), /<LinkifiedText value=\{clue\.data\.shop_address/);
  assert.match(source, /rel="noopener noreferrer"/);
});

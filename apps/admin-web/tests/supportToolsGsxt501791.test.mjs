// 501791（思法汇成 11-08）：办案辅助工具里“全国组织机构查询平台”换成国家企业信用信息公示系统，新窗口打开，旁边提示用浏览器记住密码；系统不保存外部密码。
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../src/dashboard.css", import.meta.url), "utf8");

test("办案辅助工具：用国家企业信用信息公示系统替换全国组织机构查询平台", () => {
  const block = app.slice(app.indexOf("const supportTools"), app.indexOf("];", app.indexOf("const supportTools")));
  assert.match(block, /\{ label: "国家企业信用信息公示系统", href: "https:\/\/www\.gsxt\.gov\.cn\/index\.html", hint: "从首页登录；首次登录后可让浏览器记住密码" \}/);
  assert.doesNotMatch(block, /全国组织机构查询平台|cods\.org\.cn/);
  // 对方已拦截的老地址不能再用。
  assert.doesNotMatch(block, /txnT01\.do|shiming\.gsxt/);
  assert.match(block, /href: "https:\/\/sbj\.cnipa\.gov\.cn\/trademark-query"/);
  assert.equal((block.match(/label: "/g) || []).length, 5, "其余 4 个链接不变");
  for (const word of ["国家知识产权局商标局", "国家知识产权局专利局", "法律法规查询", "裁判文书检索"]) assert.ok(block.includes(word), word);
});

test("办案辅助工具：新窗口打开并显示提示，不存密码", () => {
  const render = app.slice(app.indexOf("{supportTools.map("), app.indexOf("))}", app.indexOf("{supportTools.map(")));
  assert.match(render, /target="_blank"/);
  assert.match(render, /rel="noreferrer"/);
  assert.match(render, /item\.hint && <small className="support-tools-hint">\{item\.hint\}<\/small>/);
  assert.doesNotMatch(app, /gsxt[^\n]*(password|密码"\s*:)/i);
  assert.match(css, /\.support-tools-hint\{/);
  const rules = css.slice(css.indexOf(".support-tools-text{"), css.indexOf("}", css.indexOf(".support-tools-hint{")) + 1);
  assert.doesNotMatch(rules, /color-mix|:has\(/, "钉钉旧内核兼容");
});

// 1028 陶威反馈：钉钉工作台登录页“绑定钉钉并登录”按钮在钉钉手机内核（Chrome 100）里显示成空框。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const css = fs.readFileSync(new URL("../src/huzhi-login.css", import.meta.url), "utf8");

test("沪知登录页不用 Chrome 100 不支持的 color-mix，登录按钮背景始终可见", () => {
  assert.ok(!css.includes("color-mix("), "color-mix 与 var() 一起用时整条声明失效，按钮背景变透明");
  const button = css.slice(css.indexOf(".login-page-huzhi .login-card .login-submit-button {"));
  assert.match(button.slice(0, button.indexOf("}")), /background: linear-gradient\(180deg, #4672be, var\(--huzhi-ink\)\);/);
});

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

test("1029：个人设置有“解绑钉钉”（钉钉内解绑当前身份并退出），员工账号里逐个列出并解绑", () => {
  const center = fs.readFileSync(new URL("../src/UserCenterPage.tsx", import.meta.url), "utf8");
  assert.match(center, /<Popconfirm title="解绑钉钉"/);
  assert.match(center, /api\.post\('\/auth\/me\/dingtalk\/unbind',\{auth_code\}\)/);
  assert.match(center, /dispatchEvent\(new Event\('sunhold:session-end'\)\)/);
  const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  assert.match(app, /addEventListener\("sunhold:session-end", endClientSession\)/);
  const bindings = fs.readFileSync(new URL("../src/system/SystemUserDingTalkBindings.tsx", import.meta.url), "utf8");
  assert.match(bindings, /api\.delete\(`\/system\/users\/\$\{userId\}\/dingtalk-bindings\//);
  assert.ok(!bindings.includes("color-mix("));
  const management = fs.readFileSync(new URL("../src/system/SystemUserManagement.tsx", import.meta.url), "utf8");
  assert.match(management, /editingUser && <SystemUserDingTalkBindings userId=\{editingUser\.id\} form=\{userForm\} \/>/);
});

test("1029：钉钉内退出后再打开先选账号，可“登录其他账号”加入列表；选账号页样式兼容 Chrome 100", () => {
  const app = fs.readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
  assert.match(app, /if \(getDingTalkEnvironment\(\)\.platform !== "notInDingTalk"\) localStorage\.setItem\(DINGTALK_CHOOSE_KEY, "1"\);\n    endClientSession\(\);/);
  assert.match(app, /choose: localStorage\.getItem\(DINGTALK_CHOOSE_KEY\) === "1"/);
  assert.match(app, /api\.post\("\/auth\/dingtalk\/choose", \{ ticket: dingtalkChooser\.ticket, username \}\)/);
  assert.match(app, /api\.post\("\/auth\/dingtalk\/bind", \{ \.\.\.values, ticket: dingtalkChooser\.ticket \}\)/);
  assert.match(app, />登录其他账号<\/Button>/);
  const styles = fs.readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const chooser = styles.slice(styles.indexOf("/* 钉钉选账号页"));
  assert.ok(!/color-mix\(|:has\(|@container|dvh/.test(chooser));
});

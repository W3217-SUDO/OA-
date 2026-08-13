import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const appSource = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const systemSource = fs.readFileSync(new URL("./src/SystemCenterPage.tsx", import.meta.url), "utf8");

test("DingTalk workbench login supports first-time OA binding and later SSO", () => {
  assert.match(appSource, /api\.get\("\/auth\/dingtalk\/config"\)/);
  assert.match(appSource, /requestDingTalkAuthCode\(\{ corpId: config\.corp_id \}\)/);
  assert.match(appSource, /api\.post\("\/auth\/dingtalk\/login"/);
  assert.match(appSource, /api\.post\("\/auth\/dingtalk\/bind"/);
  assert.equal(
    appSource.match(/requestDingTalkAuthCode\(\{ corpId: config\.corp_id \}\)/g)?.length,
    2,
    "first-time binding must request a fresh one-time DingTalk auth code",
  );
  assert.match(appSource, /绑定钉钉并登录/);
  assert.match(appSource, /以后从钉钉工作台打开将直接登录/);
});

test("system user management exposes DingTalk binding state and repair field", () => {
  assert.match(systemSource, /dingtalk_bound/);
  assert.match(systemSource, /钉钉 UserId/);
  assert.match(systemSource, /每个 UserId 只能绑定一个系统员工/);
});

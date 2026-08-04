import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

const supportToolsStart = source.indexOf("const supportTools = [");
assert.notEqual(supportToolsStart, -1, "supportTools should be declared in App.tsx");
const supportToolsEnd = source.indexOf("];", supportToolsStart);
assert.notEqual(supportToolsEnd, -1, "supportTools declaration should be closed");
const supportToolsSource = source.slice(supportToolsStart, supportToolsEnd);

test("support tools keep legacy external research destinations", () => {
  const expectedLinks = [
    ["国家知识产权局商标局", "http://wcjs.sbj.cnipa.gov.cn/txnT01.do"],
    ["国家知识产权局专利局", "http://pss-system.cnipa.gov.cn/sipopublicsearch/portal/uiIndex.shtml"],
    ["全国组织机构查询平台", "https://www.cods.org.cn"],
    ["法律法规查询", "https://flk.npc.gov.cn/"],
    ["裁判文书检索", "https://openlaw.cn/index.jsp"],
  ];

  for (const [label, href] of expectedLinks) {
    assert.ok(
      supportToolsSource.includes(`label: "${label}"`),
      `${label} should be listed in supportTools`,
    );
    assert.ok(
      supportToolsSource.includes(`href: "${href}"`),
      `${label} should open the old system destination`,
    );
  }
});

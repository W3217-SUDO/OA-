import assert from "node:assert/strict";
import fs from "node:fs";

const app = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("./src/styles.css", import.meta.url), "utf8");

const tabsIndex = app.indexOf('className="workspace-tabs topbar-workspace-tabs"');
const headerEndIndex = app.indexOf("</Header>", tabsIndex);
const contentIndex = app.indexOf('<Content\n          className=', headerEndIndex);

assert.ok(tabsIndex > 0, "workspace tabs must be rendered in the top bar");
assert.ok(headerEndIndex > tabsIndex, "workspace tabs must remain inside the header");
assert.ok(contentIndex > headerEndIndex, "content must start after the header tabs");
assert.equal(
  app.slice(contentIndex).includes('className="workspace-tabs"'),
  false,
  "content must not render a second workspace-tab row",
);
assert.match(app, /<Sider\s+width=\{200\}/);
assert.match(css, /\.logo \{[\s\S]*?width: 200px;[\s\S]*?min-width: 200px;/);
assert.match(css, /\.topbar-workspace-tabs\.ant-tabs-card > \.ant-tabs-nav \.ant-tabs-tab \{[\s\S]*?height: 50px;/);
assert.equal(app.includes("caseQuickKeyword"), false, "duplicate case quick-search state must be removed");
assert.equal(app.includes('className="case-quick-search"'), false, "top bar must render one combined search only");
assert.match(css, /\.global-search \{[\s\S]*?width: 320px;[\s\S]*?min-width: 320px;[\s\S]*?flex: 0 0 320px;/);
assert.match(css, /\.topbar-workspace-tabs \{[\s\S]*?min-width: 0;[\s\S]*?flex: 1 1 0;/);
assert.match(css, /\.topbar-workspace-tabs \.ant-tabs-nav-wrap \{[\s\S]*?min-width: 0;[\s\S]*?overflow: hidden;/);
assert.match(app, /aria-label="刷新当前页"/);

console.log("shell topbar layout regression: PASS");

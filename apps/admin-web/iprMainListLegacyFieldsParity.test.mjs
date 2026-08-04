import assert from "node:assert/strict";
import fs from "node:fs";

const legacy = fs.readFileSync(new URL("../../../旧系统归档源码/SH.CRM.WEB/Areas/IPR/Views/Case/CaseList.cshtml", import.meta.url), "utf8");
const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(legacy, /<th style="text-align: center">申请日<\/th>/, "Legacy IPR case list showed application date.");
assert.match(legacy, /<th style="text-align: center">处理人<\/th>/, "Legacy IPR case list showed case handler.");

assert.match(
  center,
  /\{\s*title: "申请日",[\s\S]*?row\.data\.application_date \|\| "—",/,
  "New IPR case list should render application date from existing detail data.",
);
assert.match(
  center,
  /\{\s*title: "处理人",[\s\S]*?row\.data\.case_manager \|\| "—",/,
  "New IPR case list should render the case handler from existing detail data.",
);

console.log("ipr main list legacy field parity: PASS");
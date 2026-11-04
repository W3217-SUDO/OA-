// 501312（fwl 11-04）：线索没有调查辅助员时，“调查员”一列只显示调查员，不多出“姓名待维护”。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../../api-server/app/core/contracts.py", import.meta.url), "utf8");

test("没有辅助员账号时不用辅助员显示名", () => {
  assert.match(page, /const assistants = !assistantUsernames\.length \? "" : r\.data\?\.investigation_assistant_display_name/);
});

test("后端空的人员字段不再显示成姓名待维护", () => {
  assert.match(api, /data\[f"\{key\}_display_name"\] = _contract_person_display_name\(data\.get\(key\), names_by_username\) if str\(data\.get\(key\) or ""\)\.strip\(\) else ""/);
});

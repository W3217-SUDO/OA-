import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const roles = fs.readFileSync(new URL("./src/OrganizationCenterPage.tsx", import.meta.url), "utf8");

const submitStart = source.indexOf("const submitCompanyScheduleCourtInfo = async");
const submitEnd = source.indexOf("const openHearing =", submitStart);
assert.notEqual(submitStart, -1, "court modal submit handler is required");
const submit = source.slice(submitStart, submitEnd);

assert.match(source, /can_edit_court_info: boolean/, "case capabilities must expose the dedicated court permission");
assert.match(source, /!getCaseCapability\(row\)\.can_edit_court_info/, "opening the court dialog must use the dedicated capability");
assert.match(source, /counselDetailCapabilities\.can_edit_court_info && <div className="case-detail-legacy-submenu">/, "the ordinary-case court submenu must be hidden without the permission");
assert.match(submit, /api\.put\(`\/cases\/\$\{companyScheduleCourtInfo\.row\.id\}\/court-info`, payload\)/, "court dialog must use its narrow direct-save endpoint");
assert.doesNotMatch(submit, /\/progress/, "court dialog must not use the workflow-progress endpoint");
for (const key of ["first_instance_court", "second_instance_court", "execution_court_name", "retrial_court_name"]) {
  assert.match(submit, new RegExp(key), `${key} must remain in the direct court payload`);
}
assert.match(roles, /"案件法院信息修改"/, "administrators must be able to assign the court permission in role management");

console.log("case court-info permission parity: PASS");

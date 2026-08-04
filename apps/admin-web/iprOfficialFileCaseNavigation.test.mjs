import assert from "node:assert/strict";
import fs from "node:fs";

const official = fs.readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");
const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  official,
  /const openLinkedIprCase = \(target: \{ caseId\?: number \| null; caseKind\?: string; caseNo\?: string \}\) => \{[\s\S]*?message\.warning\("当前官文未关联知识产权案件"\)/,
  "Official-file linked case navigation should warn clearly when the target case is missing.",
);

assert.match(
  official,
  /const openLinkedIprCase = \(target: \{ caseId\?: number \| null; caseKind\?: string; caseNo\?: string \}\) => \{[\s\S]*?params\.set\("page", target\.caseKind === "商标" \? "ipr-trademark" : "ipr-patent"\);[\s\S]*?params\.set\("record_id", String\(target\.caseId\)\)/,
  "Official-file linked case navigation should preserve the target IPR case id in the existing record_id contract.",
);

assert.match(
  official,
  /const openLinkedIprCase = \(target: \{ caseId\?: number \| null; caseKind\?: string; caseNo\?: string \}\) => \{[\s\S]*?window\.history\.pushState\([\s\S]*?window\.dispatchEvent\(new PopStateEvent\("popstate"\)\)/,
  "Official-file linked case navigation should route in-app without a full-page reload.",
);

assert.doesNotMatch(
  official,
  /window\.location\.assign/,
  "Official-file linked case navigation should not hard-refresh the app shell.",
);

assert.match(
  official,
  /render:\(_,r\)=><Button type="link" onClick=\{\(\)=>openLinkedIprCase\(\{ caseId: r\.data\.ipr_case_id, caseKind: r\.data\.case_kind, caseNo: r\.data\.ipr_case_no \}\)\}\>\{r\.data\.ipr_case_no\|\|"—"\}<\/Button>/,
  "Official-file list should use the in-app linked IPR case navigation helper.",
);

assert.match(
  official,
  /children:<Button type="link" onClick=\{\(\)=>openLinkedIprCase\(\{ caseId: detail\.data\.ipr_case_id, caseKind: detail\.data\.case_kind, caseNo: detail\.data\.ipr_case_no \}\)\}\>\{detail\.data\.ipr_case_no\|\|"—"\}<\/Button>/,
  "Official-file detail drawer should use the same linked IPR case navigation helper.",
);

assert.match(
  center,
  /new URLSearchParams\(window\.location\.search\)\.get\("record_id"\)/,
  "IPR center should keep consuming record_id from query params to open the linked case detail.",
);

console.log("ipr official-file linked case navigation: PASS");

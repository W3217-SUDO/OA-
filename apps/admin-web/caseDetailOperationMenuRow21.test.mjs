import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /data-testid="case-detail-operation-menu"/);
assert.match(source, /<Button>操作<\/Button>/);
assert.match(source, /caseDetailActionButtons/);
assert.match(source, /companyScheduleDetailActionButtons/);
assert.match(source, /shouldUseCompanyScheduleDetailOperationMenu\(initialView,caseListReturnContext\?\.route\)\?companyScheduleDetailActionButtons:caseDetailActionButtons/);
const detailExtraStart = source.indexOf("extra={viewingCounselCase&&");
const detailExtraEnd = source.indexOf("\n        {viewingCounselCase&&", detailExtraStart);
assert.ok(detailExtraStart >= 0 && detailExtraEnd > detailExtraStart);
assert.match(source.slice(detailExtraStart, detailExtraEnd), /dropdownRender=\{\(\)=>[\s\S]*caseDetailActionButtons/);

console.log("case detail operation menu row 21 contract passed");

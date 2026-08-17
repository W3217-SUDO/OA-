import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /data-testid="case-detail-operation-menu"/);
assert.match(source, /<Button>操作<\/Button>/);
assert.match(source, /placement="bottomRight"/);
assert.match(source, /caseDetailPrimaryActionButtons/);
assert.match(source, /caseDetailMoreActionButtons/);
assert.match(source, /data-testid="case-detail-more-operation"/);
assert.match(source, /data-testid="case-detail-more-operation-panel"/);
assert.match(source, /dropdownRender=\{\(\) => caseDetailPrimaryActionButtons\}/);

console.log("case detail legacy operation menu contract passed");

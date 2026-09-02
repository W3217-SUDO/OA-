import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

assert.equal((source.match(/void createSealApplication\(true\); }}>提交同步用印/g) || []).length, 2);
assert.doesNotMatch(source, /deferSyncSealSubmission/);
assert.match(source, /合同审批与用印申请已分别提交至对应审批渠道/);
assert.doesNotMatch(source, /合同通过后自动提交/);
assert.equal((source.match(/用印草稿待提交/g) || []).length, 2);
assert.equal((source.match(/已提交用印审批/g) || []).length, 2);

console.log("contract sync-seal immediate submission row 6 frontend contract passed");

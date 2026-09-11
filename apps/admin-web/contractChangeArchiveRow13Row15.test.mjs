import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { contractSecondaryActionPolicy } from "./src/contractWorkflowPolicy.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const modal = fs.readFileSync(path.join(here, "src/contract/ContractModals.tsx"), "utf8");
const actions = fs.readFileSync(path.join(here, "src/contract/services/workflowActions.tsx"), "utf8");
const backend = fs.readFileSync(path.join(here, "../api-server/app/areas/contract/router.py"), "utf8");

// Row 13: the edit page must present a save action and the API must complete
// the change directly instead of leaving a pending approval item.
assert.match(modal, /okText="保存变更"/);
assert.match(modal, />保存变更<\/Button>/);
assert.match(actions, /合同变更已直接保存/);
assert.match(backend, /action="合同变更完成"/);
assert.match(backend, /"status": "已完成"/);
assert.match(backend, /contract\.description = str\(value\)/);
assert.match(backend, /"description": \(contract\.description or data\.get\("description", ""\)/);

// Row 15: the legacy list exposes the confirmation from any non-terminal
// state, including an in-progress approval; only terminal states are blocked.
assert.equal(contractSecondaryActionPolicy("审批通过").canArchive, true);
assert.equal(contractSecondaryActionPolicy("已完成").canArchive, true);
assert.equal(contractSecondaryActionPolicy("审批中").canArchive, true);
assert.equal(contractSecondaryActionPolicy("草稿").canArchive, true);
assert.equal(contractSecondaryActionPolicy("归档中").canArchive, false);
assert.match(backend, /当前合同已进入终止流程/);

console.log("contract row 13/15 parity checks passed");

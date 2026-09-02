import assert from "node:assert/strict";
import fs from "node:fs";
import { prioritizeCaseAssistantSelection } from "./src/caseSecondBatchParity.ts";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const payloadSource = fs.readFileSync(new URL("./src/caseSecondBatchParity.ts", import.meta.url), "utf8");

assert.match(source, /name="assistants" normalize=\{prioritizeCaseAssistantSelection\}><Select mode="multiple"/);
assert.match(source, /assistant_usernames \|\| row\.data\.assistants/);
assert.match(source, /name="assistants" normalize=\{prioritizeCaseAssistantSelection\}/);
assert.deepEqual(prioritizeCaseAssistantSelection(["old", "new"], ["old"]), ["new", "old"]);
assert.deepEqual(prioritizeCaseAssistantSelection(["new"], ["new", "old"]), ["new"]);
assert.deepEqual(prioritizeCaseAssistantSelection(["new", "old"], ["new", "old"]), ["new", "old"]);
assert.match(payloadSource, /kind === "normal" \? \{ assistants: list\(draft\.assistants\)/);

console.log("case multiple assistants row 5 frontend contract passed");

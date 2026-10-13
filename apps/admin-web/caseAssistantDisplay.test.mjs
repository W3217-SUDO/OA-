import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";
import { caseAssistantDisplayValues } from "./src/caseAssistantDisplay.ts";

const pageSource = fs.readFileSync(new URL("./src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.deepEqual(
  caseAssistantDisplayValues({ assistants_display_names: ["助理甲", "助理乙"], assistant: "助理甲" }),
  ["助理甲", "助理乙"],
);
assert.deepEqual(
  caseAssistantDisplayValues({
    assistants_display_names: ["【待补充中文姓名】", "【待补充中文姓名】"],
    assistant_usernames_display_names: ["助理甲", "助理乙"],
    assistants: ["历史甲", "历史乙"],
  }),
  ["助理甲", "助理乙"],
);
assert.deepEqual(
  caseAssistantDisplayValues({ assistant_usernames: ["assistant-a", "assistant-b"], assistant: "assistant-a" }),
  ["assistant-a", "assistant-b"],
);
assert.deepEqual(
  caseAssistantDisplayValues({
    assistants: ["助理甲"],
    assistant_usernames: ["assistant-a", "assistant-b"],
    assistant: "助理甲",
  }),
  ["assistant-a", "assistant-b"],
);
assert.deepEqual(
  caseAssistantDisplayValues({ assistant_display_names: ["显示甲", "显示乙"], assistant: "assistant-a" }),
  ["显示甲", "显示乙"],
);
assert.deepEqual(caseAssistantDisplayValues({ assistant: "历史助理" }), ["历史助理"]);
assert.deepEqual(caseAssistantDisplayValues({ legacy_record: { CaseAssistantName: "旧系统助理" } }), ["旧系统助理"]);
assert.deepEqual(caseAssistantDisplayValues({}), []);
// Exact empty persisted fields and response projections observed for the
// reported production record; no employee fixture or database write is needed.
assert.deepEqual(caseAssistantDisplayValues({
  assistant: "", assistants: [], assistant_username: "", assistant_usernames: [],
  assistant_display_name: "—", assistant_username_display_name: "—",
  assistant_usernames_display_names: [], assistants_display_names: [],
  legacy_record: { CaseAssistant: null, CaseAssistantName: null },
}), []);
assert.deepEqual(caseAssistantDisplayValues({
  assistant_display_name: " — ", legacy_record: { CaseAssistantName: "历史助理" },
}), ["历史助理"]);
assert.deepEqual(caseAssistantDisplayValues({
  assistant_usernames_display_names: ["—", "助理甲", "助理乙"],
}), ["助理甲", "助理乙"]);
assert.deepEqual(caseAssistantDisplayValues({ assistants: ["Alex", "助理甲"] }), ["Alex", "助理甲"]);
assert.deepEqual(caseAssistantDisplayValues({ assistant_usernames: ["unknown-account"] }), ["unknown-account"]);
assert.deepEqual(caseAssistantDisplayValues({ assistant_display_name: "姓名待维护" }), ["姓名待维护"]);
const headerSource = fs.readFileSync(new URL("./src/legal/CaseDetail/CaseDetailHeader.tsx", import.meta.url), "utf8");
assert.match(headerSource, /<th>律师助理<\/th><td>\{caseAssistantDisplayNames\(viewingCase\.data\)\}<\/td>/);
assert.match(pageSource, /case \"assistant\": return caseAssistantDisplayNames\(row\.data\)/);
assert.match(pageSource, /key:\"assistant\",width:120,render:[^\n]+caseAssistantDisplayNames\(row\.data\)/);
assert.match(pageSource, /<CaseDetailHeader[\s\S]+?viewingCase=\{viewingCounselCase\}[\s\S]+?caseAssistantDisplayNames=\{caseAssistantDisplayNames\}/);
assert.doesNotMatch(pageSource, /casePersonDisplayName\(row\.data\.assistant,row\.data\.assistant_display_name\)/);

// Execute the actual shared page display chain, so returning no candidates
// proves the displayed empty state instead of only testing token filtering.
const displayChain = pageSource.slice(
  pageSource.indexOf("  const casePersonDisplayName ="),
  pageSource.indexOf("  const legacyCaseParticipantDisplayNames ="),
);
assert.ok(displayChain.includes("const caseAssistantDisplayNames ="));
const compiledChain = ts.transpileModule(displayChain, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText;
const displayAssistant = new Function("caseAssistantOptions", "caseAssistantDisplayValues",
  `${compiledChain}\nreturn caseAssistantDisplayNames;`)([
    { value: "assistant-a", label: "助理甲" },
    { value: "assistant-b", label: "Alex" },
  ], caseAssistantDisplayValues);
assert.equal(displayAssistant({ assistant: "", assistant_display_name: "—", assistants: [], assistant_usernames: [] }), "—");
assert.equal(displayAssistant({ assistant_usernames: ["assistant-a", "assistant-b"] }), "助理甲、Alex");
assert.equal(displayAssistant({ assistant_usernames: ["unknown-account"] }), "姓名待维护");
assert.equal(displayAssistant({ assistant_display_name: "姓名待维护" }), "姓名待维护");
console.log("case assistant multi-value display passed");

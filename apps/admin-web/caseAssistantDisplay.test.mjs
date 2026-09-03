import assert from "node:assert/strict";
import fs from "node:fs";
import { caseAssistantDisplayValues } from "./src/caseAssistantDisplay.ts";

const pageSource = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

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
assert.match(pageSource, /<th>律师助理<\/th><td>\{caseAssistantDisplayNames\(viewingCounselCase\.data\)\}<\/td>/);
assert.doesNotMatch(pageSource, /casePersonDisplayName\(row\.data\.assistant,row\.data\.assistant_display_name\)/);

console.log("case assistant multi-value display passed");

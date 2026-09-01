import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const payloadSource = fs.readFileSync(new URL("./src/caseSecondBatchParity.ts", import.meta.url), "utf8");

assert.match(source, /name="assistants"><Select mode="multiple"/);
assert.match(source, /assistant_usernames \|\| row\.data\.assistants/);
assert.match(source, /assistantOrderRef = useRef<string\[\]>\(\[\]\)/);
assert.match(source, /onFocus=\{\(\)=>\{assistantOrderRef\.current=normalCaseEditForm\.getFieldValue\("assistants"\)\|\|\[\];\}\}/);
assert.match(source, /onChange=\{\(values:string\[\]\)=>\{const previous=assistantOrderRef\.current;const added=values\.find\(value=>!previous\.includes\(value\)\);const ordered=added\?\[added,\.\.\.previous\.filter\(value=>values\.includes\(value\)\)\]:previous\.filter\(value=>values\.includes\(value\)\);assistantOrderRef\.current=ordered;normalCaseEditForm\.setFieldValue\("assistants",ordered\);\}\}/);
assert.doesNotMatch(source, /setTimeout[^\n]*assistants/);
assert.match(payloadSource, /kind === "normal" \? \{ assistants: list\(draft\.assistants\)/);

console.log("case multiple assistants row 5 frontend contract passed");

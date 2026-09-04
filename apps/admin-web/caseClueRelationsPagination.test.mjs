import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const loaderStart = source.indexOf("const loadCounselDetailCluesPage = async");
const loaderEnd = source.indexOf("const openCaseTasks = async", loaderStart);
const loader = source.slice(loaderStart, loaderEnd);
const tabStart = source.indexOf('{key:"clues",label:"线索信息"');
const tabEnd = source.indexOf('{key:"reminders"', tabStart);
const tab = source.slice(tabStart, tabEnd);

assert.notEqual(loaderStart, -1, "case clue page loader is required");
assert.match(loader, /clue_page: nextPage/, "pagination must be requested from the server");
assert.match(loader, /clue_page_size: nextPageSize/, "page size must be requested from the server");
assert.match(loader, /clue_keyword: keyword/, "keyword search must be requested from the server");
assert.match(loader, /counselDetailClueRequestRef/, "stale clue responses must be ignored");
assert.match(tab, /<Input\.Search/, "the clue tab must expose a search control");
assert.match(tab, /counselDetailCluePagination/, "the clue table must use server pagination state");
assert.match(tab, /onClick=\{\(\)=>openRelatedClue\(row\)\}/, "the clue number must navigate to the clue detail");
assert.match(tab, /openCaseClueWorkspace\(row\)/, "the existing in-case clue workspace must remain available");
assert.match(source, /rememberInvestigationDetailTarget/, "detail navigation must preserve the selected clue context");
assert.match(source, /当前账号无权查看该调查线索详情/, "detail permission failures must be explicit");
assert.match(source, /关联调查线索不存在或已被删除/, "missing clue failures must be explicit");

console.log("case clue relations pagination: PASS");

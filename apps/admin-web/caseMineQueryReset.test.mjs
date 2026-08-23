import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case list reset returns to the first server page with an empty query", () => {
  assert.match(source, /caseQueryForm\.resetFields\(\);setCaseQuery\(\{\}\);setOriginalPage\(1\);if\(counselListMode\)void loadCounselCases\(\{\},1,counselPageSize\);else void loadOrdinaryCases\(\{\},1,originalPageSize\);/);
  assert.match(source, /const \[originalPage, setOriginalPage\] = useState\(caseListReturnContext\?\.page \|\| 1\)/);
  assert.match(source, /const \[originalPageSize, setOriginalPageSize\] = useState\(caseListReturnContext\?\.pageSize \|\| 15\)/);
  assert.match(source, /setOriginalPage\(nextPage\);setOriginalPageSize\(nextPageSize\);sessionStorage\.setItem\("sunhold:case-list-return"/);
  assert.match(source, /return loadOrdinaryCases\(nextQuery, 1, originalPageSize\)/);
});

test("ordinary case list retains detail, export, and batch entry points", () => {
  assert.match(source, /onClick=\{\(\)=>void openCounselDetail\(row\)\}/);
  assert.match(source, /const exportCases = async \(\) => \{/);
  assert.match(source, /exportSelectedCasesExcel\(true\)/);
  assert.match(source, /setBatchUpdateOpen\(true\)/);
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

const returnBodyMatch = source.match(
  /const returnToCaseList = \(\) => \{([\s\S]*?)\n  \};\n  const advanceCreateStep/,
);
assert.ok(returnBodyMatch, "CaseCenterPage 应保留详情返回来源列表的实现");

const executeReturnToCaseList = new Function(
  "caseListReturnContext",
  "originalPage",
  "originalPageSize",
  "sessionStorage",
  "setOriginalPage",
  "setOriginalPageSize",
  "onNavigate",
  returnBodyMatch[1],
);

const runReturnToCaseList = ({ context, storedContext = null }) => {
  let route;
  let page;
  let pageSize;
  executeReturnToCaseList(
    context,
    context?.page || 1,
    context?.pageSize || 10,
    {
      getItem: (key) =>
        key === "sunhold:case-list-return" && storedContext
          ? JSON.stringify(storedContext)
          : null,
    },
    (value) => {
      page = value;
    },
    (value) => {
      pageSize = value;
    },
    (value) => {
      route = value;
    },
  );
  return { route, page, pageSize };
};

test("case detail records its source context and wires both close actions to the shared return behavior", () => {
  assert.match(
    source,
    /sessionStorage\.setItem\("sunhold:case-list-return", JSON\.stringify\(\{ route: initialView, page: originalPage, pageSize: originalPageSize, query: caseQuery \}\)\)/,
  );
  assert.match(
    source,
    /onClose=\{\(\) => isCaseDetailView \? returnToCaseList\(\) : setViewingCounselCase\(null\)\}/,
  );
  assert.match(
    source,
    /data-testid="case-detail-back" onClick=\{returnToCaseList\}>返回案件列表<\/Button>/,
  );
  assert.match(
    source,
    /useState\(caseListReturnContext\?\.page \|\| 1\)/,
  );
  assert.match(
    source,
    /useState\(caseListReturnContext\?\.pageSize \|\| 10\)/,
  );
});

test("case detail returns to a my-case source with its captured pagination", () => {
  assert.deepEqual(
    runReturnToCaseList({
      context: { route: "case-mine-civil", page: 2, pageSize: 15 },
    }),
    { route: "case-mine-civil", page: 2, pageSize: 15 },
  );
});

test("case detail returns to the latest persisted company-schedule source", () => {
  assert.deepEqual(
    runReturnToCaseList({
      context: { route: "case-mine", page: 1, pageSize: 10 },
      storedContext: { route: "case-company-schedule", page: 3, pageSize: 20 },
    }),
    { route: "case-company-schedule", page: 3, pageSize: 20 },
  );
});

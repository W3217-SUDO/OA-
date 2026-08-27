import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("detail litigant editor uses the independent API while creation keeps the wizard API", () => {
  assert.match(source, /api\.put\(`\/cases\/\$\{editingCaseLitigants\.id\}\/litigants-detail`, values\)/);
  assert.match(source, /api\.put\(`\/cases\/\$\{createdCaseId\}\/litigants`, \{/);
});

test("party roles support remote keyword search and multiple system selections", () => {
  assert.match(source, /api\.get\("\/case-litigant-candidates", \{ params: \{ keyword: keyword\.trim\(\) \} \}\)/);
  assert.match(source, /const searchCaseLitigantCandidates = \(keyword: string\)/);
  assert.match(source, /mode="multiple"[\s\S]*?filterOption=\{false\}[\s\S]*?onSearch=\{searchCaseLitigantCandidates\}/);
  for (const role of ["plaintiffs", "defendants", "third_parties"]) {
    assert.match(source, new RegExp(`renderCasePartySelector\\("${role}"`));
  }
});

test("each party role exposes in-dialog creation and selects the created party", () => {
  assert.match(source, /aria-label=\{`新增\$\{CASE_LITIGANT_PARTY_LABELS\[role\]\}当事人`\}/);
  assert.match(source, /api\.post\("\/customers", \{/);
  assert.match(source, /customer_type: "当事人"/);
  assert.match(source, /caseLitigantsForm\.setFieldValue\(creatingCasePartyRole, Array\.from\(new Set\(\[\.\.\.currentValues, candidate\.title\]\)\)\)/);
  assert.match(source, /okText="保存并选中"/);
});

test("agent fields remain separate from party selectors", () => {
  for (const field of ["plaintiff_agents", "defendant_agents", "third_party_agents"]) {
    assert.match(source, new RegExp(`name="${field}"`));
  }
});

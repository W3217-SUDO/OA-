import assert from "node:assert/strict";
import test from "node:test";

import { getCaseDetailSectionVisibility } from "./src/caseDetailSectionVisibility.ts";

test("empty placeholders do not expose court or archive sections", () => {
  assert.deepEqual(
    getCaseDetailSectionVisibility({
      first_court_name: "—",
      second_court_name: " ",
      execution_court_name: null,
      archive_type: "-",
    }),
    { firstCourt: false, secondCourt: false, executionCourt: false, court: false, archive: false },
  );
});

test("court stages become visible independently", () => {
  assert.deepEqual(getCaseDetailSectionVisibility({ first_court_case_no: "(2026)沪01民初1号" }), {
    firstCourt: true,
    secondCourt: false,
    executionCourt: false,
    court: true,
    archive: false,
  });
  assert.deepEqual(getCaseDetailSectionVisibility({ second_court_name: "上海市高级人民法院" }), {
    firstCourt: false,
    secondCourt: true,
    executionCourt: false,
    court: true,
    archive: false,
  });
  assert.deepEqual(getCaseDetailSectionVisibility({ execution_court_filing_date: "2026-08-28" }), {
    firstCourt: false,
    secondCourt: false,
    executionCourt: true,
    court: true,
    archive: false,
  });
});

test("archive appears after archive data or an archive workflow status exists", () => {
  assert.equal(getCaseDetailSectionVisibility({ archive_submitted_at: "2026-08-28" }).archive, true);
  assert.equal(getCaseDetailSectionVisibility({ archive_status: "未提交" }).archive, false);
  assert.equal(getCaseDetailSectionVisibility({ archive_status: "not_submitted" }).archive, false);
  assert.equal(getCaseDetailSectionVisibility({ archive_status: "待审核" }).archive, true);
  assert.equal(getCaseDetailSectionVisibility({}, "已归档").archive, true);
  assert.equal(getCaseDetailSectionVisibility({}, "文书准备").archive, false);
});

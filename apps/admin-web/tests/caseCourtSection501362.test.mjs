import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { getCaseDetailSectionVisibility } from "../src/caseDetailSectionVisibility.ts";

const header = readFileSync(new URL("../src/legal/CaseDetail/CaseDetailHeader.tsx", import.meta.url), "utf8");

test("501362：没人填过法院信息时不显示法院信息栏，填了才显示", () => {
  assert.match(header, /case_type !== "法律顾问" && sectionVisibility\.court && <section className="case-court-summary"/);
  assert.equal(getCaseDetailSectionVisibility({ court: "", case_register_date: "2026-11-04" }).court, false, "只有案件立案日期不算法院信息");
  assert.equal(getCaseDetailSectionVisibility({ first_court_name: "上海市杨浦区人民法院" }).court, true);
  assert.equal(getCaseDetailSectionVisibility({ first_court_filing_date: "2026-11-05" }).court, true);
});

test("501362：填写入口仍在“操作 › 修改法院信息”（501640 起民事案件叫“修改法院和公证信息”）", () => {
  const constants = readFileSync(new URL("../src/legal/constants.tsx", import.meta.url), "utf8");
  const page = readFileSync(new URL("../src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");
  assert.ok(constants.includes('"修改法院和公证信息"'));
  assert.ok(page.includes('"修改法院信息"'), "刑事、行政案件仍叫修改法院信息");
});

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("legacy settlement and archive lists keep ten-row defaults", () => {
  assert.match(source, /const \[generalSettlementMeta, setGeneralSettlementMeta\] = useState\(\{[\s\S]*?pageSize: 10/);
  assert.match(source, /const \[archiveSettlementMeta, setArchiveSettlementMeta\] = useState\(\{[\s\S]*?pageSize: 10/);
});

test("settlement query params preserve route status semantics", () => {
  assert.match(source, /isGeneralSettlementPaidRoute[\s\S]*?status: "已付款"/);
  assert.match(source, /isGeneralSettlementPaymentRoute[\s\S]*?status: "待付款"/);
  assert.match(source, /isGeneralSettlementRejectedRoute[\s\S]*?status:/);
});

test("archive query params preserve route-specific endpoints", () => {
  assert.match(source, /\/finance\/archive-settlements\/payment/);
  assert.match(source, /\/finance\/archive-settlements\/paid/);
  assert.match(source, /\/finance\/archive-settlements\/rejected/);
  assert.match(source, /\/finance\/archive-settlements\/pending/);
});

test("settlement clear resets filters, selection, detail expansion, and page one", () => {
  assert.match(source, /if \(isGeneralSettlementRoute\)[\s\S]*?setOriginalQueryDraft\(\{\}\)[\s\S]*?setGeneralSettlementDetails\(\[\]\)[\s\S]*?loadGeneralSettlements\(\{\}, 1/);
});

test("archive clear resets filters, selection, and page one", () => {
  assert.match(source, /if \(isArchiveSettlementActiveRoute\)[\s\S]*?setOriginalQueryDraft\(\{\}\)[\s\S]*?loadArchiveSettlements\(\{\}, 1/);
});

test("settlement failures use the legacy query error fallback", () => {
  assert.match(source, /const settlementLegacyErrorMessage = "查询出错\."/);
  assert.match(source, /message\.error\(settlementLegacyErrorMessage\)/);
});

test("settlement review sends application ids, decision, and comment", () => {
  assert.match(source, /\/finance\/general-settlements\/applications\/review/);
  assert.match(source, /application_ids: generalSettlementReviewTargets\.map/);
  assert.match(source, /approved: generalSettlementReviewApproved/);
});

test("settlement payment and rollback keep explicit action state", () => {
  assert.match(source, /\/finance\/general-settlements\/applications\/payment/);
  assert.match(source, /action: generalSettlementPaymentAction/);
  assert.match(source, /generalSettlementPaymentAction === "rollback"/);
});

test("settlement reapply keeps a separate bounded endpoint", () => {
  assert.match(source, /\/finance\/general-settlements\/applications\/reapply/);
  assert.match(source, /generalSettlementReapplyTargets\.map/);
});

test("archive review and rollback preserve route-specific payloads", () => {
  assert.match(source, /\/finance\/archive-settlements\/payment\/review/);
  assert.match(source, /settlement_ids: archiveSettlementReviewTargets\.map/);
  assert.match(source, /record_ids: archiveSettlementRollbackTargets\.map/);
});

test("archive settlement review keeps legacy action wording and failure fallbacks", () => {
  assert.match(source, /title="同意结算"/);
  assert.match(source, /title="拒绝结算"/);
  assert.match(source, /同意结算 \$\{response\.data\.reviewed\} 条归档费/);
  assert.match(source, /拒绝结算 \$\{response\.data\.reviewed\} 条归档费/);
  assert.match(source, /标识已结算出错\./);
  assert.match(source, /拒绝结算出错\./);
  assert.match(source, /归档费回滚出错\./);
  assert.match(source, /isArchiveSettlementRejectedRoute \? "回滚归档费" : "回滚归档费结算"/);
  assert.match(source, /已回滚 \$\{response\.data\.rolled_back\} 条归档费结算/);
});

test("archive reapply remains available for rejected settlements", () => {
  assert.match(source, /\/finance\/archive-settlements\/rejected\/reapply/);
  assert.match(source, /archiveSettlementReapplyTargets\.map/);
});

test("settlement rows expose expanded detail and status context", () => {
  assert.match(source, /generalSettlementDetails\.includes\(row\.id\)/);
  assert.match(source, /finance-settlement-expanded/);
  assert.match(source, /finance-archive-payment-context/);
});

test("settlement lists retain server pagination metadata", () => {
  assert.match(source, /loadGeneralSettlements\(\s*originalQuery,\s*page,\s*pageSize,?\s*\)/);
  assert.match(source, /loadArchiveSettlements\(\s*originalQuery,\s*page,\s*pageSize,?\s*\)/);
  assert.match(source, /current: generalSettlementMeta\.page/);
  assert.match(source, /current: archiveSettlementMeta\.page/);
});

test("settlement export routes remain available for selected and full lists", () => {
  assert.match(source, /exportGeneralSettlement/);
  assert.match(source, /exportPendingArchiveSettlements/);
  assert.match(source, /selectedOriginalRows/);
});

test("general settlement export only permits backend-supported full exports", () => {
  const start = source.indexOf("const exportGeneralSettlement");
  const end = source.indexOf("const exportPendingArchiveSettlements", start);
  assert.ok(start >= 0 && end > start, "general settlement export handler should exist");
  const block = source.slice(start, end);
  assert.match(block, /selectedOnly/);
  assert.match(block, /application_ids: selectedIds\.join/);
  assert.match(block, /ids: selectedIds\.join/);
  assert.match(block, /if \(!isGeneralSettlementPendingRoute && !selectedOnly\)/);
  assert.match(block, /请选择需要导出的结算申请/);
  assert.match(
    block,
    /selectedOnly\s*\?[\s\S]*isGeneralSettlementPendingRoute[\s\S]*\{ kind \}[\s\S]*responseType/,
  );
  assert.match(block, /selectedOnly\s*&&\s*!selectedIds\.length/);
});

test("general settlement apply captures an operator remark instead of hardcoding one", () => {
  const start = source.indexOf("const applyGeneralSettlementRows");
  const end = source.indexOf("const exportConfiguredRows", start);
  assert.ok(start >= 0 && end > start, "general settlement apply handler should exist");
  const block = source.slice(start, end);
  assert.match(block, /generalSettlementApplyTargets/);
  assert.match(block, /submitGeneralSettlementApply/);
  assert.match(block, /comment: generalSettlementApplyComment/);
  assert.doesNotMatch(block, /comment:\s*["']寰呯粨绠楅〉闈㈡彁浜?["']/);
  assert.match(source, /open=\{generalSettlementApplyTargets\.length > 0\}/);
});

test("settlement request paths remain bounded and avoid fetch-all", () => {
  assert.doesNotMatch(source, /loadGeneralSettlementAll|loadArchiveSettlementAll|fetch-all/);
  assert.match(source, /page_size: pageSize/);
});
